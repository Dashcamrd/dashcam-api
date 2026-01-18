"""
GPS Router - Handles GPS tracking, location, and history
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from services.geocoding_service import GeocodingService
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import logging
import uuid
from models.dto import LatestGpsDto, TrackPlaybackDto, TrackPointDto, AccStateDto
from models.device_cache_db import DeviceCacheDB
from adapters import GPSAdapter, DeviceAdapter
from database import SessionLocal

# Database dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

logger = logging.getLogger(__name__)

def _get_relative_time_from_timestamp(timestamp_seconds: int) -> str:
    """Convert Unix timestamp to relative time format like 'X minutes ago'"""
    if not timestamp_seconds:
        return "Unknown"
    
    try:
        # Convert Unix timestamp to datetime
        timestamp = datetime.fromtimestamp(timestamp_seconds)
        now = datetime.now()
        diff = now - timestamp
        
        # Calculate time difference
        total_seconds = int(diff.total_seconds())
        
        if total_seconds < 60:
            return "Just now"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif total_seconds < 86400:  # Less than 1 day
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:  # More than 1 day
            days = total_seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
    except Exception as e:
        logger.error(f"Error parsing timestamp '{timestamp_seconds}': {e}")
        return "Unknown"

def _get_relative_time(timestamp_str: str) -> str:
    """Convert timestamp string to relative time format like 'X minutes ago'"""
    if not timestamp_str:
        return "Unknown"
    
    try:
        # Parse the timestamp string (format: "2025-10-26 11:20:39")
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff = now - timestamp
        
        # Calculate time difference
        total_seconds = int(diff.total_seconds())
        
        if total_seconds < 60:
            return "Just now"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif total_seconds < 86400:  # Less than 1 day
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:  # More than 1 day
            days = total_seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
    except Exception as e:
        logger.error(f"Error parsing timestamp '{timestamp_str}': {e}")
        return "Unknown"

router = APIRouter(prefix="/gps", tags=["GPS"])

class TrackQueryRequest(BaseModel):
    device_id: str
    start_date: str  # format: "2024-01-01"
    end_date: str    # format: "2024-01-01"

class DetailedTrackRequest(BaseModel):
    device_id: str
    date: str        # format: "2024-01-01"
    start_time: Optional[str] = None  # format: "10:00:00"
    end_time: Optional[str] = None    # format: "11:00:00"

def verify_device_access(device_id: str, current_user: dict) -> bool:
    """Verify that the current user has access to the specified device"""
    user_devices = get_user_devices(current_user["user_id"], is_admin=current_user.get("is_admin", False))
    user_device_ids = [device.device_id for device in user_devices]
    return device_id in user_device_ids

@router.get("/latest/{device_id}")
def get_latest_gps(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the latest GPS location for a device.
    
    OPTIMIZED: Uses cached data from database (populated by forwarding webhooks)
    for near real-time updates (every 1-2 seconds) instead of calling VMS API.
    Falls back to VMS API only if cache is stale (>5 minutes old).
    """
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    
    # ========================================
    # OPTIMIZATION: Try cached data FIRST
    # ========================================
    cache = db.query(DeviceCacheDB).filter(DeviceCacheDB.device_id == device_id).first()
    
    if cache and cache.latitude is not None and cache.longitude is not None:
        # Check if cache is fresh (less than 5 minutes old)
        cache_age_seconds = 999999  # Default to stale
        if cache.updated_at:
            cache_age_seconds = (datetime.now() - cache.updated_at).total_seconds()
        
        # Use cached data if it's fresh (< 300 seconds = 5 minutes)
        if cache_age_seconds < 300:
            logger.info(f"[{correlation_id}] ✅ Using CACHED GPS for {device_id} (age: {cache_age_seconds:.0f}s) - NO VMS API CALL")
            
            # Build timestamp_ms from cache
            timestamp_ms = None
            if cache.gps_time:
                timestamp_ms = int(cache.gps_time.timestamp() * 1000)
            elif cache.last_online_time:
                timestamp_ms = int(cache.last_online_time.timestamp() * 1000)
            elif cache.updated_at:
                timestamp_ms = int(cache.updated_at.timestamp() * 1000)
            
            # Get location name
            location_name = cache.address
            if not location_name and cache.latitude and cache.longitude:
                location_name = GeocodingService.get_location_name(cache.latitude, cache.longitude)
            
            return {
                "success": True,
                "device_id": device_id,
                "latitude": cache.latitude,
                "longitude": cache.longitude,
                "speed": cache.speed,
                "direction": cache.direction,
                "altitude": cache.altitude,
                "acc_on": cache.acc_status or False,
                "timestamp_ms": timestamp_ms,
                "lastOnlineTime": timestamp_ms,
                "last_online_time_ms": timestamp_ms,
                "last_online_time": timestamp_ms,
                "address": location_name,
                "location_name": location_name,
                "source": "cache"  # Indicate data source for debugging
            }
        else:
            logger.info(f"[{correlation_id}] ⚠️ Cache stale for {device_id} (age: {cache_age_seconds:.0f}s), falling back to VMS API")
    else:
        logger.info(f"[{correlation_id}] ⚠️ No cache for {device_id}, falling back to VMS API")
    
    # ========================================
    # FALLBACK: Call VMS API if cache is stale/missing
    # ========================================
    logger.info(f"[{correlation_id}] 🔄 Calling VMS API for latest GPS (device: {device_id})")
    
    # Store cache timestamp for later use (VMS API might return wrong timestamp for sleeping devices)
    cache_timestamp_ms = None
    if cache and cache.updated_at:
        if cache.gps_time:
            cache_timestamp_ms = int(cache.gps_time.timestamp() * 1000)
        elif cache.last_online_time:
            cache_timestamp_ms = int(cache.last_online_time.timestamp() * 1000)
        elif cache.updated_at:
            cache_timestamp_ms = int(cache.updated_at.timestamp() * 1000)
    
    # Use V2 API ONLY - no V1 fallback
    result = manufacturer_api.get_latest_gps_v2({"deviceId": device_id})
    
    # Check if vendor API returned an error first
    if result.get("code") == -1 or result.get("code") not in [200, 0]:
        error_msg = result.get("message", "Unknown error from vendor API")
        logger.warning(f"[{correlation_id}] Vendor API error for latest GPS: {error_msg}")
        
        # If API fails but we have stale cache, return stale cache with warning
        if cache and cache.latitude is not None:
            logger.info(f"[{correlation_id}] ⚠️ VMS API failed, returning STALE cache data")
            timestamp_ms = None
            if cache.gps_time:
                timestamp_ms = int(cache.gps_time.timestamp() * 1000)
            elif cache.updated_at:
                timestamp_ms = int(cache.updated_at.timestamp() * 1000)
            
            return {
                "success": True,
                "device_id": device_id,
                "latitude": cache.latitude,
                "longitude": cache.longitude,
                "speed": cache.speed,
                "direction": cache.direction,
                "timestamp_ms": timestamp_ms,
                "lastOnlineTime": timestamp_ms,
                "last_online_time_ms": timestamp_ms,
                "address": cache.address,
                "location_name": cache.address or "Location unavailable",
                "source": "stale_cache",
                "warning": "Data may be outdated"
            }
        
        # Check for vendor API infrastructure errors (database, connection issues)
        error_msg_lower = str(error_msg).lower()
        if "mysql" in error_msg_lower or "database" in error_msg_lower or "connection" in error_msg_lower:
            logger.error(f"[{correlation_id}] Vendor API infrastructure error: {error_msg}")
            return {
                "success": False,
                "device_id": device_id,
                "latitude": None,
                "longitude": None,
                "message": "Vendor API temporarily unavailable - please try again later",
                "is_offline": True,
                "error_type": "vendor_infrastructure_error"
            }
        
        # Return graceful response - don't treat as fatal error
        return {
            "success": False,
            "device_id": device_id,
            "latitude": None,
            "longitude": None,
            "message": "GPS data temporarily unavailable",
            "is_offline": True
        }
    
    # Parse response using adapter with correlation ID (V2 only)
    dto = GPSAdapter.parse_latest_gps_response(result, device_id, correlation_id, use_v2_only=True)
    
    if dto:
        # Return with multiple field name formats for Flutter compatibility
        response_data = dto.model_dump(by_alias=False)
        
        # IMPORTANT: Use cache timestamp if available (VMS might return wrong timestamp for sleeping devices)
        # VMS API sometimes returns current time instead of device's actual last online time
        final_timestamp_ms = dto.timestamp_ms
        if cache_timestamp_ms is not None:
            # Check if VMS timestamp seems "too fresh" (within 2 minutes of now)
            # If so, prefer the cache timestamp which reflects actual device activity
            now_ms = int(datetime.now().timestamp() * 1000)
            if dto.timestamp_ms is not None:
                vms_age_seconds = (now_ms - dto.timestamp_ms) / 1000
                cache_age_seconds = (now_ms - cache_timestamp_ms) / 1000
                
                # If VMS says "just now" (<2min) but cache says older, use cache
                if vms_age_seconds < 120 and cache_age_seconds > 120:
                    logger.info(f"[{correlation_id}] VMS timestamp too fresh ({vms_age_seconds:.0f}s), using cache timestamp ({cache_age_seconds:.0f}s)")
                    final_timestamp_ms = cache_timestamp_ms
            else:
                # VMS returned no timestamp, use cache
                final_timestamp_ms = cache_timestamp_ms
        
        # Always include timestamp fields (even if None) so Flutter knows what to look for
        response_data["timestamp_ms"] = final_timestamp_ms
        
        # Add timestamp aliases if available (or None if not available)
        response_data["lastOnlineTime"] = final_timestamp_ms
        response_data["last_online_time_ms"] = final_timestamp_ms
        response_data["last_online_time"] = final_timestamp_ms
        
        # Get geocoded address from coordinates (same as devices screen)
        if dto.latitude is not None and dto.longitude is not None:
            location_name = GeocodingService.get_location_name(dto.latitude, dto.longitude)
            response_data["address"] = location_name
            response_data["location_name"] = location_name
        
        response_data["source"] = "vms_api"  # Indicate data source for debugging
        
        return {"success": True, **response_data}
    else:
        # No GPS data available - return graceful response
        logger.info(f"[{correlation_id}] No GPS data found for device {device_id}")
        return {
            "success": False,
            "device_id": device_id,
            "latitude": None,
            "longitude": None,
            "message": "No GPS data available for this device",
            "is_offline": True
        }

