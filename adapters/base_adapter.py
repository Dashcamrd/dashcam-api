"""
Base adapter utilities for common transformations.
"""
import logging
import uuid
import os
import yaml
from typing import Optional, Any, Dict
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class BaseAdapter:
    """Base class with common utility methods for adapters"""
    
    # Cache for config
    _config_cache: Optional[Dict[str, Any]] = None
    _config_path: str = "config/manufacturer_api.yaml"
    
    @classmethod
    def _load_config(cls) -> Dict[str, Any]:
        """Load API configuration from YAML file"""
        if cls._config_cache is not None:
            return cls._config_cache
        
        config_path = os.getenv("MANUFACTURER_API_CONFIG", cls._config_path)
        try:
            with open(config_path, 'r') as f:
                cls._config_cache = yaml.safe_load(f)
                return cls._config_cache
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}, adapters will use defaults")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            return {}
    
    @classmethod
    def get_endpoint_config(cls, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific endpoint"""
        config = cls._load_config()
        profile = os.getenv("MANUFACTURER_API_PROFILE", "default")
        
        if not config or "profiles" not in config:
            return None
        
        profile_config = config.get("profiles", {}).get(profile, {})
        endpoints = profile_config.get("endpoints", {})
        return endpoints.get(endpoint_name)
    
    @staticmethod
    def generate_correlation_id() -> str:
        """
        Generate a unique correlation ID for request tracing.
        
        Returns:
            UUID string for correlation
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def convert_raw_coords_to_decimal(raw_coord: Optional[int]) -> Optional[float]:
        """
        Convert vendor coordinate format (1e6 scaled) to decimal degrees.
        
        Args:
            raw_coord: Coordinate value multiplied by 1,000,000 (e.g., 5290439 = 5.290439°)
        
        Returns:
            Decimal degrees or None if input is invalid
        """
        if raw_coord is None:
            return None
        if isinstance(raw_coord, (int, float)):
            return raw_coord / 1_000_000.0
        return None
    
    # Vendor sends string timestamps in device's local timezone
    # For Saudi Arabia devices: UTC+3
    DEVICE_TZ = timezone(timedelta(hours=3))  # Saudi Arabia UTC+3
    
    # Vendor integer timestamps (lastOnlineTime, etc.) are 5 hours behind actual UTC
    # This is due to China (UTC+8) to Saudi (UTC+3) offset in vendor's system
    INTEGER_TS_CORRECTION_HOURS = 5
    
    @staticmethod
    def convert_timestamp_to_ms(timestamp: Optional[Any]) -> Optional[int]:
        """
        Convert vendor timestamp to milliseconds.
        
        Integer timestamps need +5 hours correction (vendor offset issue).
        String timestamps are treated as UTC.
        """
        if timestamp is None:
            return None
        
        if isinstance(timestamp, int):
            # Add 5 hours correction for vendor integer timestamps
            correction_seconds = BaseAdapter.INTEGER_TS_CORRECTION_HOURS * 3600
            if timestamp < 1_000_000_000_000:
                # Seconds - add correction then convert to ms
                return (timestamp + correction_seconds) * 1000
            else:
                # Already milliseconds - add correction in ms
                return timestamp + (correction_seconds * 1000)
        
        if isinstance(timestamp, str):
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp() * 1000)
            except ValueError:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    return int(dt.timestamp() * 1000)
                except (ValueError, AttributeError):
                    return None
        
        return None
    
    @staticmethod
    def convert_track_timestamp_to_ms(timestamp: Optional[Any]) -> Optional[int]:
        """
        Convert track history timestamp to milliseconds.
        
        String timestamps from track history are in DEVICE LOCAL TIME (Saudi = UTC+3).
        We need to treat them as Saudi time and convert to proper UTC epoch.
        
        Example:
        - Vendor sends: "2025-12-15 18:38:00" (Saudi local time)
        - We interpret as: 18:38 Saudi = 15:38 UTC
        - Store as UTC epoch milliseconds
        - Flutter displays in local timezone correctly
        """
        if timestamp is None:
            return None
        
        # Integer timestamps are already UTC epoch
        if isinstance(timestamp, int):
            if timestamp < 1_000_000_000_000:
                return timestamp * 1000
            else:
                return timestamp
        
        # String timestamps are in device local time (Saudi = UTC+3)
        if isinstance(timestamp, str):
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                # Treat as Saudi local time (UTC+3), not UTC
                dt = dt.replace(tzinfo=BaseAdapter.DEVICE_TZ)
                return int(dt.timestamp() * 1000)
            except ValueError:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    return int(dt.timestamp() * 1000)
                except (ValueError, AttributeError):
                    return None
        
        return None
    
    @staticmethod
    def extract_nested_value(data: Dict, path: str, default: Any = None) -> Any:
        """
        Extract value from nested dictionary using dot-notation path.
        
        Args:
            data: Dictionary to extract from
            path: Dot-separated path (e.g., "data.gpsInfo.0.latitude")
            default: Default value if path not found
        
        Returns:
            Extracted value or default
        """
        parts = path.split(".")
        value = data
        try:
            for part in parts:
                # Try as dict key first
                if isinstance(value, dict):
                    value = value.get(part)
                # Try as list index
                elif isinstance(value, list):
                    value = value[int(part)]
                else:
                    return default
                if value is None:
                    return default
            return value
        except (KeyError, IndexError, ValueError, TypeError):
            return default
    
    @staticmethod
    def normalize_state_code(state: Optional[int]) -> Optional[bool]:
        """
        Convert vendor state code to boolean (online/offline).
        
        Vendor codes:
        - 0: offline
        - 1: online
        - 2: low power (treated as offline)
        
        Args:
            state: State code from vendor
        
        Returns:
            True if online (1), False otherwise
        """
        if state is None:
            return None
        return state == 1
    
    @staticmethod
    def normalize_acc_state(acc_state: Optional[int]) -> Optional[bool]:
        """
        Convert vendor ACC state code to boolean.
        
        Args:
            acc_state: ACC state (0=off, 1=on)
        
        Returns:
            Boolean or None
        """
        if acc_state is None:
            return None
        return acc_state == 1
    
    @staticmethod
    def validate_response_structure(
        vendor_response: Dict[str, Any],
        required_fields: list,
        correlation_id: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that vendor response has required structure.
        
        Args:
            vendor_response: Raw vendor API response
            required_fields: List of required field paths (dot notation)
            correlation_id: Optional correlation ID for logging
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(vendor_response, dict):
            error_msg = "Response is not a dictionary"
            if correlation_id:
                logger.warning(f"[{correlation_id}] {error_msg}")
            return False, error_msg
        
        for field_path in required_fields:
            value = BaseAdapter.extract_nested_value(vendor_response, field_path)
            if value is None:
                error_msg = f"Missing required field: {field_path}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                return False, error_msg
        
        return True, None
    
    @classmethod
    def get_response_data_path(cls, endpoint_name: str, default_path: Optional[str] = None) -> Optional[str]:
        """
        Get response data path from config for an endpoint.
        
        Args:
            endpoint_name: Internal endpoint name
            default_path: Default path if not in config
        
        Returns:
            Data path string (dot notation) or None
        """
        endpoint_config = cls.get_endpoint_config(endpoint_name)
        if endpoint_config and "response" in endpoint_config:
            return endpoint_config["response"].get("data_path", default_path)
        return default_path
    
    @classmethod
    def get_response_success_codes(cls, endpoint_name: str, default_codes: list = [200, 0]) -> list:
        """
        Get success codes from config for an endpoint.
        
        Args:
            endpoint_name: Internal endpoint name
            default_codes: Default success codes
        
        Returns:
            List of success codes
        """
        endpoint_config = cls.get_endpoint_config(endpoint_name)
        if endpoint_config and "response" in endpoint_config:
            return endpoint_config["response"].get("success_codes", default_codes)
        return default_codes
    
    @classmethod
    def extract_response_data(cls, vendor_response: Dict[str, Any], endpoint_name: str, default_path: Optional[str] = None) -> Any:
        """
        Extract data from vendor response using config-defined path.
        
        Args:
            vendor_response: Raw vendor API response
            endpoint_name: Internal endpoint name
            default_path: Default path if not in config
        
        Returns:
            Extracted data or None
        """
        data_path = cls.get_response_data_path(endpoint_name, default_path)
        if data_path:
            return cls.extract_nested_value(vendor_response, data_path)
        
        # Fallback to default locations
        return vendor_response.get("data")
