"""
Media Router - Handles video preview, playback, and file management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional
from pydantic import BaseModel
import logging
import uuid
from adapters import MediaAdapter

logger = logging.getLogger(__name__)

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

class IntercomRequest(BaseModel):
    device_id: str
    channel: Optional[int] = 1

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
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Starting preview+monitor for device {request.device_id}")
    
    # Request 1: Get video stream (Preview - dataType=1)
    preview_data = MediaAdapter.build_preview_request(
        device_id=request.device_id,
        channel=request.channel,
        stream_type=request.stream,
        data_type=1  # Preview (video only)
    )
    
    preview_result = manufacturer_api.open_preview(preview_data)
    preview_dto = MediaAdapter.parse_preview_response(preview_result, request.device_id, correlation_id + "_video")
    
    # Request 2: Get audio stream (Monitor - dataType=3)
    monitor_data = MediaAdapter.build_preview_request(
        device_id=request.device_id,
        channel=request.channel,
        stream_type=request.stream,
        data_type=3  # Monitor (audio only)
    )
    
    monitor_result = manufacturer_api.open_preview(monitor_data)
    monitor_dto = MediaAdapter.parse_preview_response(monitor_result, request.device_id, correlation_id + "_audio")
    
    if preview_dto and monitor_dto:
        # Combine both: video URL from preview, audio URL from monitor
        videos_with_audio = []
        for video in preview_dto.videos:
            video_dict = video.model_dump(by_alias=False)
            # Add audio URL from monitor
            if monitor_dto.videos:
                video_dict['audio_url'] = monitor_dto.videos[0].play_url
            videos_with_audio.append(video_dict)
        
        return {
            "success": True,
            "message": "Preview+Monitor started successfully",
            "device_id": request.device_id,
            "videos": videos_with_audio
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to start preview+monitor: Preview={bool(preview_dto)}, Monitor={bool(monitor_dto)}"
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
    
    # Build request using adapter
    close_data = MediaAdapter.build_close_preview_request(device_id)
    
    # Call manufacturer API
    result = manufacturer_api.close_preview(close_data)
    
    # Parse response using adapter
    success = MediaAdapter.parse_simple_response(result)
    
    if success:
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
    
    # Build request using adapter
    playback_data = MediaAdapter.build_playback_request(
        device_id=request.device_id,
        start_time=request.start_time,
        end_time=request.end_time,
        channel=request.channel,
        data_type=1,  # Playback
        stream_type=0  # 0=main stream, 1=sub stream (default to main)
    )
    
    # Call manufacturer API
    result = manufacturer_api.start_playback(playback_data)
    
    # Parse response using adapter
    preview_dto = MediaAdapter.parse_preview_response(result, request.device_id)
    
    if preview_dto:
        return {
            "success": True,
            "message": "Playback started successfully",
            "device_id": request.device_id,
            "time_range": f"{request.start_time} to {request.end_time}",
            "videos": [v.model_dump(by_alias=False) for v in preview_dto.videos]
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
    
    # Build request using adapter
    close_data = MediaAdapter.build_close_playback_request(device_id)
    
    # Call manufacturer API
    result = manufacturer_api.close_playback(close_data)
    
    # Parse response using adapter
    success = MediaAdapter.parse_simple_response(result)
    
    if success:
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

@router.post("/intercom/start")
def start_intercom(
    request: IntercomRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start two-way intercom with device.
    Returns WebRTC URLs for playing device audio and pushing user audio.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Starting intercom for device {request.device_id}")
    
    # Build request using adapter
    intercom_data = MediaAdapter.build_intercom_request(request.device_id, request.channel)
    
    # Call manufacturer API
    result = manufacturer_api.start_intercom(intercom_data)
    
    # Check if successful
    if result.get("code") == 200 and result.get("data", {}).get("errorCode") == 200:
        data = result.get("data", {})
        return {
            "success": True,
            "message": "Intercom started successfully",
            "device_id": request.device_id,
            "channel": request.channel,
            "play_url": data.get("playUrl"),  # WebRTC URL for receiving device audio
            "push_url": data.get("pushUrl"),  # WebRTC URL for sending user audio
        }
    else:
        error_desc = result.get("data", {}).get("errorDesc", result.get("message", "Unknown error"))
        raise HTTPException(
            status_code=400,
            detail=f"Failed to start intercom: {error_desc}"
        )

@router.post("/intercom/stop")
def stop_intercom(
    request: IntercomRequest,
    current_user: dict = Depends(get_current_user)
):
    """Stop two-way intercom with device"""
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Stopping intercom for device {request.device_id}")
    
    # Build request using adapter
    intercom_data = MediaAdapter.build_intercom_request(request.device_id, request.channel)
    
    # Call manufacturer API
    result = manufacturer_api.end_intercom(intercom_data)
    
    # Check if successful
    if result.get("code") == 200:
        return {
            "success": True,
            "message": "Intercom stopped successfully",
            "device_id": request.device_id
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to stop intercom: {result.get('message', 'Unknown error')}"
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


