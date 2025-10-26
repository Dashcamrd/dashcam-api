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

logger = logging.getLogger(__name__)

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
    
    # Call manufacturer API
    device_data = {"deviceId": device_id}
    result = manufacturer_api.get_latest_gps(device_data)
    
    if result.get("code") == 200:  # Manufacturer API returns 200 for success
        data = result.get("data", {})
        gps_info = data.get("gpsInfo", [])
        
        if gps_info:
            # Get the latest GPS entry (first one in the array)
            latest_gps = gps_info[0]
            return {
                "success": True,
                "device_id": device_id,
                "latitude": latest_gps.get("latitude"),
                "longitude": latest_gps.get("longitude"),
                "speed": latest_gps.get("speed"),
                "direction": latest_gps.get("direction"),
                "height": latest_gps.get("height"),
                "timestamp": latest_gps.get("time"),
                "address": None  # Not provided by manufacturer API
            }
        else:
            return {
                "success": False,
                "device_id": device_id,
                "message": "No GPS data found for this device"
            }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get GPS data: {result.get('message', 'Unknown error')}"
        )

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
    
    # Call manufacturer API
    track_data = {
        "deviceId": request.device_id,
        "date": request.date,
        "startTime": request.start_time,
        "endTime": request.end_time
    }
    result = manufacturer_api.query_detailed_track(track_data)
    
    if result.get("code") == 0:
        track_data = result.get("data", {})
        return {
            "success": True,
            "device_id": request.device_id,
            "date": request.date,
            "time_range": f"{request.start_time or 'start'} to {request.end_time or 'end'}",
            "track_points": track_data.get("points", []),
            "total_points": len(track_data.get("points", [])),
            "total_distance": track_data.get("totalDistance"),
            "duration": track_data.get("duration"),
            "max_speed": track_data.get("maxSpeed"),
            "avg_speed": track_data.get("avgSpeed")
        }
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
            gps_result = manufacturer_api.get_latest_gps(device_data)
            
            gps_status = "online" if gps_result.get("code") == 200 else "offline"
            
            # Parse GPS data from manufacturer API response
            gps_data = {}
            if gps_result.get("code") == 200:
                data = gps_result.get("data", {})
                gps_info = data.get("gpsInfo", [])
                if gps_info:
                    gps_data = gps_info[0]  # Get the latest GPS entry
            
            # Convert raw coordinates to decimal degrees (same as map page)
            latitude = None
            longitude = None
            location_name = "Location unavailable"
            
            if gps_data:
                lat_raw = gps_data.get("latitude")
                lng_raw = gps_data.get("longitude")
                
                if lat_raw and lng_raw:
                    # Convert from raw integer format to decimal degrees
                    latitude = lat_raw / 1000000.0
                    longitude = lng_raw / 1000000.0
                    
                    # Generate human-readable location name (same logic as map page)
                    if latitude and longitude:
                        # Simple location mapping based on coordinates
                        if 5.2 <= latitude <= 5.4 and 100.2 <= longitude <= 100.4:
                            location_name = "Batu Maung, Malaysia"
                        else:
                            location_name = f"{latitude:.6f}, {longitude:.6f}"
            
            devices_with_gps.append({
                "device_id": device.device_id,
                "name": device.name,
                "status": device.status,
                "gps_status": gps_status,
                "last_location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "location_name": location_name,
                    "timestamp": gps_data.get("time") if gps_data else None,
                    "address": gps_data.get("address") if gps_data else None
                },
                "last_update": _get_relative_time(gps_data.get("time")) if gps_data else "Unknown"
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
    
    # Call manufacturer API
    device_data = {"deviceId": device_id}
    result = manufacturer_api.get_device_states(device_data)
    
    if result.get("code") == 200:  # Manufacturer API returns 200 for success
        data = result.get("data", {})
        device_list = data.get("list", [])
        
        if device_list and len(device_list) > 0:
            device_data = device_list[0]  # Get first device
            acc_state = device_data.get("accState", 0)  # 0 = OFF, 1 = ON
            
            return {
                "success": True,
                "acc_status": acc_state == 1,  # Convert to boolean
                "acc_state": acc_state,
                "raw_data": device_data
            }
        else:
            return {
                "success": False,
                "message": "No device data found",
                "acc_status": False,
                "acc_state": 0
            }
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch device states")


