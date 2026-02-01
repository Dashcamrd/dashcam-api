"""
Device Auto-Configuration Service

Automatically configures devices when they come online (ACC ON).
Uses device_cache table (populated by data forwarding webhooks) for
efficient status checking without API calls.

Flow:
1. ACC turns ON (detected via device_cache.acc_status from data forwarding)
2. Wait 3 minutes (to ensure stable connection)
3. Send configuration command via text_delivery API
4. If success: mark configured = 'yes'
5. If fail: retry every 5 minutes until success

Key: Uses acc_status (ACC ON) as the reliable indicator that device
is truly online and ready to receive commands, rather than is_online
which can be stale/unreliable.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from database import SessionLocal
from models.device_db import DeviceDB
from services.manufacturer_api_service import manufacturer_api

logger = logging.getLogger(__name__)


class DeviceAutoConfigService:
    """
    Background service to automatically configure devices when they come online.
    Runs as an async task, checking for unconfigured online devices periodically.
    """
    
    # Configuration constants
    INITIAL_DELAY_MINUTES = 3      # Wait 3 minutes after device comes online
    RETRY_DELAY_MINUTES = 5        # Retry every 5 minutes on failure
    CHECK_INTERVAL_SECONDS = 60    # Check for unconfigured devices every 60 seconds
    
    # The configuration command to send to devices
    CONFIG_COMMAND = """#!/bin/sh
