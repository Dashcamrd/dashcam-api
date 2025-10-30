"""
Media Adapter - Maps vendor Media API responses to stable DTOs.
"""
import logging
from typing import Optional, Dict, Any, List
from models.dto import MediaPreviewDto, VideoStreamDto
from .base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class MediaAdapter(BaseAdapter):
    """Adapter for media-related endpoints (preview, playback, intercom)"""
    
    @staticmethod
    def parse_preview_response(
        vendor_response: Dict[str, Any],
        device_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[MediaPreviewDto]:
        """
        Parse vendor preview response into MediaPreviewDto.
        
        Vendor response structure:
        {
            "code": 200,
            "data": {
                "videos": [
                    {
                        "deviceId": "12345",
                        "channel": 1,
                        "playUrl": "rtsp://...",
                        "streamType": 0,
                        "dataType": 1
                    }
                ]
            }
        }
        
        Args:
            vendor_response: Raw vendor API response
            device_id: Device ID for the preview
        
        Returns:
            MediaPreviewDto or None if no data found
        """
        try:
            # Validate response code using config
            success_codes = MediaAdapter.get_response_success_codes("media_preview", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Preview response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return None
            
            # Extract videos using config-defined path
            videos_raw = MediaAdapter.extract_response_data(vendor_response, "media_preview", "data.videos")
            
            # Fallback to manual extraction
            if videos_raw is None:
                data = vendor_response.get("data", {})
                videos_raw = data.get("videos", [])
            
            if not videos_raw:
                logger.debug(f"No video streams found in preview response for device {device_id}")
                return MediaPreviewDto(deviceId=device_id, videos=[])
            
            videos: List[VideoStreamDto] = []
            for v in videos_raw:
                try:
                    videos.append(VideoStreamDto(
                        deviceId=v.get("deviceId") or device_id,
                        channel=v.get("channel", 1),
                        playUrl=v.get("playUrl") or v.get("play_url", ""),
                        streamType=v.get("streamType") or v.get("stream_type", 0),
                        dataType=v.get("dataType") or v.get("data_type", 1)
                    ))
                except Exception as e:
                    logger.debug(f"Error parsing video stream: {e}, skipping")
                    continue
            
            return MediaPreviewDto(deviceId=device_id, videos=videos)
            
        except Exception as e:
            logger.error(f"Error parsing preview response: {e}", exc_info=True)
            return None
    
    @staticmethod
    def build_preview_request(
        device_id: str,
        channel: int = 1,
        data_type: int = 1,
        stream_type: int = 0
    ) -> Dict[str, Any]:
        """
        Build request for preview endpoint.
        
        Args:
            device_id: Device ID
            channel: Channel number (default: 1)
            data_type: 1=Preview, 3=Monitor (default: 1)
            stream_type: 0=main, 1=sub (default: 0)
        
        Returns:
            Request dictionary
        """
        return {
            "deviceId": device_id,
            "channels": [channel],
            "dataType": data_type,
            "streamType": stream_type
        }
    
    @staticmethod
    def build_close_preview_request(
        device_id: str,
        channels: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Build request for close preview endpoint.
        
        Args:
            device_id: Device ID
            channels: List of channels to close (default: [1])
        
        Returns:
            Request dictionary
        """
        return {
            "deviceId": device_id,
            "channels": channels or [1]
        }
    
    @staticmethod
    def build_playback_request(
        device_id: str,
        start_time: str,
        end_time: str,
        channel: int = 1,
        data_type: int = 1,
        stream_type: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build request for playback endpoint.
        
        Args:
            device_id: Device ID
            start_time: Start time string (format: "2024-01-01 10:00:00")
            end_time: End time string (format: "2024-01-01 11:00:00")
            channel: Channel number (default: 1)
            data_type: 1=Preview, 3=Monitor (default: 1)
            stream_type: Optional stream type (0=main, 1=sub)
        
        Returns:
            Request dictionary
        """
        request: Dict[str, Any] = {
            "deviceId": device_id,
            "channels": [channel],
            "startTime": start_time,
            "endTime": end_time,
            "dataType": data_type
        }
        
        if stream_type is not None:
            request["streamType"] = stream_type
        
        return request
    
    @staticmethod
    def build_close_playback_request(
        device_id: str,
        channels: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Build request for close playback endpoint.
        
        Args:
            device_id: Device ID
            channels: List of channels to close (default: [1])
        
        Returns:
            Request dictionary
        """
        return {
            "deviceId": device_id,
            "channels": channels or [1]
        }
    
    @staticmethod
    def build_intercom_request(
        device_id: str,
        channel: int = 1
    ) -> Dict[str, Any]:
        """
        Build request for two-way intercom endpoint.
        
        Args:
            device_id: Device ID
            channel: Channel number (default: 1)
        
        Returns:
            Request dictionary
        """
        return {
            "deviceId": device_id,
            "channel": channel
        }
    
    @staticmethod
    def parse_simple_response(vendor_response: Dict[str, Any]) -> bool:
        """
        Parse simple success/failure responses (for close, end operations).
        
        Args:
            vendor_response: Raw vendor API response
        
        Returns:
            True if successful, False otherwise
        """
        code = vendor_response.get("code")
        return code in (200, 0)

