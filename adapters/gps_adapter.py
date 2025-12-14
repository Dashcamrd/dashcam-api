"""
GPS Adapter - Maps vendor GPS API responses to stable DTOs.
"""
import logging
from typing import Optional, Dict, Any, List
from models.dto import LatestGpsDto, TrackPointDto, TrackPlaybackDto, AlarmDto
from .base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

# Alarm type mappings for alarmFlags
ALARM_FLAG_MAPPING = {
    "emergency": {"name": "Emergency SOS", "severity": "critical", "type_id": 1},
    "overspeed": {"name": "Overspeed", "severity": "warning", "type_id": 2},
    "fatigueDriving": {"name": "Driver Fatigue", "severity": "warning", "type_id": 3},
    "prewarning": {"name": "Pre-warning", "severity": "info", "type_id": 4},
    "gnssModuleFailure": {"name": "GPS Module Failure", "severity": "warning", "type_id": 5},
    "gnssAntennaShortCircuit": {"name": "GPS Antenna Short", "severity": "warning", "type_id": 6},
    "collision": {"name": "Collision Warning", "severity": "critical", "type_id": 7},
    "rollover": {"name": "Rollover Alert", "severity": "critical", "type_id": 8},
    "illegalIgnition": {"name": "Illegal Ignition", "severity": "warning", "type_id": 9},
    "illegalMobileDevice": {"name": "Illegal Mobile Device", "severity": "warning", "type_id": 10},
    "frontCollision": {"name": "Front Collision Warning", "severity": "critical", "type_id": 11},
    "laneDeparture": {"name": "Lane Departure Warning", "severity": "info", "type_id": 12},
    "pedestrianCollision": {"name": "Pedestrian Collision Warning", "severity": "critical", "type_id": 13},
    "headwayMonitoring": {"name": "Following Too Close", "severity": "warning", "type_id": 14},
    "harshBraking": {"name": "Harsh Braking", "severity": "warning", "type_id": 15},
    "harshAcceleration": {"name": "Harsh Acceleration", "severity": "info", "type_id": 16},
    "smoking": {"name": "Smoking Detected", "severity": "warning", "type_id": 17},
    "phoneUse": {"name": "Phone Use Detected", "severity": "warning", "type_id": 18},
    "driverAbsence": {"name": "Driver Absence", "severity": "warning", "type_id": 19},
    "yawning": {"name": "Yawning Detected", "severity": "info", "type_id": 20},
    "distracted": {"name": "Driver Distracted", "severity": "warning", "type_id": 21},
}


