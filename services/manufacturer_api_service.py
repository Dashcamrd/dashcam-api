"""
Manufacturer API Service - Handles all communication with the MDVR platform API
"""
import requests
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ManufacturerAPIService:
    """Service for interacting with the manufacturer's MDVR API"""
    
    def __init__(self):
        self.base_url = os.getenv("MANUFACTURER_API_BASE_URL", "http://180.167.106.70:9337")
        self.username = os.getenv("MANUFACTURER_API_USERNAME")
        self.password = os.getenv("MANUFACTURER_API_PASSWORD")
        self.token = None
        self.token_expires_at = None
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        if not self.token or self._is_token_expired():
            self._refresh_token()
        
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
        """Refresh authentication token"""
        try:
            login_data = {
                "account": self.username,
                "password": self.password
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/user/login",
                json=login_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:  # Success
                    self.token = result.get("data", {}).get("token")
                    # Set token to expire in 23 hours (1 hour before actual expiry)
                    self.token_expires_at = datetime.now() + timedelta(hours=23)
                    logger.info("Successfully refreshed manufacturer API token")
                    return True
                else:
                    logger.error(f"Login failed: {result.get('message')}")
                    return False
            else:
                logger.error(f"Login request failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return False
    
    def _make_request(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to manufacturer API"""
        try:
            headers = self._get_headers()
            url = f"{self.base_url}{endpoint}"
            
            response = requests.post(url, json=data or {}, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return {"code": -1, "message": f"Request failed with status {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error making API request to {endpoint}: {str(e)}")
            return {"code": -1, "message": f"Request error: {str(e)}"}
    
    # Auth endpoints
    def logout(self) -> Dict[str, Any]:
        """Logout from manufacturer API"""
        return self._make_request("/api/v1/user/logout")
    
    # Organization endpoints
    def get_organization_tree(self) -> Dict[str, Any]:
        """Get organization tree"""
        return self._make_request("/api/v1/org/getTree")
    
    # Device endpoints
    def get_user_device_list(self) -> Dict[str, Any]:
        """Get list of devices for the user"""
        return self._make_request("/api/v1/device/getUserDeviceList")
    
    def get_device_status_list(self) -> Dict[str, Any]:
        """Get device status list"""
        return self._make_request("/api/v1/device/getDeviceStatusList")
    
    def get_device_config(self, device_data: Dict) -> Dict[str, Any]:
        """Get device configuration"""
        return self._make_request("/api/v1/device/getConfig", device_data)
    
    # GPS endpoints
    def query_track_dates(self, device_data: Dict) -> Dict[str, Any]:
        """Query available track dates for device"""
        return self._make_request("/api/v1/gps/queryTrackDates", device_data)
    
    def query_detailed_track(self, track_data: Dict) -> Dict[str, Any]:
        """Query detailed track information"""
        return self._make_request("/api/v1/gps/queryDetailedTrack", track_data)
    
    def get_latest_gps(self, device_data: Dict) -> Dict[str, Any]:
        """Get latest GPS information"""
        return self._make_request("/api/v1/gps/getLatestGpsV2", device_data)
    
    # Media endpoints
    def open_preview(self, preview_data: Dict) -> Dict[str, Any]:
        """Open preview and monitor"""
        return self._make_request("/api/v1/media/preview", preview_data)
    
    def close_preview(self, preview_data: Dict) -> Dict[str, Any]:
        """Close preview"""
        return self._make_request("/api/v1/media/closePreview", preview_data)
    
    def start_playback(self, playback_data: Dict) -> Dict[str, Any]:
        """Start video playback"""
        return self._make_request("/api/v1/media/playback", playback_data)
    
    def close_playback(self, playback_data: Dict) -> Dict[str, Any]:
        """Close video playback"""
        return self._make_request("/api/v1/media/closePlayback", playback_data)
    
    # Intercom endpoints
    def start_intercom(self, intercom_data: Dict) -> Dict[str, Any]:
        """Start two-way intercom"""
        return self._make_request("/api/v1/intercom/start", intercom_data)
    
    def end_intercom(self, intercom_data: Dict) -> Dict[str, Any]:
        """End intercom"""
        return self._make_request("/api/v1/intercom/end", intercom_data)
    
    # Statistics endpoints
    def get_vehicle_details(self, query_data: Dict) -> Dict[str, Any]:
        """Query vehicle details"""
        return self._make_request("/api/v1/stat/history/getVehicleDetail", query_data)
    
    def get_vehicle_statistics(self, query_data: Dict) -> Dict[str, Any]:
        """Get vehicle statistics"""
        return self._make_request("/api/v1/stat/history/statByVehicle", query_data)
    
    # Alarm endpoints
    def get_vehicle_alarms(self, query_data: Dict) -> Dict[str, Any]:
        """Query vehicle alarms (last 3 hours)"""
        return self._make_request("/api/v1/stat/realtime/getVehicleAlarm", query_data)
    
    def get_alarm_type_descriptions(self) -> Dict[str, Any]:
        """Get alarm type descriptions"""
        return self._make_request("/api/v1/alarm/getTypeDescription")
    
    def get_attachment(self, attachment_data: Dict) -> Dict[str, Any]:
        """Get attachments"""
        return self._make_request("/api/v1/stat/common/getAttachment", attachment_data)
    
    # Task endpoints
    def create_text_delivery_task(self, task_data: Dict) -> Dict[str, Any]:
        """Create text delivery task"""
        return self._make_request("/api/v1/task/createTextDelivery", task_data)
    
    def get_task_list(self, query_data: Dict) -> Dict[str, Any]:
        """Get task list"""
        return self._make_request("/api/v1/task/getList", query_data)
    
    def get_task_details(self, task_data: Dict) -> Dict[str, Any]:
        """Get task details"""
        return self._make_request("/api/v1/task/getDetail", task_data)
    
    def update_task_info(self, task_data: Dict) -> Dict[str, Any]:
        """Update task information"""
        return self._make_request("/api/v1/task/updateInfo", task_data)
    
    def update_task_status(self, task_data: Dict) -> Dict[str, Any]:
        """Update task status"""
        return self._make_request("/api/v1/task/updateStatus", task_data)
    
    def get_task_results(self, task_data: Dict) -> Dict[str, Any]:
        """Get task execution results"""
        return self._make_request("/api/v1/task/getResult", task_data)
    
    def delete_task(self, task_data: Dict) -> Dict[str, Any]:
        """Delete task"""
        return self._make_request("/api/v1/task/delete", task_data)
    
    # Text delivery endpoint
    def send_text(self, text_data: Dict) -> Dict[str, Any]:
        """Send text delivery"""
        return self._make_request("/api/v1/text/send", text_data)
    
    # System config endpoints
    def add_system_config(self, config_data: Dict) -> Dict[str, Any]:
        """Add system configuration"""
        return self._make_request("/api/v1/config/add", config_data)
    
    def query_system_config(self, query_data: Dict) -> Dict[str, Any]:
        """Query system configuration"""
        return self._make_request("/api/v1/config/query", query_data)
    
    def modify_system_config(self, config_data: Dict) -> Dict[str, Any]:
        """Modify system configuration"""
        return self._make_request("/api/v1/config/modify", config_data)
    
    def delete_system_config(self, config_data: Dict) -> Dict[str, Any]:
        """Delete system configuration"""
        return self._make_request("/api/v1/config/delete", config_data)
    
    def update_config_status(self, config_data: Dict) -> Dict[str, Any]:
        """Enable/disable system configuration"""
        return self._make_request("/api/v1/config/updateStatus", config_data)
    
    # Forwarding endpoints
    def create_forwarding_platform(self, platform_data: Dict) -> Dict[str, Any]:
        """Create forwarding platform"""
        return self._make_request("/api/v1/forwarding/platform/create", platform_data)
    
    def create_forwarding_policy(self, policy_data: Dict) -> Dict[str, Any]:
        """Create forwarding policy"""
        return self._make_request("/api/v1/forwarding/policy/create", policy_data)
    
    def set_device_forwarding_config(self, config_data: Dict) -> Dict[str, Any]:
        """Set device forwarding configuration"""
        return self._make_request("/api/v1/forwarding/device/set", config_data)
    
    def get_device_forwarding_config(self, config_data: Dict) -> Dict[str, Any]:
        """Get device forwarding configuration"""
        return self._make_request("/api/v1/forwarding/device/get", config_data)
    
    def delete_device_forwarding_config(self, config_data: Dict) -> Dict[str, Any]:
        """Delete device forwarding configuration"""
        return self._make_request("/api/v1/forwarding/device/delete", config_data)
    
    def batch_set_device_forwarding_config(self, config_data: Dict) -> Dict[str, Any]:
        """Batch set device forwarding configuration"""
        return self._make_request("/api/v1/forwarding/device/batchSet", config_data)


# Singleton instance
manufacturer_api = ManufacturerAPIService()

