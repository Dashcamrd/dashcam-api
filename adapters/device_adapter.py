"""
Device Adapter - Maps vendor Device API responses to stable DTOs.
"""
import logging
from typing import Optional, Dict, Any, List
from models.dto import AccStateDto, DeviceDto
from .base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class DeviceAdapter(BaseAdapter):
    """Adapter for device-related endpoints"""
    
    @staticmethod
    def parse_device_states_response(
        vendor_response: Dict[str, Any],
        device_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[AccStateDto]:
        """
        Parse vendor device states response into AccStateDto.
        
        Vendor response structure:
        {
            "code": 200,
            "data": {
                "list": [
                    {
                        "deviceId": "12345",
                        "state": 1,  # 0=offline, 1=online, 2=low power
                        "accState": 1,  # 0=off, 1=on
                        "lastOnlineTime": 1735888000  # Unix seconds
                    }
                ]
            }
        }
        
        Args:
            vendor_response: Raw vendor API response
            device_id: Device ID to extract state for
        
        Returns:
            AccStateDto or None if not found
        """
        try:
            # Validate response code using config
            success_codes = DeviceAdapter.get_response_success_codes("device_states", [200])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Device states response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return None
            
            # Extract device list using config-defined path
            device_list = DeviceAdapter.extract_response_data(vendor_response, "device_states", "data.list")
            
            # Fallback to manual extraction
            if device_list is None:
                data = vendor_response.get("data", {})
                device_list = data.get("list", [])
            
            if not device_list:
                device_list = []
            
            if not device_list or len(device_list) == 0:
                error_msg = f"No device state data found for device {device_id}"
                if correlation_id:
                    logger.debug(f"[{correlation_id}] {error_msg}")
                else:
                    logger.debug(error_msg)
                return AccStateDto(
                    deviceId=device_id,
                    acc_on=False,
                    last_online_time_ms=None
                )
            
            # Find device in list (should match device_id)
            device_state = None
            for d in device_list:
                if d.get("deviceId") == device_id:
                    device_state = d
                    break
            
            if not device_state:
                # If not found, return default
                return AccStateDto(
                    deviceId=device_id,
                    acc_on=False,
                    last_online_time_ms=None
                )
            
            # Parse ACC state
            acc_state_raw = device_state.get("accState", 0)
            acc_on = DeviceAdapter.normalize_acc_state(acc_state_raw)
            
            # NOTE: Device states endpoint does NOT return lastOnlineTime
            # The vendor API response only includes: deviceId, state, accState
            # Last online time must come from GPS endpoint, not device states
            # Setting last_online_time_ms to None to indicate it's not available here
            
            if correlation_id:
                logger.info(f"[{correlation_id}] Device state raw data: {device_state}")
                logger.info(f"[{correlation_id}] Device states endpoint does not provide lastOnlineTime - use GPS endpoint instead")
            
            return AccStateDto(
                deviceId=device_id,
                acc_on=acc_on,
                last_online_time_ms=None  # Not available from device states endpoint
            )
            
        except Exception as e:
            error_msg = f"Error parsing device states response: {e}"
            if correlation_id:
                logger.error(f"[{correlation_id}] {error_msg}", exc_info=True)
            else:
                logger.error(error_msg, exc_info=True)
            return AccStateDto(
                deviceId=device_id,
                acc_on=False,
                last_online_time_ms=None
            )
    
    @staticmethod
    def parse_device_list_response(
        vendor_response: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> List[DeviceDto]:
        """
        Parse vendor device list response into list of DeviceDto.
        
        Vendor response structure:
        {
            "code": 200,
            "data": {
                "list": [
                    {
                        "deviceId": "12345",
                        "plateNumber": "ABC123",
                        "state": 1,
                        "accState": 1,
                        "deviceName": "Vehicle 1"
                    }
                ],
                "total": 10
            }
        }
        
        Args:
            vendor_response: Raw vendor API response
        
        Returns:
            List of DeviceDto objects
        """
        devices: List[DeviceDto] = []
        
        try:
            # Validate response code using config
            success_codes = DeviceAdapter.get_response_success_codes("device_list", [200])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Device list response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return devices
            
            # Extract device list using config-defined path
            device_list = DeviceAdapter.extract_response_data(vendor_response, "device_list", "data.list")
            
            # Fallback to manual extraction
            if device_list is None:
                data = vendor_response.get("data", {})
                device_list = data.get("list", [])
            
            if not device_list:
                device_list = []
            
            for d in device_list:
                try:
                    device_id = d.get("deviceId")
                    if not device_id:
                        continue
                    
                    # Map fields
                    plate_no = d.get("plateNumber")
                    device_name = d.get("deviceName") or d.get("name")
                    
                    # Map state (0=offline, 1=online, 2=low power)
                    state_raw = d.get("state", 0)
                    online = DeviceAdapter.normalize_state_code(state_raw)
                    
                    # Map ACC state
                    acc_state_raw = d.get("accState", 0)
                    acc_on = DeviceAdapter.normalize_acc_state(acc_state_raw)
                    
                    devices.append(DeviceDto(
                        deviceId=device_id,
                        name=device_name,
                        plate_no=plate_no,
                        online=online,
                        acc_on=acc_on
                    ))
                except Exception as e:
                    logger.debug(f"Error parsing device entry: {e}, skipping")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing device list response: {e}", exc_info=True)
        
        return devices
    
    @staticmethod
    def build_device_states_request(device_ids: List[str]) -> Dict[str, Any]:
        """
        Build request for device states endpoint.
        
        Args:
            device_ids: List of device IDs to query
        
        Returns:
            Request dictionary
        """
        return {
            "deviceIds": device_ids
        }
    
    @staticmethod
    def build_device_list_request(
        page: int = 1,
        page_size: int = 10,
        company_id: Optional[int] = None,
        device_ids: Optional[List[str]] = None,
        plate_numbers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build request for device list endpoint.
        
        Args:
            page: Page number (starts at 1)
            page_size: Items per page
            company_id: Optional company ID filter
            device_ids: Optional device ID filter (max 1000)
            plate_numbers: Optional plate number filter (max 1000)
        
        Returns:
            Request dictionary
        """
        request: Dict[str, Any] = {
            "page": page,
            "pageSize": page_size
        }
        
        if company_id is not None:
            request["companyId"] = company_id
        
        if device_ids:
            request["deviceIds"] = device_ids[:1000]  # Limit to 1000
        
        if plate_numbers:
            request["plateNumbers"] = plate_numbers[:1000]  # Limit to 1000
        
        return request

