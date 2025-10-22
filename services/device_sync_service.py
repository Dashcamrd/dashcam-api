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
        
        # Get all devices from manufacturer API
        result = manufacturer_api.get_user_device_list()
        
        if result.get("code") != 0:
            logger.error(f"❌ Failed to get device list: {result.get('message', 'Unknown error')}")
            return {
                "success": False,
                "error": f"Manufacturer API error: {result.get('message', 'Unknown error')}"
            }
        
        manufacturer_devices = result.get("data", {}).get("devices", [])
        logger.info(f"📱 Found {len(manufacturer_devices)} devices from manufacturer")
        
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