@router.post("/track-dates")
def query_track_dates(
    request: TrackQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Query available GPS tracking dates for a device within a date range.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    track_data = {
        "deviceId": request.device_id,
        "startDate": request.start_date,
        "endDate": request.end_date
    }
    result = manufacturer_api.query_track_dates(track_data)
    
    if result.get("code") == 0:
        dates_data = result.get("data", {})
        return {
            "success": True,
            "device_id": request.device_id,
            "date_range": f"{request.start_date} to {request.end_date}",
            "available_dates": dates_data.get("dates", []),
            "total_days": len(dates_data.get("dates", []))
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to query track dates: {result.get('message', 'Unknown error')}"
        )

@router.post("/history")
def get_detailed_track_history(
    request: DetailedTrackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed GPS tracking history for a specific date and time range.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Getting track history for device {request.device_id}")
    
    # Convert date to startTime/endTime (Unix timestamps in seconds)
    from datetime import datetime, time as dt_time
    
    try:
        # Parse date string (YYYY-MM-DD)
        date_obj = datetime.strptime(request.date, "%Y-%m-%d")
        
        # Start of day: 00:00:00
        start_datetime = datetime.combine(date_obj.date(), dt_time.min)
        start_time = int(start_datetime.timestamp())
        
        # End of day: 23:59:59
        end_datetime = datetime.combine(date_obj.date(), dt_time.max)
        end_time = int(end_datetime.timestamp())
        
        # Override with provided times if specified
        if request.start_time:
            # Parse time string (HH:MM:SS) and combine with date
            time_obj = datetime.strptime(request.start_time, "%H:%M:%S").time()
            start_datetime = datetime.combine(date_obj.date(), time_obj)
            start_time = int(start_datetime.timestamp())
        
        if request.end_time:
            # Parse time string (HH:MM:SS) and combine with date
            time_obj = datetime.strptime(request.end_time, "%H:%M:%S").time()
            end_datetime = datetime.combine(date_obj.date(), time_obj)
            end_time = int(end_datetime.timestamp())
        
    except ValueError as e:
        logger.error(f"[{correlation_id}] Error parsing date/time: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date/time format: {e}")
    
    # Call manufacturer API with Unix timestamps
    track_data = {
        "deviceId": request.device_id,
        "startTime": start_time,
        "endTime": end_time
    }
    
    # Log the actual request details for debugging
    logger.info(f"[{correlation_id}] Requesting track data:")
    logger.info(f"[{correlation_id}]   Device ID: {request.device_id}")
    logger.info(f"[{correlation_id}]   Date: {request.date}")
    logger.info(f"[{correlation_id}]   Start Time (Unix): {start_time} ({datetime.fromtimestamp(start_time)})")
    logger.info(f"[{correlation_id}]   End Time (Unix): {end_time} ({datetime.fromtimestamp(end_time)})")
    logger.info(f"[{correlation_id}]   Request data: {track_data}")
    
    result = manufacturer_api.query_detailed_track(track_data)
    
    # Log the vendor API response
    logger.info(f"[{correlation_id}] Vendor API response: code={result.get('code')}, message={result.get('message')}")
    
    # Check if vendor API returned an error
    if result.get("code") == -1 or result.get("code") not in [200, 0]:
        error_msg = result.get("message", "Unknown error from vendor API")
        logger.error(f"[{correlation_id}] Vendor API error: {error_msg}")
        
        # Check if it's a 404 - might mean no data for this date
        if "404" in str(error_msg) or "not found" in str(error_msg).lower():
            return {
                "success": False,
                "message": f"No track data available for {request.date}",
                "device_id": request.device_id,
                "date": request.date,
                "points": []
            }
        
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get track history: {error_msg}"
        )
    
    # Parse response using adapter with correlation ID
    playback = GPSAdapter.parse_track_history_response(result, request.device_id, correlation_id)
    
    if playback:
        return {"success": True, **playback.model_dump(by_alias=False)}
    else:
        # Adapter returned None - likely no data or parsing issue
        logger.warning(f"[{correlation_id}] Adapter returned no data for device {request.device_id} on {request.date}")
        return {
            "success": False,
            "message": f"No track data available for {request.date}",
            "device_id": request.device_id,
            "date": request.date,
            "points": []
        }

@router.get("/devices")
def get_user_devices_with_gps_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all devices assigned to the current user with their GPS status.
    
    OPTIMIZED: Uses cached data from database (populated by forwarding webhooks)
    instead of calling VMS API for each device. This avoids rate limiting issues.
    """
    user_devices = get_user_devices(current_user["user_id"], is_admin=current_user.get("is_admin", False))
    
    if not user_devices:
        return {
            "success": True,
            "devices": [],
            "message": "No devices assigned to this user"
        }
    
    # Get device IDs for efficient database query
    device_ids = [device.device_id for device in user_devices]
    
    # Fetch ALL cached data in ONE database query (no VMS API calls!)
    cached_devices = db.query(DeviceCacheDB).filter(
        DeviceCacheDB.device_id.in_(device_ids)
    ).all()
    
    # Create lookup dict for fast access
    cache_lookup = {cache.device_id: cache for cache in cached_devices}
    
    logger.info(f"📊 Fetched {len(cached_devices)} cached devices from database (no VMS API calls)")
    
    # Build response using cached data
    devices_with_gps = []
    for device in user_devices:
        cache = cache_lookup.get(device.device_id)
        
        if cache:
            # Use cached data from forwarding webhooks
            latitude = cache.latitude
            longitude = cache.longitude
            address = cache.address
            
            # Check if cache is stale (> 5 minutes = 300 seconds)
            cache_age_seconds = 999999  # Default to stale
            if cache.updated_at:
                cache_age_seconds = (datetime.now() - cache.updated_at).total_seconds()
            
            # Only trust acc_status and is_online if cache is fresh
            if cache_age_seconds < 300:  # Fresh cache (< 5 minutes)
                acc_status = cache.acc_status or False
                is_online = cache.is_online or False
                gps_status = "online" if (latitude is not None and longitude is not None) else "offline"
            else:  # Stale cache - don't trust status fields
                acc_status = False  # Show as OFF when data is old
                is_online = False
                gps_status = "offline"  # Mark as offline when data is stale
            
            # Get location name from cache or geocode if needed
            if address:
                location_name = address
            elif latitude and longitude:
                location_name = GeocodingService.get_location_name(latitude, longitude)
            else:
                location_name = "Location unavailable"
            
            # Calculate timestamp for relative time
            last_online_time_ms = None
            if cache.last_online_time:
                last_online_time_ms = int(cache.last_online_time.timestamp() * 1000)
            elif cache.gps_time:
                last_online_time_ms = int(cache.gps_time.timestamp() * 1000)
            elif cache.updated_at:
                last_online_time_ms = int(cache.updated_at.timestamp() * 1000)
            
            devices_with_gps.append({
                "device_id": device.device_id,
                "name": device.name,
                "status": device.status,
                "gps_status": gps_status,
                "acc_status": acc_status,
                "last_location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "location_name": location_name,
                    "timestamp": last_online_time_ms,
                    "address": address
                },
                "last_update": _get_relative_time_from_timestamp(last_online_time_ms // 1000) if last_online_time_ms else "Unknown"
            })
        else:
            # No cached data - device hasn't sent data via forwarding yet
            devices_with_gps.append({
                "device_id": device.device_id,
                "name": device.name,
                "status": device.status,
                "gps_status": "offline",
                "acc_status": False,
                "last_location": {
                    "latitude": None,
                    "longitude": None,
                    "location_name": "No data received yet",
                    "timestamp": None,
                    "address": None
                },
                "last_update": "Unknown"
            })
    
    return {
        "success": True,
        "devices": devices_with_gps,
        "total_devices": len(devices_with_gps)
    }

@router.get("/states/{device_id}")
def get_device_states(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get device states including ACC status.
    
    OPTIMIZED: Uses cached data from database (populated by forwarding webhooks)
    for instant response instead of calling VMS API.
    Falls back to VMS API only if cache is stale (>5 minutes old).
    """
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    
    # ========================================
    # OPTIMIZATION: Try cached data FIRST
    # ========================================
    cache = db.query(DeviceCacheDB).filter(DeviceCacheDB.device_id == device_id).first()
    
    if cache:
        # Check if cache is fresh (less than 5 minutes old)
        cache_age_seconds = 999999  # Default to stale
        if cache.updated_at:
            cache_age_seconds = (datetime.now() - cache.updated_at).total_seconds()
        
        # Use cached data if it's fresh (< 300 seconds = 5 minutes)
        if cache_age_seconds < 300:
            logger.info(f"[{correlation_id}] ✅ Using CACHED states for {device_id} (age: {cache_age_seconds:.0f}s) - NO VMS API CALL")
            
            return {
                "success": True,
                "device_id": device_id,
                "acc_on": cache.acc_status or False,
                "acc_status": cache.acc_status or False,
                "is_online": cache.is_online or False,
                "source": "cache"
            }
        else:
            logger.info(f"[{correlation_id}] ⚠️ Cache stale for {device_id} (age: {cache_age_seconds:.0f}s), falling back to VMS API")
    else:
        logger.info(f"[{correlation_id}] ⚠️ No cache for {device_id}, falling back to VMS API")
    
    # ========================================
    # FALLBACK: Call VMS API if cache is stale/missing
    # ========================================
    logger.info(f"[{correlation_id}] 🔄 Calling VMS API for device states (device: {device_id})")
    
    # Build request using adapter
    request_data = DeviceAdapter.build_device_states_request([device_id])
    
    # Call manufacturer API
    result = manufacturer_api.get_device_states({"deviceId": device_id})
    
    # Parse response using adapter with correlation ID
    dto = DeviceAdapter.parse_device_states_response(result, device_id, correlation_id)
    
    if dto:
        # Return with both snake_case and camelCase field names for compatibility
        response_data = {
            "success": True,
            "device_id": dto.device_id,
            "acc_on": dto.acc_on,
            "acc_status": dto.acc_on,  # Alias for Flutter
            "source": "vms_api"
        }
        
        return response_data
    else:
        # If API fails but we have stale cache, return stale cache
        if cache:
            logger.info(f"[{correlation_id}] ⚠️ VMS API failed, returning STALE cache data")
            return {
                "success": True,
                "device_id": device_id,
                "acc_on": cache.acc_status or False,
                "acc_status": cache.acc_status or False,
                "source": "stale_cache",
                "warning": "Data may be outdated"
            }
        
        raise HTTPException(status_code=500, detail="Failed to fetch device states")


