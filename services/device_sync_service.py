"""
Device synchronization service
Automatically syncs devices from manufacturer API to local database
"""
from sqlalchemy.orm import Session
from database import SessionLocal
from models.device_db import DeviceDB
from services.manufacturer_api_service import ManufacturerAPIService
import logging

logger = logging.getLogger(__name__)

def sync_devices_from_manufacturer():
    """
    Sync all devices from manufacturer API to local database.
    This should be called when admin logs in or periodically.
    """
    db = SessionLocal()
    manufacturer_api = ManufacturerAPIService()
    
    try:
        logger.info("🔄 Starting device sync from manufacturer API...")
        
        # Call manufacturer API directly (bypassing our service)
        import requests
        
        # Use fresh token from direct curl test
        fresh_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJCYXNlQ2xhaW1zIjp7IklkIjoyODQsIlV1aWQiOiIxM2QzMTAzMC1mMGM1LTQ2OTUtYTllZC0yN2ZlZmIyNTkxNWEiLCJVc2VybmFtZSI6Im1vbm8xIiwiQ29tcGFueUlkIjo0MzcsIkNvbXBhbnkiOiLmspnnibnpmL_mi4nkvK9EQVMiLCJSb2xlSWQiOjI1LCJFeHBpcmF0aW9uIjowfSwiQnVmZmVyVGltZSI6MCwiaXNzIjoidGwiLCJhdWQiOlsidGwiXSwibmJmIjoxNzYxMjMzMzc5fQ.WrKJBJKQweA5dFk4jr4xbGtQQyVXFzlj5-FtcWCOUls"
        
        logger.info("🔄 Calling manufacturer API directly...")
        
        # Make direct request to manufacturer API
        response = requests.post(
            "http://180.167.106.70:9337/api/v1/device/getList",
            headers={
                "Content-Type": "application/json",
                "X-Token": fresh_token
            },
            json={"page": 1, "pageSize": 10},
            timeout=30
        )
        
        logger.info(f"📡 Manufacturer API response status: {response.status_code}")
        logger.info(f"📡 Manufacturer API response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Got device data: {result}")
            
            if result.get("code") == 200:
                manufacturer_devices = result.get("data", {}).get("list", [])
                logger.info(f"📱 Found {len(manufacturer_devices)} devices from manufacturer")
            else:
                logger.error(f"❌ Manufacturer API error: {result.get('message')}")
                return {
                    "success": False,
                    "error": f"Manufacturer API error: {result.get('message')}"
                }
        else:
            logger.error(f"❌ Manufacturer API request failed: {response.status_code}")
            return {
                "success": False,
                "error": f"Manufacturer API request failed: {response.status_code}"
            }
        
        # Get existing devices from local database
        existing_devices = db.query(DeviceDB).all()
        existing_device_ids = {device.device_id for device in existing_devices}
        
        # Track sync results
        new_devices = []
        updated_devices = []
        skipped_devices = []
        
        for device_data in manufacturer_devices:
            device_id = device_data.get("deviceId")
            device_name = device_data.get("deviceName", device_id)
            org_id = device_data.get("orgId", "default")
            status = device_data.get("status", "offline")
            
            if device_id in existing_device_ids:
                # Update existing device
                existing_device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
                if existing_device:
                    existing_device.name = device_name
                    existing_device.org_id = org_id
                    existing_device.status = status
                    updated_devices.append(device_id)
            else:
                # Create new device (unassigned)
                new_device = DeviceDB(
                    device_id=device_id,
                    name=device_name,
                    assigned_user_id=None,  # Unassigned initially
                    org_id=org_id,
                    status=status
                )
                db.add(new_device)
                new_devices.append(device_id)
        
        # Commit all changes
        db.commit()
        
        logger.info(f"✅ Device sync completed:")
        logger.info(f"   📱 New devices: {len(new_devices)}")
        logger.info(f"   🔄 Updated devices: {len(updated_devices)}")
        logger.info(f"   📊 Total manufacturer devices: {len(manufacturer_devices)}")
        
        return {
            "success": True,
            "new_devices": len(new_devices),
            "updated_devices": len(updated_devices),
            "total_manufacturer_devices": len(manufacturer_devices),
            "new_device_ids": new_devices,
            "updated_device_ids": updated_devices
        }
        
    except Exception as e:
        logger.error(f"❌ Error syncing devices: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()

def get_sync_status():
    """Get current sync status and device counts"""
    db = SessionLocal()
    try:
        # Count local devices
        total_local_devices = db.query(DeviceDB).count()
        assigned_devices = db.query(DeviceDB).filter(DeviceDB.assigned_user_id.isnot(None)).count()
        unassigned_devices = db.query(DeviceDB).filter(DeviceDB.assigned_user_id.is_(None)).count()
        
        return {
            "total_local_devices": total_local_devices,
            "assigned_devices": assigned_devices,
            "unassigned_devices": unassigned_devices,
            "last_sync": "Manual sync required"  # Could be enhanced with timestamps
        }
    finally:
        db.close()