class GPSAdapter(BaseAdapter):
    """Adapter for GPS-related endpoints"""
    
    @staticmethod
    def parse_latest_gps_response(
        vendor_response: Dict[str, Any],
        device_id: str,
        correlation_id: Optional[str] = None,
        use_v2_only: bool = False
    ) -> Optional[LatestGpsDto]:
        """
        Parse vendor GPS response (v1 or v2) into LatestGpsDto.
        
        V2 response structure (getLatestGPS):
        {
            "code": 200,
            "data": {
                "list": [
                    {
                        "deviceId": "18270761136",
                        "gps": {
                            "latitude": 22.649954,  # Already in decimal
                            "longitude": 114.148194,  # Already in decimal
                            "speed": 359,  # 1/10 km/h units
                            "direction": 240,
                            "time": 1726934400,  # Unix seconds
                            "altitude": 73
                        },
                        "lastOnlineTime": 1726934500
                    }
                ]
            }
        }
        
        V1 response structure (gps/search):
        {
            "code": 200,
            "data": {
                "gpsInfo": [
                    {
                        "latitude": 5290439,  # 1e6 scaled
                        "longitude": 100291992,  # 1e6 scaled
                        "speed": 650,
                        "direction": 180,
                        "height": 50,
                        "time": 1735888000
                    }
                ]
            }
        }
        
        Args:
            vendor_response: Raw vendor API response
            device_id: Device ID for the GPS data
        
        Returns:
            LatestGpsDto or None if no data found
        """
        try:
            # Validate response structure
            success_codes = GPSAdapter.get_response_success_codes("gps_search_v1", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"GPS response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return None
            
            data = vendor_response.get("data", {})
            latest_gps = None
            
            # Try V2 format first (data.list[] with gps object)
            device_list = data.get("list", [])
            if device_list:
                # Find device in list
                for device_item in device_list:
                    if device_item.get("deviceId") == device_id:
                        gps_data = device_item.get("gps", {})
                        if gps_data:
                            # V2 format: coordinates already in decimal, no scaling needed
                            latitude = gps_data.get("latitude")
                            longitude = gps_data.get("longitude")
                            speed_raw = gps_data.get("speed")
                            # V2 speed is in 1/10 km/h units
                            speed_kmh = speed_raw / 10.0 if speed_raw is not None else None
                            direction_deg = gps_data.get("direction")
                            altitude_m = gps_data.get("altitude")
                            
                            # Use ONLY lastOnlineTime (no gps.time fallback)
                            if use_v2_only:
                                # Use lastOnlineTime as primary (no fallback to gps.time)
                                device_last_online = device_item.get("lastOnlineTime")
                                timestamp_ms = GPSAdapter.convert_timestamp_to_ms(device_last_online)
                            else:
                                # Original logic: Try gps.time first, then lastOnlineTime
                                gps_time = gps_data.get("time")
                                device_last_online = device_item.get("lastOnlineTime")
                                timestamp = gps_time or device_last_online
                                timestamp_ms = GPSAdapter.convert_timestamp_to_ms(timestamp)
                                if timestamp_ms is None and device_last_online:
                                    timestamp_ms = GPSAdapter.convert_timestamp_to_ms(device_last_online)
                            
                            address = None  # V2 doesn't include address
                            
                            if correlation_id:
                                logger.info(f"[{correlation_id}] Parsed V2 GPS response for device {device_id}")
                                if use_v2_only:
                                    logger.info(f"[{correlation_id}] Using ONLY lastOnlineTime: {device_item.get('lastOnlineTime')}")
                                else:
                                    logger.info(f"[{correlation_id}] gps.time: {gps_data.get('time')}, device.lastOnlineTime: {device_item.get('lastOnlineTime')}")
                                logger.info(f"[{correlation_id}] Final timestamp_ms: {timestamp_ms}")
                                logger.info(f"[{correlation_id}] Full device_item keys: {list(device_item.keys())}")
                                logger.info(f"[{correlation_id}] Full gps_data keys: {list(gps_data.keys())}")
                            
                            return LatestGpsDto(
                                deviceId=device_id,
                                latitude=latitude,
                                longitude=longitude,
                                speed_kmh=speed_kmh,
                                direction_deg=direction_deg,
                                altitude_m=altitude_m,
                                timestamp_ms=timestamp_ms,
                                address=address
                            )
            
            # If use_v2_only is True, don't try V1 fallback
            if use_v2_only:
                error_msg = f"No GPS data found in V2 response for device {device_id} (V1 fallback disabled)"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return None
            
            # Fallback to V1 format (data.gpsInfo[])
            gps_info = data.get("gpsInfo", [])
            
            if not gps_info or len(gps_info) == 0:
                error_msg = f"No GPS info found in response for device {device_id}"
                if correlation_id:
                    logger.debug(f"[{correlation_id}] {error_msg}")
                else:
                    logger.debug(error_msg)
                return None
            
            # Get first entry (latest) - V1 format
            latest_gps = gps_info[0]
            
            # Convert coordinates
            lat_raw = latest_gps.get("latitude")
            lng_raw = latest_gps.get("longitude")
            latitude = GPSAdapter.convert_raw_coords_to_decimal(lat_raw)
            longitude = GPSAdapter.convert_raw_coords_to_decimal(lng_raw)
            
            # Handle speed (may be in 0.1 km/h units, check if > 1000)
            speed_raw = latest_gps.get("speed")
            speed_kmh = None
            if speed_raw is not None:
                if isinstance(speed_raw, (int, float)):
                    # If speed > 1000, likely in 0.1 km/h units
                    speed_kmh = speed_raw / 10.0 if speed_raw > 1000 else float(speed_raw)
            
            # Handle direction
            direction_deg = latest_gps.get("direction")
            
            # Handle altitude
            altitude_m = latest_gps.get("height")
            
            # Handle timestamp
            timestamp = latest_gps.get("time") or latest_gps.get("timestamp")
            timestamp_ms = GPSAdapter.convert_timestamp_to_ms(timestamp)
            
            # Handle address (optional)
            address = latest_gps.get("address")
            
            return LatestGpsDto(
                deviceId=device_id,
                latitude=latitude,
                longitude=longitude,
                speed_kmh=speed_kmh,
                direction_deg=direction_deg,
                altitude_m=altitude_m,
                timestamp_ms=timestamp_ms,
                address=address
            )
            
        except Exception as e:
            error_msg = f"Error parsing latest GPS response: {e}"
            if correlation_id:
                logger.error(f"[{correlation_id}] {error_msg}", exc_info=True)
            else:
                logger.error(error_msg, exc_info=True)
            return None
    
    @staticmethod
    def parse_track_history_response(
        vendor_response: Dict[str, Any],
        device_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[TrackPlaybackDto]:
        """
        Parse vendor detailed track response into TrackPlaybackDto.
        
        Args:
            vendor_response: Raw vendor API response
            device_id: Device ID for the track
        
        Returns:
            TrackPlaybackDto or None if no data found
        """
        try:
            # Validate response code using config
            success_codes = GPSAdapter.get_response_success_codes("gps_query_detailed_track_v1", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Track history response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return None
            
            # Extract points using config-defined path (data.gpsInfo for gps_search_v1)
            raw_points = GPSAdapter.extract_response_data(vendor_response, "gps_query_detailed_track_v1", "data.gpsInfo")
            
            # Fallback to manual extraction
            if raw_points is None:
                data = vendor_response.get("data", {})
                raw_points = data.get("gpsInfo", []) or data.get("points", []) or []
            
            if not raw_points:
                raw_points = []
            
            points: List[TrackPointDto] = []
            for p in raw_points:
                try:
                    lat_raw = p.get("latitude")
                    lng_raw = p.get("longitude")
                    
                    # Skip if coordinates are missing
                    if lat_raw is None or lng_raw is None:
                        continue
                    
                    latitude = GPSAdapter.convert_raw_coords_to_decimal(lat_raw)
                    longitude = GPSAdapter.convert_raw_coords_to_decimal(lng_raw)
                    
                    # Skip if conversion failed
                    if latitude is None or longitude is None:
                        continue
                    
                    # Handle timestamp
                    ts = p.get("time") or p.get("timestamp")
                    timestamp_ms = GPSAdapter.convert_timestamp_to_ms(ts)
                    if timestamp_ms is None:
                        continue  # Skip points without valid timestamp
                    
                    # Handle speed
                    speed_raw = p.get("speed")
                    speed_kmh = None
                    if speed_raw is not None:
                        if isinstance(speed_raw, (int, float)):
                            speed_kmh = speed_raw / 10.0 if speed_raw > 1000 else float(speed_raw)
                    
                    # Handle direction
                    direction_deg = p.get("direction")
                    
                    points.append(TrackPointDto(
                        latitude=latitude,
                        longitude=longitude,
                        timestamp_ms=timestamp_ms,
                        speed_kmh=speed_kmh,
                        direction_deg=direction_deg
                    ))
                except Exception as e:
                    logger.debug(f"Error parsing track point: {e}, skipping point")
                    continue
            
            # Extract time range from first/last points or data
            # Use timestamps from points if available, otherwise try data fields
            if points:
                start_time_ms = points[0].timestamp_ms
                end_time_ms = points[-1].timestamp_ms
            else:
                start_time_ms = GPSAdapter.convert_timestamp_to_ms(data.get("startTime")) or 0
                end_time_ms = GPSAdapter.convert_timestamp_to_ms(data.get("endTime")) or 0
            
            return TrackPlaybackDto(
                deviceId=device_id,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                points=points
            )
            
        except Exception as e:
            error_msg = f"Error parsing track history response: {e}"
            if correlation_id:
                logger.error(f"[{correlation_id}] {error_msg}", exc_info=True)
            else:
                logger.error(error_msg, exc_info=True)
            return None
    
    @staticmethod
    def build_latest_gps_request(device_id: str, hours_back: int = 24) -> Dict[str, Any]:
        """
        Build request for getting latest GPS data.
        
        Args:
            device_id: Device ID to query
            hours_back: How many hours back to search (default 24)
        
        Returns:
            Request dictionary for GPS search endpoint
        """
        import time
        current_time = int(time.time())
        return {
            "deviceId": device_id,
            "startTime": current_time - (hours_back * 3600),
            "endTime": current_time
        }
    
    @staticmethod
    def build_detailed_track_request(
        device_id: str,
        start_time: int,
        end_time: int
    ) -> Dict[str, Any]:
        """
        Build request for detailed track query.
        
        Args:
            device_id: Device ID to query
            start_time: Unix timestamp in seconds
            end_time: Unix timestamp in seconds
        
        Returns:
            Request dictionary for detailed track endpoint
        """
        return {
            "deviceId": device_id,
            "startTime": start_time,
            "endTime": end_time
        }
    
    @staticmethod
    def parse_gps_alarms(
        vendor_response: Dict[str, Any],
        device_id: str,
        correlation_id: Optional[str] = None
    ) -> List[AlarmDto]:
        """
        Parse GPS search response and extract alarms from alarmFlags.
        
        Each GPS point may have an alarmFlags object with boolean fields.
        We extract points where any alarm flag is True.
        
        Args:
            vendor_response: Raw vendor API response from /api/v2/gps/search
            device_id: Device ID for the GPS data
            correlation_id: Optional correlation ID for logging
        
        Returns:
            List of AlarmDto objects extracted from GPS points with active alarms
        """
        try:
            # Validate response code
            success_codes = GPSAdapter.get_response_success_codes("gps_search_v1", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"GPS response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                return []
            
            # Extract GPS points from response
            data = vendor_response.get("data", {})
            
            # Try different response formats
            raw_points = data.get("list", []) or data.get("gpsInfo", []) or []
            
            if not raw_points:
                if correlation_id:
                    logger.info(f"[{correlation_id}] No GPS points in response")
                return []
            
            alarms: List[AlarmDto] = []
            seen_alarms = set()  # Deduplicate by (alarm_type, timestamp)
            
            for p in raw_points:
                try:
                    alarm_flags = p.get("alarmFlags", {})
                    
                    # Skip if no alarm flags or empty
                    if not alarm_flags:
                        continue
                    
                    # Check each alarm flag
                    for flag_name, is_active in alarm_flags.items():
                        if not is_active:
                            continue
                        
                        # Get alarm info from mapping
                        alarm_info = ALARM_FLAG_MAPPING.get(flag_name, {
                            "name": flag_name.replace("_", " ").title(),
                            "severity": "info",
                            "type_id": 0
                        })
                        
                        # Extract location
                        lat_raw = p.get("latitude")
                        lng_raw = p.get("longitude")
                        latitude = GPSAdapter.convert_raw_coords_to_decimal(lat_raw)
                        longitude = GPSAdapter.convert_raw_coords_to_decimal(lng_raw)
                        
                        # Extract timestamp
                        ts = p.get("time") or p.get("timestamp")
                        timestamp_ms = GPSAdapter.convert_timestamp_to_ms(ts)
                        
                        if timestamp_ms is None:
                            continue
                        
                        # Deduplicate
                        alarm_key = (flag_name, timestamp_ms)
                        if alarm_key in seen_alarms:
                            continue
                        seen_alarms.add(alarm_key)
                        
                        # Create alarm DTO using correct field names
                        alarm = AlarmDto(
                            alarm_id=f"{device_id}_{flag_name}_{timestamp_ms}",
                            device_id=device_id,
                            type_id=alarm_info["type_id"],
                            level=alarm_info["severity"],
                            message=alarm_info["name"],
                            timestamp_ms=timestamp_ms,
                            latitude=latitude,
                            longitude=longitude,
                            speed=p.get("speed", 0) / 10.0 if p.get("speed") else None,
                            status="active"
                        )
                        alarms.append(alarm)
                        
                except Exception as e:
                    logger.debug(f"Error parsing GPS point for alarms: {e}")
                    continue
            
            # Sort by timestamp (most recent first)
            alarms.sort(key=lambda a: a.timestamp_ms or 0, reverse=True)
            
            # 🔍 Detailed logging of alarm flags found in raw data
            if correlation_id:
                logger.info(f"[{correlation_id}] Extracted {len(alarms)} alarms from {len(raw_points)} GPS points")
                logger.info(f"[{correlation_id}] Our mapping has {len(ALARM_FLAG_MAPPING)} alarm types defined")
                
                # Log unique alarm flag names found across all points
                all_flags_seen = set()
                all_flag_names_in_response = set()  # All flag names, regardless of active/inactive
                points_with_flags = 0
                for p in raw_points:
                    alarm_flags = p.get("alarmFlags", {})
                    if alarm_flags:
                        points_with_flags += 1
                        for flag_name, is_active in alarm_flags.items():
                            all_flag_names_in_response.add(flag_name)
                            if is_active:
                                all_flags_seen.add(flag_name)
                
                logger.info(f"[{correlation_id}] GPS points with alarmFlags field: {points_with_flags}/{len(raw_points)}")
                logger.info(f"[{correlation_id}] Total unique alarm types in response: {len(all_flag_names_in_response)}")
                
                # Show which flags exist in response but NOT in our mapping
                unmapped_flags = all_flag_names_in_response - set(ALARM_FLAG_MAPPING.keys())
                if unmapped_flags:
                    logger.info(f"[{correlation_id}] ⚠️ Unmapped alarm types in response: {sorted(unmapped_flags)}")
                
                if all_flags_seen:
                    logger.info(f"[{correlation_id}] 🚨 Active alarm flags found: {sorted(all_flags_seen)}")
                else:
                    logger.info(f"[{correlation_id}] ⚪ No active alarm flags found in any GPS point")
                    # Log sample of what alarmFlags look like (first point with the field)
                    sample_points = [p for p in raw_points[:10] if p.get("alarmFlags")]
                    if sample_points:
                        sample_flags = sample_points[0].get('alarmFlags', {})
                        logger.info(f"[{correlation_id}] 🔍 Sample alarmFlags ({len(sample_flags)} types): {list(sample_flags.keys())}")
                    else:
                        # Log keys available in GPS points
                        if raw_points:
                            logger.info(f"[{correlation_id}] 🔍 GPS point keys available: {list(raw_points[0].keys())}")
            
            return alarms
            
        except Exception as e:
            error_msg = f"Error parsing GPS alarms: {e}"
            if correlation_id:
                logger.error(f"[{correlation_id}] {error_msg}", exc_info=True)
            return []

