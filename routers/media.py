"""
Media Router - Handles video preview, playback, and file management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/media", tags=["Media"])

class PreviewRequest(BaseModel):
    device_id: str
    channel: Optional[int] = 1
    stream: Optional[int] = 1  # 1=main stream, 2=sub stream

class PlaybackRequest(BaseModel):
    device_id: str
    channel: Optional[int] = 1
    start_time: str  # format: "2024-01-01 10:00:00"
    end_time: str    # format: "2024-01-01 11:00:00"

def verify_device_access(device_id: str, current_user: dict) -> bool:
    """Verify that the current user has access to the specified device"""
    user_devices = get_user_devices(current_user["user_id"])
    user_device_ids = [device.device_id for device in user_devices]
    return device_id in user_device_ids

@router.post("/preview")
def start_preview(
    request: PreviewRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start live video preview for a device.
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    preview_data = {
        "deviceId": request.device_id,
        "channel": request.channel,
        "stream": request.stream
    }
    
    result = manufacturer_api.open_preview(preview_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "message": "Preview started successfully",
            "data": result.get("data", {}),
            "device_id": request.device_id
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to start preview: {result.get('message', 'Unknown error')}"
        )

@router.post("/preview/close")
def close_preview(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Close live video preview for a device"""
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    preview_data = {"deviceId": device_id}
    result = manufacturer_api.close_preview(preview_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "message": "Preview closed successfully",
            "device_id": device_id
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to close preview: {result.get('message', 'Unknown error')}"
        )

@router.post("/playback")
def start_playback(
    request: PlaybackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start video playback for a specific time range.
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    playback_data = {
        "deviceId": request.device_id,
        "channel": request.channel,
        "startTime": request.start_time,
        "endTime": request.end_time
    }
    
    result = manufacturer_api.start_playback(playback_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "message": "Playback started successfully",
            "data": result.get("data", {}),
            "device_id": request.device_id,
            "time_range": f"{request.start_time} to {request.end_time}"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to start playback: {result.get('message', 'Unknown error')}"
        )

@router.post("/playback/close")
def close_playback(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Close video playback for a device"""
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    playback_data = {"deviceId": device_id}
    result = manufacturer_api.close_playback(playback_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "message": "Playback closed successfully",
            "device_id": device_id
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to close playback: {result.get('message', 'Unknown error')}"
        )

@router.get("/files/{device_id}")
def get_media_files(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    channel: Optional[int] = Query(1, description="Channel number")
):
    """
    Get list of available media files for a device.
    This is a stub implementation - actual endpoint depends on manufacturer API.
    """
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # This would call a specific manufacturer API endpoint for file listing
    # For now, return a stub response
    return {
        "success": True,
        "device_id": device_id,
        "files": [],  # This would contain actual file list from manufacturer API
        "message": "File listing feature - to be implemented based on manufacturer API",
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "channel": channel
        }
    }


