"""
Statistics Adapter - Maps vendor Statistics and Alarm API responses to stable DTOs.
"""
import logging
from typing import Optional, Dict, Any, List
from models.dto import AlarmDto, AlarmSummaryDto, VehicleStatisticsDto, VehicleDetailDto
from .base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class StatisticsAdapter(BaseAdapter):
    """Adapter for statistics and alarm-related endpoints"""
    
    @staticmethod
    def parse_alarm_response(
        vendor_response: Dict[str, Any],
        device_id: str,
        correlation_id: Optional[str] = None
    ) -> AlarmSummaryDto:
        """
        Parse vendor alarm response into AlarmSummaryDto.
        
        Vendor response structure (getVehicleAlarm):
        {
            "code": 200,
            "data": {
                "vehicles": [
                    {
                        "deviceId": "12345",
                        "alarm": {
                            "typeId": 1,
                            "level": 1,  # 1=critical, 2=warning, 3=info
                            "id": "alarm_123",
                            "latitude": 5290439,
                            "longitude": 100291992,
                            "happenAt": 1735888000,
                            ...
                        }
                    }
                ]
            }
        }
        
        Args:
            vendor_response: Raw vendor API response
            device_id: Device ID
        
        Returns:
            AlarmSummaryDto
        """
        alarms: List[AlarmDto] = []
        critical_count = 0
        warning_count = 0
        info_count = 0
        
        try:
            # Validate response code using config
            success_codes = StatisticsAdapter.get_response_success_codes("stat_realtime_get_vehicle_alarm", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Alarm response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return AlarmSummaryDto(
                    deviceId=device_id,
                    total_alarms=0,
                    critical_count=0,
                    warning_count=0,
                    info_count=0,
                    alarms=[]
                )
            
            # Extract alarms using config-defined path
            data = vendor_response.get("data", {})
            
            # Handle different response structures
            vehicles = data.get("vehicles", [])
            alarms_raw = StatisticsAdapter.extract_response_data(vendor_response, "stat_realtime_get_vehicle_alarm", "data.alarms") or []
            
            # If vehicles structure, extract alarms from each vehicle
            if vehicles:
                for vehicle in vehicles:
                    alarm_data = vehicle.get("alarm")
                    if alarm_data:
                        alarms_raw.append({
                            **alarm_data,
                            "deviceId": vehicle.get("deviceId", device_id)
                        })
            
            for alarm_raw in alarms_raw:
                try:
                    # Normalize level (vendor may use 1/2/3 or strings)
                    level_raw = alarm_raw.get("level")
                    level = None
                    if isinstance(level_raw, int):
                        level_map = {1: "critical", 2: "warning", 3: "info"}
                        level = level_map.get(level_raw, "info")
                    elif isinstance(level_raw, str):
                        level = level_raw.lower()
                    
                    # Count by level
                    if level == "critical":
                        critical_count += 1
                    elif level == "warning":
                        warning_count += 1
                    else:
                        info_count += 1
                    
                    # Convert coordinates
                    lat_raw = alarm_raw.get("latitude")
                    lng_raw = alarm_raw.get("longitude")
                    latitude = StatisticsAdapter.convert_raw_coords_to_decimal(lat_raw)
                    longitude = StatisticsAdapter.convert_raw_coords_to_decimal(lng_raw)
                    
                    # Convert timestamp
                    happen_at = alarm_raw.get("happenAt") or alarm_raw.get("timestamp")
                    timestamp_ms = StatisticsAdapter.convert_timestamp_to_ms(happen_at)
                    
                    # Extract alarm ID
                    alarm_id = str(alarm_raw.get("id") or alarm_raw.get("alarmId") or "")
                    if not alarm_id:
                        continue  # Skip alarms without ID
                    
                    alarms.append(AlarmDto(
                        alarmId=alarm_id,
                        deviceId=alarm_raw.get("deviceId") or device_id,
                        typeId=alarm_raw.get("typeId"),
                        level=level,
                        message=alarm_raw.get("message") or alarm_raw.get("msg"),
                        timestampMs=timestamp_ms,
                        latitude=latitude,
                        longitude=longitude,
                        address=alarm_raw.get("address"),
                        speed=alarm_raw.get("speed"),
                        altitude=alarm_raw.get("altitude"),
                        hasAttachment=alarm_raw.get("hasAttachment", False),
                        status=alarm_raw.get("status", "active")
                    ))
                except Exception as e:
                    logger.debug(f"Error parsing alarm entry: {e}, skipping")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing alarm response: {e}", exc_info=True)
        
        return AlarmSummaryDto(
            deviceId=device_id,
            total_alarms=len(alarms),
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            alarms=alarms
        )
    
    @staticmethod
    def parse_vehicle_statistics_response(
        vendor_response: Dict[str, Any],
        device_id: str,
        date_range: str,
        correlation_id: Optional[str] = None
    ) -> Optional[VehicleStatisticsDto]:
        """
        Parse vendor vehicle statistics response into VehicleStatisticsDto.
        
        Args:
            vendor_response: Raw vendor API response
            device_id: Device ID
            date_range: Human-readable date range string
        
        Returns:
            VehicleStatisticsDto or None if not found
        """
        try:
            # Validate response code using config
            success_codes = StatisticsAdapter.get_response_success_codes("stat_history_get_vehicle_statistic", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Statistics response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return None
            
            data = vendor_response.get("data", {})
            
            # Map vendor field names to DTO fields
            return VehicleStatisticsDto(
                deviceId=device_id,
                date_range=date_range,
                totalDistanceKm=data.get("totalDistance") or data.get("total_distance"),
                totalDurationS=data.get("totalDuration") or data.get("total_duration"),
                averageSpeedKmh=data.get("averageSpeed") or data.get("average_speed"),
                maxSpeedKmh=data.get("maxSpeed") or data.get("max_speed"),
                totalStops=data.get("totalStops") or data.get("total_stops"),
                fuel_consumption=data.get("fuelConsumption") or data.get("fuel_consumption"),
                idleTimeS=data.get("idleTime") or data.get("idle_time"),
                totalAlarms=data.get("totalAlarms") or data.get("total_alarms")
            )
            
        except Exception as e:
            logger.error(f"Error parsing vehicle statistics response: {e}", exc_info=True)
            return None
    
    @staticmethod
    def parse_vehicle_detail_response(
        vendor_response: Dict[str, Any],
        device_id: str,
        date: str
    ) -> Optional[VehicleDetailDto]:
        """
        Parse vendor vehicle detail response into VehicleDetailDto.
        
        Args:
            vendor_response: Raw vendor API response
            device_id: Device ID
            date: Date string
        
        Returns:
            VehicleDetailDto or None if not found
        """
        try:
            code = vendor_response.get("code")
            if code not in (200, 0):
                logger.warning(f"Vehicle detail response has non-success code: {code}")
                return None
            
            data = vendor_response.get("data", {})
            
            # Parse alarms if present
            alarms: List[AlarmDto] = []
            alarms_raw = data.get("alarms", [])
            for alarm_raw in alarms_raw:
                try:
                    alarm_id = str(alarm_raw.get("id") or alarm_raw.get("alarmId", ""))
                    if not alarm_id:
                        continue
                    
                    level_raw = alarm_raw.get("level")
                    level = None
                    if isinstance(level_raw, int):
                        level_map = {1: "critical", 2: "warning", 3: "info"}
                        level = level_map.get(level_raw, "info")
                    elif isinstance(level_raw, str):
                        level = level_raw.lower()
                    
                    alarms.append(AlarmDto(
                        alarmId=alarm_id,
                        deviceId=device_id,
                        typeId=alarm_raw.get("typeId"),
                        level=level,
                        message=alarm_raw.get("message"),
                        timestampMs=StatisticsAdapter.convert_timestamp_to_ms(alarm_raw.get("timestamp") or alarm_raw.get("happenAt")),
                        latitude=StatisticsAdapter.convert_raw_coords_to_decimal(alarm_raw.get("latitude")),
                        longitude=StatisticsAdapter.convert_raw_coords_to_decimal(alarm_raw.get("longitude")),
                        address=alarm_raw.get("address"),
                        speed=alarm_raw.get("speed"),
                        altitude=alarm_raw.get("altitude"),
                        hasAttachment=alarm_raw.get("hasAttachment", False),
                        status=alarm_raw.get("status", "active")
                    ))
                except Exception:
                    continue
            
            return VehicleDetailDto(
                deviceId=device_id,
                date=date,
                trips=data.get("trips", []),
                stops=data.get("stops", []),
                alarms=alarms,
                totalDistanceKm=data.get("totalDistance") or data.get("total_distance"),
                totalDurationS=data.get("totalDuration") or data.get("total_duration")
            )
            
        except Exception as e:
            logger.error(f"Error parsing vehicle detail response: {e}", exc_info=True)
            return None
    
    @staticmethod
    def build_alarm_query_request(
        device_ids: List[str],
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Build request for alarm query endpoint.
        
        Args:
            device_ids: List of device IDs
            start_time: Optional start time (Unix seconds)
            end_time: Optional end time (Unix seconds)
            page: Page number (default: 1)
            page_size: Items per page (default: 10)
        
        Returns:
            Request dictionary
        """
        request: Dict[str, Any] = {
            "deviceIds": device_ids,
            "pageArg": {
                "page": page,
                "pageSize": page_size
            }
        }
        
        if start_time:
            request["start"] = start_time
        if end_time:
            request["end"] = end_time
        
        return request
    
    @staticmethod
    def build_vehicle_statistics_request(
        device_ids: List[str],
        start_time: int,
        end_time: int
    ) -> Dict[str, Any]:
        """
        Build request for vehicle statistics endpoint.
        
        Args:
            device_ids: List of device IDs
            start_time: Start time (Unix seconds)
            end_time: End time (Unix seconds)
        
        Returns:
            Request dictionary
        """
        return {
            "deviceIds": device_ids,
            "startTime": start_time,
            "endTime": end_time
        }
    
    @staticmethod
    def build_vehicle_detail_request(
        device_id: str,
        start_time: int,
        end_time: int
    ) -> Dict[str, Any]:
        """
        Build request for vehicle detail endpoint.
        
        Args:
            device_id: Device ID
            start_time: Start time (Unix seconds)
            end_time: End time (Unix seconds)
        
        Returns:
            Request dictionary
        """
        return {
            "deviceId": device_id,
            "startTime": start_time,
            "endTime": end_time
        }

