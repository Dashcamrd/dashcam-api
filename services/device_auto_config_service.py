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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from database import SessionLocal
from models.device_db import DeviceDB
from services.manufacturer_api_service import manufacturer_api

logger = logging.getLogger(__name__)

_autoconfig_thread_pool = ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="autoconfig"
)


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
    
    CYCLE_TIMEOUT = 45

    async def _run_worker(self):
        """Main worker loop - syncs device statuses and configures unconfigured devices"""
        logger.info(f"🔄 Auto-config worker started, checking every {self.CHECK_INTERVAL_SECONDS}s")
        
        while self.running:
            try:
                await asyncio.wait_for(
                    self._run_cycle(), timeout=self.CYCLE_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"❌ Auto-config cycle exceeded {self.CYCLE_TIMEOUT}s timeout, skipping"
                )
            except Exception as e:
                logger.error(f"❌ Error in auto-config worker: {e}", exc_info=True)
            
            await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)

    async def _run_cycle(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_autoconfig_thread_pool, self._sync_device_statuses_blocking)
        await loop.run_in_executor(_autoconfig_thread_pool, self._process_unconfigured_devices_blocking)

    def _sync_device_statuses_blocking(self):
        """
        Runs in a dedicated thread pool. Syncs device statuses from device_cache.
        """
        db: Session = SessionLocal()
        try:
            from models.device_cache_db import DeviceCacheDB
            
            devices = db.query(DeviceDB).all()
            
            if not devices:
                return
            
            now = datetime.utcnow()
            STALE_THRESHOLD_MINUTES = 10
            updated_count = 0
            
            for device in devices:
                cache = db.query(DeviceCacheDB).filter(
                    DeviceCacheDB.device_id == device.device_id
                ).first()
                
                if not cache:
                    continue
                
                old_status = device.status
                
                cache_is_fresh = False
                if cache.updated_at:
                    age_minutes = (now - cache.updated_at).total_seconds() / 60
                    cache_is_fresh = age_minutes <= STALE_THRESHOLD_MINUTES
                
                if cache.acc_status and cache_is_fresh:
                    new_status = "online"
                elif device.parking_mode and cache_is_fresh:
                    new_status = "online"
                else:
                    new_status = "offline"
                device.status = new_status
                
                if old_status == "offline" and new_status == "online":
                    device.last_online_at = now
                    logger.info(f"📡 Device {device.device_id} ACC turned ON at {now}")
                    updated_count += 1
                elif new_status == "online" and device.last_online_at is None:
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
    
    def _process_unconfigured_devices_blocking(self):
        """Runs in a dedicated thread pool. Finds and configures unconfigured online devices."""
        db: Session = SessionLocal()
        try:
            devices = self._get_unconfigured_online_devices(db)
            
            if not devices:
                return
            
            logger.info(f"📋 Found {len(devices)} unconfigured online devices to process")
            
            for device in devices:
                self._process_device_blocking(db, device)
                
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
    
    def _process_device_blocking(self, db: Session, device: DeviceDB):
        """Process a single device for configuration (runs in thread pool)"""
        device_id = device.device_id
        attempts = device.config_attempts or 0
        last_attempt = device.config_last_attempt
        last_online = device.last_online_at
        
        now = datetime.utcnow()
        
        if attempts == 0:
            if last_online is None:
                logger.debug(f"⏳ Device {device_id}: waiting for online timestamp (status sync)")
                return
            
            required_wait = last_online + timedelta(minutes=self.INITIAL_DELAY_MINUTES)
            if now < required_wait:
                remaining = int((required_wait - now).total_seconds() // 60)
                logger.debug(f"⏳ Device {device_id}: waiting {remaining}m before first config attempt")
                return
        else:
            if last_attempt is None:
                last_attempt = now - timedelta(minutes=self.RETRY_DELAY_MINUTES + 1)
            
            required_wait = last_attempt + timedelta(minutes=self.RETRY_DELAY_MINUTES)
            if now < required_wait:
                remaining = int((required_wait - now).total_seconds() // 60)
                logger.debug(f"⏳ Device {device_id}: waiting {remaining}m before retry attempt #{attempts + 1}")
                return
        
        logger.info(f"🔧 Attempting to configure device {device_id} (attempt #{attempts + 1})")
        
        success = self._send_configuration_blocking(device_id)
        
        if success:
            device.configured = "yes"
            device.config_last_attempt = now
            device.config_attempts = attempts + 1
            db.commit()
            logger.info(f"✅ Device {device_id} configured successfully!")
        else:
            device.config_last_attempt = now
            device.config_attempts = attempts + 1
            db.commit()
            logger.warning(f"❌ Device {device_id} configuration failed (attempt #{attempts + 1}), will retry in {self.RETRY_DELAY_MINUTES}m")
    
    def _send_configuration_blocking(self, device_id: str) -> bool:
        """Send config command to device (runs in thread pool)"""
        try:
            result = manufacturer_api.send_text({
                "name": f"AutoConfig-{device_id}",
                "content": self.CONFIG_COMMAND,
                "contentTypes": ["1"],
                "deviceId": device_id,
                "operator": "system"
            })
            
            logger.info(f"📡 Config command sent to {device_id}, response: {result}")
            
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
        """Manually trigger configuration for a specific device."""
        logger.info(f"🔧 Manual configuration triggered for device {device_id}")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _autoconfig_thread_pool,
            self._configure_device_manually_blocking, device_id
        )

    def _configure_device_manually_blocking(self, device_id: str) -> Dict:
        success = self._send_configuration_blocking(device_id)
        if success:
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
        """Reset configuration status for a device to trigger reconfiguration."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _autoconfig_thread_pool,
            self._reset_device_config_blocking, device_id
        )

    def _reset_device_config_blocking(self, device_id: str) -> Dict:
        db: Session = SessionLocal()
        try:
            device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
            if device:
                device.configured = "no"
                device.config_attempts = 0
                device.config_last_attempt = None
                device.last_online_at = datetime.utcnow()
                db.commit()
                logger.info(f"🔄 Configuration reset for device {device_id}")
                return {"success": True, "message": f"Device {device_id} configuration reset"}
            else:
                return {"success": False, "message": f"Device {device_id} not found"}
        finally:
            db.close()


# Singleton instance
device_auto_config = DeviceAutoConfigService()