update INI ftp://zxy:zxy1@chinamdvr.com:21/LST/DRD.config.ini
#end"""
    
    def __init__(self):
        self.running = False
        self._task: Optional[asyncio.Task] = None
        logger.info("🔧 Device Auto-Configuration Service initialized")
    
    def start(self):
        """Start the auto-configuration background worker"""
        if self._task is not None and not self._task.done():
            logger.warning("⚠️ Auto-config service is already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._run_worker())
        logger.info("✅ Device Auto-Configuration Service started")
    
    def stop(self):
        """Stop the auto-configuration background worker"""
        self.running = False
        if self._task is not None:
            self._task.cancel()
            logger.info("🛑 Device Auto-Configuration Service stopped")
    
    async def _run_worker(self):
        """Main worker loop - syncs device statuses and configures unconfigured devices"""
        logger.info(f"🔄 Auto-config worker started, checking every {self.CHECK_INTERVAL_SECONDS}s")
        
        while self.running:
            try:
                # First, sync device statuses from manufacturer API
                await self._sync_device_statuses()
                
                # Then process unconfigured devices
                await self._process_unconfigured_devices()
            except Exception as e:
                logger.error(f"❌ Error in auto-config worker: {e}", exc_info=True)
            
            # Wait before next check
            await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)
    
    async def _sync_device_statuses(self):
        """
        Sync device statuses from device_cache table (populated by data forwarding).
        Uses acc_status as the most reliable indicator that a device is truly online
        and ready to receive commands (ACC ON = car running, device powered).
        
        IMPORTANT: Also checks if data is fresh (updated recently).
        If cache is stale (>10 min old), consider device offline even if acc_status=True.
        This prevents trying to configure devices that went offline but have stale cache data.
        """
        db: Session = SessionLocal()
        try:
            from models.device_cache_db import DeviceCacheDB
            
            # Get all devices from database
            devices = db.query(DeviceDB).all()
            
            if not devices:
                return
            
            now = datetime.utcnow()
            STALE_THRESHOLD_MINUTES = 10  # Consider data stale if older than 10 min
            updated_count = 0
            
            for device in devices:
                # Get cached status from device_cache (populated by data forwarding)
                cache = db.query(DeviceCacheDB).filter(
                    DeviceCacheDB.device_id == device.device_id
                ).first()
                
                if not cache:
                    continue  # No cached data yet for this device
                
                old_status = device.status
                
                # Check if cache is fresh (updated within threshold)
                cache_is_fresh = False
                if cache.updated_at:
                    age_minutes = (now - cache.updated_at).total_seconds() / 60
                    cache_is_fresh = age_minutes <= STALE_THRESHOLD_MINUTES
                
                # Device is online ONLY if:
                # 1. acc_status = True (ACC is ON)
                # 2. Cache is fresh (data received recently, not stale)
                new_status = "online" if (cache.acc_status and cache_is_fresh) else "offline"
                
                # Update device status from cache
                device.status = new_status
                
                # If device ACC just turned ON (with fresh data), update last_online_at
                if old_status == "offline" and new_status == "online":
                    device.last_online_at = now
                    logger.info(f"📡 Device {device.device_id} ACC turned ON at {now}")
                    updated_count += 1
                elif new_status == "online" and device.last_online_at is None:
                    # Device ACC was already ON but we don't have last_online_at
                    device.last_online_at = cache.last_online_time or now
                    updated_count += 1
            
            db.commit()
            if updated_count > 0:
                logger.info(f"✅ Updated ACC status for {updated_count} devices from cache")
            
        except Exception as e:
            logger.error(f"❌ Error syncing device statuses from cache: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    async def _process_unconfigured_devices(self):
        """Find and configure unconfigured online devices"""
        db: Session = SessionLocal()
        try:
            # Get all online devices that are not configured
            devices = self._get_unconfigured_online_devices(db)
            
            if not devices:
                return
            
            logger.info(f"📋 Found {len(devices)} unconfigured online devices to process")
            
            for device in devices:
                await self._process_device(db, device)
                
        finally:
            db.close()
    
    def _get_unconfigured_online_devices(self, db: Session) -> List[DeviceDB]:
        """
        Get list of devices that need configuration and have ACC ON.
        
        Conditions:
        - status = "online" (meaning ACC is ON, based on device_cache.acc_status)
        - configured = "no" or NULL (not yet configured)
        
        Returns devices ready to receive configuration commands.
        """
        return db.query(DeviceDB).filter(
            DeviceDB.status == "online",  # ACC is ON
            (DeviceDB.configured == None) | (DeviceDB.configured == "no")
        ).all()
    
    async def _process_device(self, db: Session, device: DeviceDB):
        """Process a single device for configuration"""
        device_id = device.device_id
        attempts = device.config_attempts or 0
        last_attempt = device.config_last_attempt
        last_online = device.last_online_at
        
        now = datetime.utcnow()
        
        # Calculate required delay
        if attempts == 0:
            # First attempt: wait 3 minutes after coming online
            if last_online is None:
                # Device is online but we don't have last_online_at yet
                # This shouldn't happen if status sync is working, but handle gracefully
                logger.debug(f"⏳ Device {device_id}: waiting for online timestamp (status sync)")
                return  # Will check again next cycle
            
            required_wait = last_online + timedelta(minutes=self.INITIAL_DELAY_MINUTES)
            if now < required_wait:
                remaining = int((required_wait - now).total_seconds() // 60)
                logger.debug(f"⏳ Device {device_id}: waiting {remaining}m before first config attempt")
                return
        else:
            # Retry: wait 5 minutes after last attempt
            if last_attempt is None:
                last_attempt = now - timedelta(minutes=self.RETRY_DELAY_MINUTES + 1)  # Force retry
            
            required_wait = last_attempt + timedelta(minutes=self.RETRY_DELAY_MINUTES)
            if now < required_wait:
                remaining = int((required_wait - now).total_seconds() // 60)
                logger.debug(f"⏳ Device {device_id}: waiting {remaining}m before retry attempt #{attempts + 1}")
                return
        
        # Time to attempt configuration
        logger.info(f"🔧 Attempting to configure device {device_id} (attempt #{attempts + 1})")
        
        success = await self._send_configuration(device_id)
        
        if success:
            # Mark as configured
            device.configured = "yes"
            device.config_last_attempt = now
            device.config_attempts = attempts + 1
            db.commit()
            logger.info(f"✅ Device {device_id} configured successfully!")
        else:
            # Record failed attempt
            device.config_last_attempt = now
            device.config_attempts = attempts + 1
            db.commit()
            logger.warning(f"❌ Device {device_id} configuration failed (attempt #{attempts + 1}), will retry in {self.RETRY_DELAY_MINUTES}m")
    
    async def _send_configuration(self, device_id: str) -> bool:
        """
        Send the configuration command to the device via text delivery.
        
        The command updates the device's INI configuration from an FTP server.
        
        API requires:
        - name: Task name (required)
        - content: Delivery content (required)
        - contentTypes: ["1"]=Screen display, ["2"]=Voice broadcast (required)
        - deviceId: Single device ID string (required)
        - operator: Who triggered this (optional)
        """
        try:
            # Use manufacturer API to send text delivery
            result = manufacturer_api.send_text({
                "name": f"AutoConfig-{device_id}",  # Required task name
                "content": self.CONFIG_COMMAND,
                "contentTypes": ["1"],  # 1 = Screen display (execute command)
                "deviceId": device_id,  # Single device ID (not array)
                "operator": "system"  # Who triggered this
            })
            
            logger.info(f"📡 Config command sent to {device_id}, response: {result}")
            
            # Check for success
            if result.get("code") in [0, 200] or result.get("message") == "success":
                return True
            else:
                logger.error(f"❌ Config command failed for {device_id}: {result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send config to {device_id}: {e}", exc_info=True)
            return False
    
    def get_status(self) -> Dict:
        """Get current service status"""
        return {
            "running": self.running,
            "initial_delay_minutes": self.INITIAL_DELAY_MINUTES,
            "retry_delay_minutes": self.RETRY_DELAY_MINUTES,
            "check_interval_seconds": self.CHECK_INTERVAL_SECONDS
        }
    
    async def configure_device_manually(self, device_id: str) -> Dict:
        """
        Manually trigger configuration for a specific device.
        Useful for testing or forcing reconfiguration.
        """
        logger.info(f"🔧 Manual configuration triggered for device {device_id}")
        
        success = await self._send_configuration(device_id)
        
        if success:
            # Update database
            db: Session = SessionLocal()
            try:
                device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
                if device:
                    device.configured = "yes"
                    device.config_last_attempt = datetime.utcnow()
                    device.config_attempts = (device.config_attempts or 0) + 1
                    db.commit()
            finally:
                db.close()
            
            return {"success": True, "message": f"Device {device_id} configured successfully"}
        else:
            return {"success": False, "message": f"Failed to configure device {device_id}"}
    
    async def reset_device_config(self, device_id: str) -> Dict:
        """
        Reset configuration status for a device to trigger reconfiguration.
        """
        db: Session = SessionLocal()
        try:
            device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
            if device:
                device.configured = "no"
                device.config_attempts = 0
                device.config_last_attempt = None
                device.last_online_at = datetime.utcnow()  # Set to now to trigger 3-min wait
                db.commit()
                logger.info(f"🔄 Configuration reset for device {device_id}")
                return {"success": True, "message": f"Device {device_id} configuration reset"}
            else:
                return {"success": False, "message": f"Device {device_id} not found"}
        finally:
            db.close()


# Singleton instance
device_auto_config = DeviceAutoConfigService()

