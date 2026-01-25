"""
ChinaMDVR Service - Handles device activation by sending commands to chinamdvr.com
Used to redirect devices from manufacturer server to our own VMS server
"""
import requests
import hashlib
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ChinaMDVRService:
    """Service for interacting with the ChinaMDVR manufacturer server"""
    
    # ChinaMDVR API configuration (manufacturer's default server)
    BASE_URL = "http://chinamdvr.com:8337"
    USERNAME = "DRD"
    PASSWORD = "DRD000"
    
    # Our VMS server configuration
    OUR_SERVER = "vms.dashcamrd.com"
    OUR_PORT = 9339
    
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        logger.info(f"🔧 ChinaMDVR Service initialized")
        logger.info(f"   Target server: {self.BASE_URL}")
        logger.info(f"   Our server: {self.OUR_SERVER}:{self.OUR_PORT}")
    
    def _md5_hash(self, text: str) -> str:
        """Generate MD5 hash of password (common in Chinese MDVR APIs)"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _login(self) -> bool:
        """Login to ChinaMDVR server and get token"""
        try:
            logger.info(f"🔐 Logging into ChinaMDVR: {self.BASE_URL}")
            
            login_data = {
                "username": self.USERNAME,
                "password": self._md5_hash(self.PASSWORD),
                "progVersion": "0.0.1",
                "platform": 3
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/api/v1/user/login",
                json=login_data,
                timeout=30
            )
            
            result = response.json()
            
            if result.get("code") == 200 or result.get("code") == 0:
                # Try different token paths
                self.token = (
                    result.get("data", {}).get("token") or
                    result.get("token") or
                    result.get("data", {}).get("accessToken")
                )
                
                if self.token:
                    logger.info(f"✅ ChinaMDVR login successful")
                    return True
                else:
                    logger.error(f"❌ No token in response: {result}")
                    return False
            else:
                logger.error(f"❌ ChinaMDVR login failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ ChinaMDVR login error: {e}")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid token"""
        if not self.token:
            return self._login()
        return True
    
    def activate_device(self, device_id: str) -> Dict[str, Any]:
        """
        Activate a device by sending server redirect command
        
        This sends the $JTSVR1 command to change the device's server
        from chinamdvr.com to our VMS server (vms.dashcamrd.com)
        
        Args:
            device_id: The device ID to activate
            
        Returns:
            Dict with success status and message
        """
        try:
            logger.info(f"🚀 Activating device {device_id}")
            
            # Ensure we're logged in
            if not self._ensure_authenticated():
                return {
                    "success": False,
                    "message": "Failed to authenticate with manufacturer server"
                }
            
            # Build the server redirect command
            # Format: $JTSVR1,server_address,port,enable,enable
            command = f"$JTSVR1,{self.OUR_SERVER},{self.OUR_PORT},1,1"
            
            logger.info(f"📤 Sending command to device {device_id}: {command}")
            
            # Send command via text delivery API
            send_data = {
                "name": f"Activate_{device_id}",
                "content": command,
                "contentTypes": ["1", "2"],
                "deviceId": device_id,
                "operator": "admin"
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/api/v1/textDelivery/send",
                json=send_data,
                headers={"X-Token": self.token},
                timeout=30
            )
            
            result = response.json()
            
            if result.get("code") == 200 or result.get("code") == 0:
                logger.info(f"✅ Activation command sent to device {device_id}")
                return {
                    "success": True,
                    "message": f"Activation command sent to device {device_id}. Device will reconnect to {self.OUR_SERVER} shortly.",
                    "command": command,
                    "device_id": device_id
                }
            else:
                error_msg = result.get("msg") or result.get("message") or "Unknown error"
                logger.error(f"❌ Failed to send command: {error_msg}")
                return {
                    "success": False,
                    "message": f"Failed to send command: {error_msg}",
                    "device_id": device_id
                }
                
        except Exception as e:
            logger.error(f"❌ Activation error for {device_id}: {e}")
            return {
                "success": False,
                "message": f"Activation error: {str(e)}",
                "device_id": device_id
            }
    
    def check_device_exists(self, device_id: str) -> bool:
        """Check if device exists on ChinaMDVR server"""
        try:
            if not self._ensure_authenticated():
                return False
            
            # Query device list to check if device exists
            query_data = {
                "page": 1,
                "pageSize": 1,
                "deviceIds": [device_id]
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/api/v1/device/getList",
                json=query_data,
                headers={"X-Token": self.token},
                timeout=30
            )
            
            result = response.json()
            
            if result.get("code") == 200 or result.get("code") == 0:
                devices = result.get("data", {}).get("list", [])
                return len(devices) > 0
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking device {device_id}: {e}")
            return False


# Singleton instance
chinamdvr_service = ChinaMDVRService()

