"""
Manufacturer API Service - Handles all communication with the MDVR platform API
"""
import requests
import os
import hashlib
import yaml
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
from collections import deque
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ManufacturerAPIService:
    """Service for interacting with the manufacturer's MDVR API"""
    
    def __init__(self):
        # Load YAML configuration
        self.config = self._load_config()
        self.profile = os.getenv("MANUFACTURER_API_PROFILE", "default")
        
        # Get base URL from config or env
        profile_config = self.config["profiles"][self.profile]
        self.base_url = os.getenv(
            profile_config.get("base_url_env", "MANUFACTURER_API_BASE_URL"),
            profile_config.get("base_url", "https://www.chinamdvr.com:9367")
        )
        
        self.username = os.getenv("MANUFACTURER_API_USERNAME")
        self.password = os.getenv("MANUFACTURER_API_PASSWORD")
        
        # Token management - start with no token, will be fetched on first use
        self.token = None
        self.token_expires_at = None
        
        # Rate limiting - track request timestamps
        rate_limit = profile_config.get("rate_limit_per_minute", 0)
        self.rate_limit_enabled = rate_limit > 0
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max = rate_limit
        self.request_timestamps: deque = deque(maxlen=rate_limit if rate_limit > 0 else 1000)
        
        # Global defaults from config
        self.default_timeout = profile_config.get("default_timeout", 30)
        self.default_retries = profile_config.get("default_retries", 3)
        self.default_retry_delay = profile_config.get("default_retry_delay", 1)
        
        logger.info(f"🔧 Manufacturer API Config (Profile: {self.profile}):")
        logger.info(f"   Base URL: {self.base_url}")
        logger.info(f"   Username: {self.username}")
        logger.info(f"   Password: {'***' if self.password else 'NOT_SET'}")
        logger.info(f"   Token: Will be fetched automatically on first use")
        logger.info(f"   Endpoints loaded: {len(profile_config.get('endpoints', {}))}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load API configuration from YAML file"""
        config_path = os.getenv("MANUFACTURER_API_CONFIG", "config/manufacturer_api.yaml")
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"❌ Manufacturer API config file not found at {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"❌ Error parsing YAML config file {config_path}: {e}")
            raise
    
    def _get_endpoint_config(self, endpoint_name: str) -> Dict[str, Any]:
        """Get configuration for a specific endpoint"""
        profile_config = self.config["profiles"][self.profile]
        endpoint_config = profile_config.get("endpoints", {}).get(endpoint_name)
        if not endpoint_config:
            raise ValueError(f"Endpoint '{endpoint_name}' not found in config for profile '{self.profile}'")
        return endpoint_config
    
    def _build_request_data(self, endpoint_name: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Build request data by applying defaults and validating required fields"""
        endpoint_config = self._get_endpoint_config(endpoint_name)
        request_config = endpoint_config.get("request", {})
        
        # Start with provided data or empty dict
        request_data = data.copy() if data else {}
        
        # Apply defaults
        defaults = request_config.get("defaults", {})
        for key, value in defaults.items():
            if key not in request_data:
                request_data[key] = value
        
        # Validate required fields (if any are specified)
        required = request_config.get("required", [])
        if required:
            missing = [field for field in required if field not in request_data]
            if missing:
                raise ValueError(f"Missing required fields for endpoint '{endpoint_name}': {missing}")
        
        return request_data
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        if not self.token or self._is_token_expired():
            logger.info("🔄 Token expired or missing, refreshing token...")
            refresh_success = self._refresh_token()
            if not refresh_success:
                logger.error("❌ Failed to refresh token!")
                raise Exception("Failed to refresh manufacturer API token")
            logger.info("✅ Token refreshed successfully")
        
        return {
            "Content-Type": "application/json",
            "X-Token": self.token
        }
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired"""
        if not self.token_expires_at:
            return True
        return datetime.now() >= self.token_expires_at
    
    def _refresh_token(self) -> bool:
        """Refresh authentication token using configured login endpoint"""
        try:
            if not self.username or not self.password:
                logger.error("❌ Manufacturer API credentials not configured")
                return False
            
            # Get login endpoint config
            login_config = self._get_endpoint_config("login")
            endpoint_path = login_config["path"]
            
            # Hash password with MD5 as required by manufacturer API
            password_hash = hashlib.md5(self.password.encode()).hexdigest()
            
            # Build login data with defaults from config
            login_data = self._build_request_data("login", {
                "username": self.username,
                "password": password_hash
            })
            
            logger.info(f"🔄 Attempting to login to manufacturer API with username: {self.username}")
            
            # Get timeout from config or use default
            timeout = self.default_timeout
            if login_config.get("timeout"):
                timeout = login_config.get("timeout")
            
            response = requests.post(
                f"{self.base_url}{endpoint_path}",
                json=login_data,
                timeout=timeout
            )
            
            logger.info(f"📡 Login response status: {response.status_code}")
            logger.info(f"📡 Login response: {response.text[:200]}...")
            
            if response.status_code == 200:
                result = response.json()
                
                # Check success codes from config
                success_codes = login_config.get("response", {}).get("success_codes", [200, 0])
                code = result.get("code")
                
                if code in success_codes or result.get("message") == "success":
                    # Try token paths from config
                    token_paths = login_config.get("response", {}).get("token_paths", [
                        "data.token", "token", "data.accessToken", "accessToken"
                    ])
                    
                    token = None
                    for path in token_paths:
                        parts = path.split(".")
                        value = result
                        try:
                            for part in parts:
                                value = value[part]
                            if value:
                                token = value
                                break
                        except (KeyError, TypeError):
                            continue
                    
                    if token:
                        self.token = token
                        # Set token to expire in 23 hours (1 hour before actual expiry)
                        self.token_expires_at = datetime.now() + timedelta(hours=23)
                        logger.info(f"✅ Successfully refreshed manufacturer API token: {self.token[:20]}...")
                        logger.info(f"⏰ Token expires at: {self.token_expires_at}")
                        return True
                    else:
                        logger.error(f"❌ Login successful but no token found in response: {result}")
                        return False
                else:
                    logger.error(f"❌ Login failed: {result.get('message', 'Unknown error')}, code: {code}")
                    return False
            else:
                logger.error(f"❌ Login request failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error refreshing token: {str(e)}")
            return False
    
    def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid token, refresh if needed"""
        if not self.token or self._is_token_expired():
            logger.info("🔄 No valid token found, attempting to refresh...")
            return self._refresh_token()
        return True
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limit, wait if necessary"""
        if not self.rate_limit_enabled:
            return True
        
        now = time.time()
        # Remove timestamps outside the window
        while self.request_timestamps and (now - self.request_timestamps[0]) > self.rate_limit_window:
            self.request_timestamps.popleft()
        
        # Check if we're at the limit
        if len(self.request_timestamps) >= self.rate_limit_max:
            # Calculate wait time until oldest request expires
            oldest = self.request_timestamps[0]
            wait_time = self.rate_limit_window - (now - oldest) + 0.1  # Add small buffer
            if wait_time > 0:
                logger.warning(f"⏳ Rate limit reached ({self.rate_limit_max}/min), waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                # Clean up again after waiting
                now = time.time()
                while self.request_timestamps and (now - self.request_timestamps[0]) > self.rate_limit_window:
                    self.request_timestamps.popleft()
        
        # Record this request
        self.request_timestamps.append(time.time())
        return True
    
    def _make_request(
        self, 
        endpoint_name: str, 
        data: Optional[Dict] = None, 
        method: Optional[str] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make authenticated request to manufacturer API using configured endpoint details"""
        try:
            # Get endpoint configuration
            endpoint_config = self._get_endpoint_config(endpoint_name)
            endpoint_path = endpoint_config["path"]
            http_method = method or endpoint_config.get("method", "POST")
            
            # Get endpoint-specific settings
            timeout = endpoint_config.get("timeout", self.default_timeout)
            max_retries = endpoint_config.get("retries", self.default_retries)
            retry_delay = endpoint_config.get("retry_delay", self.default_retry_delay)
            
            # Check rate limit before making request
            if not self._check_rate_limit():
                return {"code": -1, "message": "Rate limit exceeded"}
            
            # Build request data with validation and defaults
            request_data = self._build_request_data(endpoint_name, data)
            
            # Skip auth for login endpoint
            if endpoint_name == "login":
                headers = {"Content-Type": "application/json"}
            else:
                # Ensure we have a valid token before making the request
                if not self._ensure_valid_token():
                    logger.error("❌ Failed to get valid token for API request")
                    return {"code": -1, "message": "Authentication failed - unable to get valid token"}
                headers = self._get_headers()
            
            url = f"{self.base_url}{endpoint_path}"
            
            # Generate correlation ID for request tracing - ensure uniqueness
            import time as time_module
            correlation_id = f"{str(uuid.uuid4())[:6]}{int(time_module.time() * 1000) % 10000}"
            attempt_text = f" (attempt {retry_count + 1}/{max_retries + 1})" if retry_count > 0 else ""
            
            logger.info(f"📡 [{correlation_id}] Making {http_method} request to {url} (endpoint: {endpoint_name}, timeout: {timeout}s{attempt_text})")
            if retry_count == 0:  # Only log request data on first attempt
                logger.info(f"📡 [{correlation_id}] Request data: {request_data}")
                logger.info(f"📡 [{correlation_id}] Full URL: {url}")
                logger.info(f"📡 [{correlation_id}] Headers: {dict(headers) if 'headers' in locals() else 'N/A'}")
            
            try:
                if http_method.upper() == "GET":
                    response = requests.get(url, params=request_data, headers=headers, timeout=timeout)
                else:
                    response = requests.post(url, json=request_data, headers=headers, timeout=timeout)
            except requests.exceptions.Timeout as e:
                logger.warning(f"⏱️  [{correlation_id}] Request timeout after {timeout}s")
                
                # Retry with exponential backoff
                if retry_count < max_retries:
                    delay = retry_delay * (2 ** retry_count)  # Exponential backoff
                    logger.info(f"🔄 [{correlation_id}] Retrying in {delay}s...")
                    time.sleep(delay)
                    return self._make_request(endpoint_name, data, method, retry_count + 1)
                else:
                    return {"code": -1, "message": f"Request timeout after {max_retries + 1} attempts"}
            
            except requests.exceptions.ConnectionError as e:
                logger.error(f"❌ [{correlation_id}] Connection error: {e}")
                
                # Retry connection errors
                if retry_count < max_retries:
                    delay = retry_delay * (2 ** retry_count)
                    logger.info(f"🔄 [{correlation_id}] Retrying connection in {delay}s...")
                    time.sleep(delay)
                    return self._make_request(endpoint_name, data, method, retry_count + 1)
                else:
                    return {"code": -1, "message": f"Connection failed after {max_retries + 1} attempts: {str(e)}"}
            
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ [{correlation_id}] Request error: {e}")
                
                # Retry other request exceptions
                if retry_count < max_retries:
                    delay = retry_delay * (2 ** retry_count)
                    logger.info(f"🔄 [{correlation_id}] Retrying in {delay}s...")
                    time.sleep(delay)
                    return self._make_request(endpoint_name, data, method, retry_count + 1)
                else:
                    return {"code": -1, "message": f"Request failed after {max_retries + 1} attempts: {str(e)}"}
            
            logger.info(f"📡 [{correlation_id}] Response status: {response.status_code}")
            logger.info(f"📡 [{correlation_id}] Response text: {response.text[:200]}...")
            
            if response.status_code == 200:
                try:
                    # Try to parse as JSON first
                    json_response = response.json()
                    logger.info(f"✅ [{correlation_id}] Successfully parsed JSON response")
                    
                    # Check if token is invalid/expired (error code 1008)
                    if json_response.get("code") == 1008:  # Invalid token error
                        logger.warning(f"⚠️ [{correlation_id}] Token expired during request, refreshing and retrying...")
                        self.token = None  # Force token refresh
                        if self._ensure_valid_token():
                            # Retry the request with new token
                            headers = self._get_headers()
                            if http_method.upper() == "GET":
                                response = requests.get(url, params=request_data, headers=headers, timeout=30)
                            else:
                                response = requests.post(url, json=request_data, headers=headers, timeout=30)
                            if response.status_code == 200:
                                return response.json()
                    
                    return json_response
                except ValueError as e:
                    # If not JSON, treat as plain text response
                    text_response = response.text.strip()
                    logger.info(f"⚠️ [{correlation_id}] JSON parsing failed: {e}")
                    logger.info(f"📄 [{correlation_id}] Non-JSON response received: {text_response}")
                    
                    # Handle different text responses
                    if text_response == "success":
                        return {"code": 0, "message": "success", "data": {}}
                    elif "error" in text_response.lower():
                        return {"code": -1, "message": text_response}
                    else:
                        return {"code": 0, "message": text_response, "data": {}}
            else:
                # Log full response for debugging
                logger.error(f"❌ [{correlation_id}] API request failed: {response.status_code}")
                logger.error(f"❌ [{correlation_id}] Response headers: {dict(response.headers)}")
                logger.error(f"❌ [{correlation_id}] Response body (first 500 chars): {response.text[:500]}")
                logger.error(f"❌ [{correlation_id}] Request URL: {url}")
                logger.error(f"❌ [{correlation_id}] Request data: {request_data}")
                logger.error(f"❌ [{correlation_id}] Request method: {http_method}")
                logger.error(f"❌ [{correlation_id}] Headers sent: {dict(headers) if 'headers' in locals() else 'N/A'}")
                
                # For 404, check if it's an HTML page (wrong endpoint) vs JSON error
                if response.status_code == 404:
                    # Check if response is HTML (wrong endpoint) or JSON (no data)
                    response_text = response.text.strip()
                    if "<html" in response_text.lower() or "<!doctype" in response_text.lower():
                        logger.error(f"❌ [{correlation_id}] 404 HTML page received - endpoint '{endpoint_path}' likely doesn't exist!")
                        logger.error(f"❌ [{correlation_id}] Verify endpoint path in config/manufacturer_api.yaml")
                        return {"code": -1, "message": f"Endpoint not found (404): {endpoint_path} - check API configuration"}
                    else:
                        # Try to parse as JSON
                        try:
                            error_json = response.json()
                            if error_json.get("code"):
                                return error_json  # Return vendor's error format
                        except:
                            pass  # Not JSON, continue with standard error
                
                return {"code": -1, "message": f"Request failed with status {response.status_code}"}
            
        except Exception as e:
            correlation_id = str(uuid.uuid4())[:8] if 'correlation_id' not in locals() else correlation_id
            logger.error(f"❌ [{correlation_id}] Error making API request to {endpoint_name}: {str(e)}")
            return {"code": -1, "message": f"Request error: {str(e)}"}
    
    # Auth endpoints
    def logout(self) -> Dict[str, Any]:
        """Logout from manufacturer API"""
        return self._make_request("logout")
    
    # Organization endpoints
    def get_organization_tree(self) -> Dict[str, Any]:
        """Get organization tree"""
        return self._make_request("get_organization_tree")
    
    # Device endpoints
    def get_user_device_list(self, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Get list of devices for the user"""
        return self._make_request("device_list", data)
    
    def get_device_states(self, device_data: Dict) -> Dict[str, Any]:
        """Get device states including ACC status"""
        # Format request as POST with deviceIds array
        if isinstance(device_data.get("deviceId"), str):
            request_data = {"deviceIds": [device_data.get("deviceId")]}
        elif "deviceIds" in device_data:
            request_data = device_data
        else:
            request_data = {"deviceIds": list(device_data.values()) if device_data else []}
        return self._make_request("device_states", request_data)
    
    def get_device_config(self, device_data: Dict) -> Dict[str, Any]:
        """Get device configuration"""
        return self._make_request("device_config_get", device_data)
    
    # GPS endpoints
    def query_track_dates(self, device_data: Dict) -> Dict[str, Any]:
        """Query available track dates for device"""
        return self._make_request("gps_query_track_dates_v1", device_data)
    
    def query_detailed_track(self, track_data: Dict) -> Dict[str, Any]:
        """Query detailed track information"""
        return self._make_request("gps_query_detailed_track_v1", track_data)
    
    def get_latest_gps(self, device_data: Dict) -> Dict[str, Any]:
        """Get latest GPS information using v1 search endpoint"""
        import time
        current_time = int(time.time())
        search_data = {
            "deviceId": device_data.get("deviceId"),
            "startTime": current_time - 86400,  # Last 24 hours
            "endTime": current_time
        }
        return self._make_request("gps_search_v1", search_data)
    
    def get_latest_gps_v2(self, device_data: Dict) -> Dict[str, Any]:
        """Get latest GPS information using v2 endpoint"""
        # Format as array for v2 endpoint
        device_id = device_data.get("deviceId")
        request_data = {"deviceIds": [device_id] if isinstance(device_id, str) else device_id}
        return self._make_request("gps_get_latest_v2", request_data)
    
    # Media endpoints
    def open_preview(self, preview_data: Dict) -> Dict[str, Any]:
        """Open preview and monitor"""
        return self._make_request("media_preview", preview_data)
    
    def close_preview(self, preview_data: Dict) -> Dict[str, Any]:
        """Close preview"""
        return self._make_request("media_close_preview", preview_data)
    
    def start_playback(self, playback_data: Dict) -> Dict[str, Any]:
        """Start video playback"""
        return self._make_request("media_playback", playback_data)
    
    def close_playback(self, playback_data: Dict) -> Dict[str, Any]:
        """Close video playback"""
        return self._make_request("media_close_playback", playback_data)
    
    # Intercom endpoints
    def start_intercom(self, intercom_data: Dict) -> Dict[str, Any]:
        """Start two-way intercom"""
        return self._make_request("media_two_way_intercom", intercom_data)
    
    def end_intercom(self, intercom_data: Dict) -> Dict[str, Any]:
        """End intercom"""
        return self._make_request("media_end_intercom", intercom_data)
    
    # File list endpoint
    def get_file_list(self, file_list_data: Dict) -> Dict[str, Any]:
        """Get list of available video file segments"""
        return self._make_request("media_get_file_list", file_list_data)
    
    # Statistics endpoints
    def get_vehicle_details(self, query_data: Dict) -> Dict[str, Any]:
        """Query vehicle details"""
        return self._make_request("stat_history_get_vehicle_detail", query_data)
    
    def get_vehicle_statistics(self, query_data: Dict) -> Dict[str, Any]:
        """Get vehicle statistics"""
        return self._make_request("stat_history_get_vehicle_statistic", query_data)
    
    # Alarm endpoints
    def get_vehicle_alarms(self, query_data: Dict) -> Dict[str, Any]:
        """Query vehicle alarms (last 3 hours)"""
        return self._make_request("stat_realtime_get_vehicle_alarm", query_data)
    
    def get_attachment(self, attachment_data: Dict) -> Dict[str, Any]:
        """Get attachments"""
        return self._make_request("get_attachments", attachment_data)
    
    # Task endpoints
    def create_text_delivery_task(self, task_data: Dict) -> Dict[str, Any]:
        """Create text delivery task"""
        return self._make_request("task_create", task_data)
    
    def get_task_list(self, query_data: Dict) -> Dict[str, Any]:
        """Get task list"""
        return self._make_request("task_get_list", query_data)
    
    def get_task_details(self, task_data: Dict) -> Dict[str, Any]:
        """Get task details"""
        return self._make_request("task_get_details", task_data)
    
    def update_task_info(self, task_data: Dict) -> Dict[str, Any]:
        """Update task information"""
        return self._make_request("task_update_info", task_data)
    
    def update_task_status(self, task_data: Dict) -> Dict[str, Any]:
        """Update task status"""
        return self._make_request("task_update_status", task_data)
    
    def get_task_results(self, task_data: Dict) -> Dict[str, Any]:
        """Get task execution results"""
        return self._make_request("task_get_results", task_data)
    
    def delete_task(self, task_data: Dict) -> Dict[str, Any]:
        """Delete task"""
        return self._make_request("task_delete", task_data)
    
    # Text delivery endpoint
    def send_text(self, text_data: Dict) -> Dict[str, Any]:
        """Send text delivery"""
        return self._make_request("text_delivery_send", text_data)
    
    # System config endpoints
    def add_system_config(self, config_data: Dict) -> Dict[str, Any]:
        """Add system configuration"""
        return self._make_request("syscfg_add", config_data)
    
    def query_system_config(self, query_data: Dict) -> Dict[str, Any]:
        """Query system configuration"""
        return self._make_request("syscfg_get", query_data)
    
    def modify_system_config(self, config_data: Dict) -> Dict[str, Any]:
        """Modify system configuration"""
        return self._make_request("syscfg_update", config_data)
    
    def delete_system_config(self, config_data: Dict) -> Dict[str, Any]:
        """Delete system configuration"""
        return self._make_request("syscfg_delete", config_data)
    
    def update_config_status(self, config_data: Dict) -> Dict[str, Any]:
        """Enable/disable system configuration"""
        return self._make_request("syscfg_switch_status", config_data)
    
    # Forwarding endpoints
    def create_forwarding_platform(self, platform_data: Dict) -> Dict[str, Any]:
        """Create forwarding platform"""
        return self._make_request("forwarding_platform_create", platform_data)
    
    def create_forwarding_policy(self, policy_data: Dict) -> Dict[str, Any]:
        """Create forwarding policy"""
        return self._make_request("forwarding_policy_create", policy_data)


# Singleton instance
manufacturer_api = ManufacturerAPIService()

