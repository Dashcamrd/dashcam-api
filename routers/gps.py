"""
GPS Router - Handles GPS tracking, location, and history
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional
from pydantic import BaseModel

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
    
    if result.get("code") == 0:
        gps_data = result.get("data", {})
        return {
            "success": True,
            "device_id": device_id,
            "gps_data": gps_data,
            "timestamp": gps_data.get("timestamp"),
            "latitude": gps_data.get("latitude"),
            "longitude": gps_data.get("longitude"),
            "speed": gps_data.get("speed"),
            "direction": gps_data.get("direction"),
            "address": gps_data.get("address")
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
            
            gps_status = "online" if gps_result.get("code") == 0 else "offline"
            gps_data = gps_result.get("data", {}) if gps_result.get("code") == 0 else {}
            
            devices_with_gps.append({
                "device_id": device.device_id,
                "name": device.name,
                "status": device.status,
                "gps_status": gps_status,
                "last_location": {
                    "latitude": gps_data.get("latitude"),
                    "longitude": gps_data.get("longitude"),
                    "timestamp": gps_data.get("timestamp"),
                    "address": gps_data.get("address")
                } if gps_data else None
            })
        except Exception as e:
            # If GPS fetch fails for a device, still include it with offline status
            devices_with_gps.append({
                "device_id": device.device_id,
                "name": device.name,
                "status": device.status,
                "gps_status": "offline",
                "last_location": None
            })
    
    return {
        "success": True,
        "devices": devices_with_gps,
        "total_devices": len(devices_with_gps)
    }
