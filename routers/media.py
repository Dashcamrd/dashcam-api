"""
Media Router - Handles video preview, playback, and file management
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional
from pydantic import BaseModel
import logging
import uuid
import httpx
import asyncio
import websockets
from adapters import MediaAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media"])

class PreviewRequest(BaseModel):
    device_id: str
    channel: Optional[int] = 1
    stream: Optional[int] = 1  # 1=main stream, 2=sub stream
    play_format: Optional[int] = 0  # 0=WebSocket, 2=WebRTC

class PlaybackRequest(BaseModel):
    device_id: str
    channel: Optional[int] = 1
    start_time: str  # format: "2024-01-01 10:00:00"
    end_time: str    # format: "2024-01-01 11:00:00"

class IntercomRequest(BaseModel):
    device_id: str
    channel: Optional[int] = 1

class FileListRequest(BaseModel):
    device_id: str
    date: str  # format: "2024-01-15"
    channel: Optional[int] = 1

def verify_device_access(device_id: str, current_user: dict) -> bool:
    """Verify that the current user has access to the specified device"""
    user_devices = get_user_devices(current_user["user_id"], is_admin=current_user.get("is_admin", False))
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
        data_type=1,  # Preview (video only)
        play_format=request.play_format  # 0=WebSocket, 2=WebRTC
    )
    
    logger.info(f"[{correlation_id}] Preview request with playFormat={request.play_format}")
    preview_result = manufacturer_api.open_preview(preview_data)
    preview_dto = MediaAdapter.parse_preview_response(preview_result, request.device_id, correlation_id + "_video")
    
    # Request 2: Get audio stream (Monitor - dataType=3)
    monitor_data = MediaAdapter.build_preview_request(
        device_id=request.device_id,
        channel=request.channel,
        stream_type=request.stream,
        data_type=3,  # Monitor (audio only)
        play_format=request.play_format  # 0=WebSocket, 2=WebRTC
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
        stream_type=1  # 0=main stream, 1=sub stream (using sub stream for faster loading)
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
    
    # Log full response for debugging
    logger.info(f"[{correlation_id}] Manufacturer API response: {result}")
    
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
        # Extract detailed error information
        data = result.get("data", {})
        error_code = data.get("errorCode", result.get("code"))
        error_desc = data.get("errorDesc", result.get("message", "Unknown error"))
        
        logger.error(f"[{correlation_id}] Intercom failed - Code: {error_code}, Message: {error_desc}")
        logger.error(f"[{correlation_id}] Full response: {result}")
        
        raise HTTPException(
            status_code=400,
            detail=f"Failed to start intercom (code {error_code}): {error_desc}"
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
    
    # Log full response for debugging
    logger.info(f"[{correlation_id}] Manufacturer API response: {result}")
    
    # Check if successful
    if result.get("code") == 200:
        return {
            "success": True,
            "message": "Intercom stopped successfully",
            "device_id": request.device_id
        }
    else:
        # Extract detailed error information
        data = result.get("data", {})
        error_code = data.get("errorCode", result.get("code"))
        error_desc = data.get("errorDesc", result.get("message", "Unknown error"))
        
        logger.error(f"[{correlation_id}] Stop intercom failed - Code: {error_code}, Message: {error_desc}")
        logger.error(f"[{correlation_id}] Full response: {result}")
        
        raise HTTPException(
            status_code=400,
            detail=f"Failed to stop intercom (code {error_code}): {error_desc}"
        )

@router.post("/file-list")
def get_file_list(
    request: FileListRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of actual video file segments available for a specific date.
    Returns the time periods where video recordings exist.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    from datetime import datetime, timedelta
    
    # Parse date and create start/end of day timestamps
    try:
        date_obj = datetime.strptime(request.date, "%Y-%m-%d")
        start_of_day = date_obj.replace(hour=0, minute=0, second=0)
        end_of_day = date_obj.replace(hour=23, minute=59, second=59)
        
        # Convert to Unix timestamps
        start_timestamp = int(start_of_day.timestamp())
        end_timestamp = int(end_of_day.timestamp())
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Build request for manufacturer API
    # Vendor API expects "channels" as an array
    file_list_data = {
        "deviceId": request.device_id,
        "channels": [request.channel],  # Array format required
        "startTime": start_timestamp,
        "endTime": end_timestamp,
        "mediaType": 2,  # 2=Video
        "streamType": 0,  # 0=all
        "storageType": 0  # 0=all
    }
    
    logger.info(f"📹 Getting file list for {request.device_id} on {request.date}")
    logger.info(f"   Request: {file_list_data}")
    
    # Call manufacturer API
    result = manufacturer_api.get_file_list(file_list_data)
    
    logger.info(f"   Vendor API response code: {result.get('code')}")
    logger.info(f"   Vendor API response: {result}")
    
    if result.get("code") == 200:
        data = result.get("data", {})
        logger.info(f"   Response data keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
        
        # Check different possible response structures
        media_list = None
        if isinstance(data, dict):
            # Try different possible keys - vendor uses "mediaFileLists"
            media_list = (
                data.get("mediaFileLists") or  # Vendor API actual key
                data.get("mediaList") or 
                data.get("media_list") or 
                data.get("files") or 
                data.get("list")
            )
        
        if media_list:
            logger.info(f"   Found media_list with {len(media_list)} items")
            logger.info(f"   First item sample: {media_list[0] if media_list else 'Empty'}")
            
            # Convert to simpler format with start/end times
            # Filter by requested channel if specified
            segments = []
            for media in media_list:
                # Filter by channel if specified (vendor returns all channels)
                media_channel = media.get("channel")
                if request.channel and media_channel != request.channel:
                    continue  # Skip if channel doesn't match
                
                # Handle different possible field names
                start_time = media.get("startTime") or media.get("start_time") or media.get("start")
                end_time = media.get("endTime") or media.get("end_time") or media.get("end")
                
                if start_time and end_time:
                    segments.append({
                        "start_time": int(start_time),  # Ensure it's an int
                        "end_time": int(end_time),      # Ensure it's an int
                        "channel": media_channel or request.channel,
                        "file_size": media.get("fileSize") or media.get("file_size") or 0
                    })
            
            logger.info(f"✅ Found {len(segments)} video segments")
            
            return {
                "success": True,
                "device_id": request.device_id,
                "date": request.date,
                "segments": segments,
                "total": len(segments)
            }
        else:
            logger.warning(f"⚠️ No mediaList found in response data")
            logger.warning(f"   Data structure: {data}")
    else:
        error_msg = result.get("message") or result.get("error") or "Unknown error"
        logger.error(f"❌ Vendor API error: {error_msg}")
    
    # No files found or error
    return {
        "success": True,
        "device_id": request.device_id,
        "date": request.date,
        "segments": [],
        "total": 0,
        "debug": {
            "vendor_code": result.get("code"),
            "vendor_message": result.get("message"),
            "has_data": bool(result.get("data"))
        }
    }

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

@router.get("/proxy")
async def proxy_video_stream(
    url: str = Query(..., description="Video stream URL to proxy"),
    current_user: dict = Depends(get_current_user)
):
    """
    Proxy video stream through backend to fix mixed content issues on web.
    This endpoint streams HTTP video URLs through HTTPS to avoid browser blocking.
    """
    try:
        # Validate URL (basic security check)
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Use httpx for async streaming
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream('GET', url) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to fetch video stream: {response.status_code}"
                    )
                
                # Stream the video content
                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                
                # Determine content type from response headers
                content_type = response.headers.get('content-type', 'video/mp4')
                
                return StreamingResponse(
                    generate(),
                    media_type=content_type,
                    headers={
                        'Cache-Control': 'no-cache',
                        'X-Accel-Buffering': 'no',
                    }
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Video stream timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to video stream: {str(e)}")
    except Exception as e:
        logger.error(f"Error proxying video stream: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.websocket("/ws-proxy")
async def websocket_video_proxy(
    websocket: WebSocket,
    url: str = Query(..., description="WebSocket URL to proxy (ws:// format)")
):
    """
    WebSocket proxy for live video streaming on web.
    Accepts wss:// connections from browser and forwards to ws:// vendor server.
    This solves the mixed content issue on HTTPS web pages.
    """
    await websocket.accept()
    
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] WebSocket proxy connecting to: {url}")
    
    vendor_ws = None
    
    try:
        # Connect to the vendor's WebSocket server
        # Use ws:// URL directly (backend can connect to insecure WebSocket)
        async with websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5
        ) as vendor_ws:
            logger.info(f"[{correlation_id}] Connected to vendor WebSocket")
            
            async def forward_to_client():
                """Forward data from vendor to browser client"""
                try:
                    async for message in vendor_ws:
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"[{correlation_id}] Vendor connection closed")
                except Exception as e:
                    logger.error(f"[{correlation_id}] Error forwarding to client: {e}")
            
            async def forward_to_vendor():
                """Forward data from browser client to vendor"""
                try:
                    while True:
                        try:
                            # Try to receive binary data first (video streams are binary)
                            data = await websocket.receive_bytes()
                            await vendor_ws.send(data)
                        except Exception:
                            # If not bytes, try text
                            try:
                                data = await websocket.receive_text()
                                await vendor_ws.send(data)
                            except WebSocketDisconnect:
                                logger.info(f"[{correlation_id}] Client disconnected")
                                break
                            except Exception as e:
                                logger.error(f"[{correlation_id}] Error receiving from client: {e}")
                                break
                except Exception as e:
                    logger.error(f"[{correlation_id}] Error forwarding to vendor: {e}")
            
            # Run both forwarding tasks concurrently
            forward_task = asyncio.create_task(forward_to_client())
            receive_task = asyncio.create_task(forward_to_vendor())
            
            # Wait for either task to complete (connection closed)
            done, pending = await asyncio.wait(
                [forward_task, receive_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
    except websockets.exceptions.InvalidURI:
        logger.error(f"[{correlation_id}] Invalid WebSocket URL: {url}")
        await websocket.close(code=1008, reason="Invalid WebSocket URL")
    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"[{correlation_id}] Vendor WebSocket returned status {e.status_code}")
        await websocket.close(code=1008, reason=f"Vendor returned {e.status_code}")
    except ConnectionRefusedError:
        logger.error(f"[{correlation_id}] Connection refused by vendor")
        await websocket.close(code=1008, reason="Connection refused")
    except asyncio.TimeoutError:
        logger.error(f"[{correlation_id}] Connection timeout")
        await websocket.close(code=1008, reason="Connection timeout")
    except WebSocketDisconnect:
        logger.info(f"[{correlation_id}] Client disconnected")
    except Exception as e:
        logger.error(f"[{correlation_id}] WebSocket proxy error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e)[:120])
        except:
            pass
    finally:
        logger.info(f"[{correlation_id}] WebSocket proxy connection closed")


