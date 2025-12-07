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
    
    # Vendor timezone: China time (UTC+8)
    VENDOR_TZ = timezone(timedelta(hours=8))
    
    # Vendor integer timestamps are offset due to timezone bug
    # Correction: China (UTC+8) - Saudi (UTC+3) = 5 hours
    VENDOR_INT_CORRECTION_SECONDS = 5 * 3600  # 5 hours = 18000 seconds
    
    @staticmethod
    def convert_timestamp_to_ms(timestamp: Optional[Any]) -> Optional[int]:
        """
        Convert vendor timestamp to milliseconds.
        
        Vendor may send:
        - Unix seconds (e.g., 1735888000) - corrected for timezone offset
        - Unix milliseconds (e.g., 1735888000000) - corrected for timezone offset
        - String format (e.g., "2024-01-01 12:00:00") in China time (UTC+8)
        
        Note: Vendor integer timestamps are 5 hours behind due to timezone bug.
        We add 5 hours to correct for Saudi Arabia (UTC+3) users.
        
        Args:
            timestamp: Timestamp in various formats
        
        Returns:
            Unix timestamp in milliseconds (UTC epoch), or None if invalid
        """
        if timestamp is None:
            return None
        
        # If it's already milliseconds (timestamp >= year 2286 in seconds = ~7e9)
        if isinstance(timestamp, int):
            if timestamp < 1_000_000_000_000:  # Less than year 2286 in ms
                # Likely seconds - add correction for vendor timezone bug
                corrected = timestamp + BaseAdapter.VENDOR_INT_CORRECTION_SECONDS
                return corrected * 1000
            else:
                # Already milliseconds - add correction for vendor timezone bug
                corrected = timestamp + (BaseAdapter.VENDOR_INT_CORRECTION_SECONDS * 1000)
                return corrected
        
        # If it's a string, try to parse
        if isinstance(timestamp, str):
            try:
                # Try common formats - vendor sends China time (UTC+8)
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                # Explicitly set timezone to China time (UTC+8)
                dt = dt.replace(tzinfo=BaseAdapter.VENDOR_TZ)
                return int(dt.timestamp() * 1000)
            except ValueError:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    return int(dt.timestamp() * 1000)
                except (ValueError, AttributeError):
                    logger.warning(f"Could not parse timestamp string: {timestamp}")
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
