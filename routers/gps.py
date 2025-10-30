"""
GPS Router - Handles GPS tracking, location, and history
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import logging
import uuid
from models.dto import LatestGpsDto, TrackPlaybackDto, TrackPointDto, AccStateDto
from adapters import GPSAdapter, DeviceAdapter

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
    user_devices = get_user_devices(current_user["user_id"])
    user_device_ids = [device.device_id for device in user_devices]
    return device_id in user_device_ids

@router.get("/latest/{device_id}")
def get_latest_gps(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the latest GPS location for a device.
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Getting latest GPS for device {device_id}")
    
    # Build request using adapter
    request_data = GPSAdapter.build_latest_gps_request(device_id)
    
    # Call manufacturer API
    result = manufacturer_api.get_latest_gps({"deviceId": device_id})
    
    # Parse response using adapter with correlation ID
    dto = GPSAdapter.parse_latest_gps_response(result, device_id, correlation_id)
    
    if dto:
        return {"success": True, **dto.model_dump(by_alias=False)}
    else:
        return {
            "success": False,
            "device_id": device_id,
            "message": "No GPS data found for this device"
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
    
    # Call manufacturer API (vendor expects date format, adapter handles conversion if needed)
    track_data = {
        "deviceId": request.device_id,
        "date": request.date,
        "startTime": request.start_time,
        "endTime": request.end_time
    }
    result = manufacturer_api.query_detailed_track(track_data)
    
    # Parse response using adapter with correlation ID
    playback = GPSAdapter.parse_track_history_response(result, request.device_id, correlation_id)
    
    if playback:
        return {"success": True, **playback.model_dump(by_alias=False)}
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get track history: {result.get('message', 'Unknown error')}"
        )

@router.get("/devices")
def get_user_devices_with_gps_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all devices assigned to the current user with their GPS status.
    """
    user_devices = get_user_devices(current_user["user_id"])
    
    if not user_devices:
        return {
            "success": True,
            "devices": [],
            "message": "No devices assigned to this user"
        }
    
    # Get latest GPS for each device
    devices_with_gps = []
    for device in user_devices:
        try:
            device_data = {"deviceId": device.device_id}
            
            # Try v2 API first for lastOnlineTime, fallback to v1 if needed
            gps_result = manufacturer_api.get_latest_gps_v2(device_data)
            
            # If v2 fails, fallback to v1
            if gps_result.get("code") != 200:
                gps_result = manufacturer_api.get_latest_gps(device_data)
            
            # Generate correlation ID for tracing
            correlation_id = str(uuid.uuid4())[:8]
            
            # Parse GPS data using adapter
            gps_dto = GPSAdapter.parse_latest_gps_response(gps_result, device.device_id, correlation_id)
            
            gps_status = "online" if gps_dto else "offline"
            
            # Extract location info from DTO
            latitude = gps_dto.latitude if gps_dto else None
            longitude = gps_dto.longitude if gps_dto else None
            location_name = "Location unavailable"
            
            if latitude and longitude:
                # Generate human-readable location name (same logic as map page)
                if 5.2 <= latitude <= 5.4 and 100.2 <= longitude <= 100.4:
                    location_name = "Batu Maung, Malaysia"
                else:
                    location_name = f"{latitude:.6f}, {longitude:.6f}"
            
            # Get timestamp for relative time
            last_online_time = None
            timestamp_for_relative = None
            if gps_dto:
                last_online_time = gps_dto.timestamp_ms
                timestamp_for_relative = gps_dto.timestamp_ms
            
            devices_with_gps.append({
                "device_id": device.device_id,
                "name": device.name,
                "status": device.status,
                "gps_status": gps_status,
                "last_location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "location_name": location_name,
                    "timestamp": timestamp_for_relative,
                    "address": gps_dto.address if gps_dto else None
                },
                "last_update": _get_relative_time_from_timestamp(last_online_time // 1000) if last_online_time else "Unknown"
            })
        except Exception as e:
            # If GPS fetch fails for a device, still include it with offline status
            devices_with_gps.append({
                "device_id": device.device_id,
                "name": device.name,
                "status": device.status,
                "gps_status": "offline",
                "last_location": {
                    "latitude": None,
                    "longitude": None,
                    "location_name": "Location unavailable",
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
    current_user: dict = Depends(get_current_user)
):
    """
    Get device states including ACC status.
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Getting device states for device {device_id}")
    
    # Build request using adapter
    request_data = DeviceAdapter.build_device_states_request([device_id])
    
    # Call manufacturer API
    result = manufacturer_api.get_device_states({"deviceId": device_id})
    
    # Parse response using adapter with correlation ID
    dto = DeviceAdapter.parse_device_states_response(result, device_id, correlation_id)
    
    if dto and dto.last_online_time_ms is not None:
        return {"success": True, **dto.model_dump(by_alias=False)}
    elif dto:
        return {"success": False, **dto.model_dump(by_alias=False), "message": "No device data found"}
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch device states")


