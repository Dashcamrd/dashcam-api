"""
Devices Router - Handles device management and configuration
"""
from fastapi import APIRouter, Depends, HTTPException
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from services.chinamdvr_service import chinamdvr_service
from typing import Optional, List
from pydantic import BaseModel
from database import SessionLocal
from models.device_db import DeviceDB
from models.device_cache_db import DeviceCacheDB, AlarmDB
from models.fcm_token_db import UserNotificationSettingsDB
from adapters import GPSAdapter
from datetime import datetime, timezone
from fastapi import Query
from utils.acc_mode import acc_mode_response
import logging

logger = logging.getLogger(__name__)


def _create_default_notification_settings(user_id: int, device_id: str, db_session, language: str = "en"):
    """
    Create default notification settings for a user-device pair.
    Default: ACC notifications OFF (user must explicitly enable).
    """
    try:
        # Check if settings already exist
        existing = db_session.query(UserNotificationSettingsDB).filter(
            UserNotificationSettingsDB.user_id == user_id,
            UserNotificationSettingsDB.device_id == device_id
        ).first()
        
        if not existing:
            new_setting = UserNotificationSettingsDB(
                user_id=user_id,
                device_id=device_id,
                acc_notification="none",  # OFF by default
                language=language
            )
            db_session.add(new_setting)
            db_session.commit()
            logger.info(f"✅ Created default notification settings for user {user_id}, device {device_id}")
            return True
        else:
            logger.debug(f"📝 Notification settings already exist for user {user_id}, device {device_id}")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Failed to create notification settings: {e}")
        return False

router = APIRouter(prefix="/devices", tags=["Devices"])


def _populate_device_cache(device_id: str, db_session=None):
    """
    Fetch device data from VMS and populate the device_cache table.
    This is called after adding a device to ensure immediate data availability.
    """
    close_db = False
    if db_session is None:
        db_session = SessionLocal()
        close_db = True
    
    try:
        logger.info(f"📡 Fetching initial data for device {device_id} from VMS...")
        
        # Fetch GPS data from VMS
        gps_result = manufacturer_api.get_device_gps([device_id])
        
        if gps_result.get("code") == 0:
            gps_data_list = gps_result.get("data", [])
            
            if gps_data_list:
                # Parse GPS data using adapter
                parsed_data = GPSAdapter.parse_gps_response(gps_data_list, device_id)
                
                if parsed_data and parsed_data.get("latitude") and parsed_data.get("longitude"):
                    # Check if cache entry exists
                    cache = db_session.query(DeviceCacheDB).filter(
                        DeviceCacheDB.device_id == device_id
                    ).first()
                    
                    if cache:
                        # Update existing cache
                        cache.latitude = parsed_data.get("latitude")
                        cache.longitude = parsed_data.get("longitude")
                        cache.speed = parsed_data.get("speed", 0)
                        cache.direction = parsed_data.get("direction", 0)
                        cache.address = parsed_data.get("address")
                        cache.acc_state = parsed_data.get("acc_state")
                        cache.updated_at = datetime.utcnow()
                        logger.info(f"✅ Updated cache for device {device_id}")
                    else:
                        # Create new cache entry
                        new_cache = DeviceCacheDB(
                            device_id=device_id,
                            latitude=parsed_data.get("latitude"),
                            longitude=parsed_data.get("longitude"),
                            speed=parsed_data.get("speed", 0),
                            direction=parsed_data.get("direction", 0),
                            address=parsed_data.get("address"),
                            acc_state=parsed_data.get("acc_state"),
                            updated_at=datetime.utcnow()
                        )
                        db_session.add(new_cache)
                        logger.info(f"✅ Created cache for device {device_id}")
                    
                    db_session.commit()
                    return True
                else:
                    logger.info(f"ℹ️ No GPS data available for device {device_id} (device may be offline)")
            else:
                logger.info(f"ℹ️ No data returned for device {device_id} from VMS")
        else:
            logger.warning(f"⚠️ VMS API returned error for device {device_id}: {gps_result.get('message')}")
        
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ Could not fetch initial data for device {device_id}: {e}")
        return False
    finally:
        if close_db:
            db_session.close()

class DeviceResponse(BaseModel):
    id: int
    device_id: str
    name: str
    status: str
    org_id: str
    brand: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None

class DeviceConfigRequest(BaseModel):
    device_id: str
    config_type: Optional[str] = "general"

class DeviceRenameRequest(BaseModel):
    device_id: str
    new_name: str

@router.get("/")
def list_user_devices(current_user: dict = Depends(get_current_user)):
    """
    Get all devices assigned to the current user.
    Returns device information from local database plus status from manufacturer API.
    """
    user_devices = get_user_devices(current_user["user_id"], is_admin=current_user.get("is_admin", False))
    
    if not user_devices:
        return {
            "success": True,
            "devices": [],
            "message": "No devices assigned to this user"
        }
    
    # Enhance device info with manufacturer API data
    enhanced_devices = []
    for device in user_devices:
        p_mode = device.parking_mode if hasattr(device, 'parking_mode') else False
        device_info = {
            "id": device.id,
            "device_id": device.device_id,
            "name": device.name,
            "status": device.status,
            "org_id": device.org_id,
            "brand": device.brand,
            "model": device.model,
            "firmware_version": device.firmware_version,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "parking_mode": p_mode or False,
            "online_status": "unknown",
            "last_seen": None
        }
        
        # Try to get real-time status from manufacturer API
        try:
            # This would typically come from device status list
            status_result = manufacturer_api.get_device_status_list()
            if status_result.get("code") == 0:
                device_statuses = status_result.get("data", {}).get("devices", [])
                for status_info in device_statuses:
                    if status_info.get("deviceId") == device.device_id:
                        device_info["online_status"] = status_info.get("status", "offline")
                        device_info["last_seen"] = status_info.get("lastSeen")
                        break
        except Exception as e:
            # If status check fails, keep default values
            pass
        
        enhanced_devices.append(device_info)
    
    return {
        "success": True,
        "devices": enhanced_devices,
        "total_devices": len(enhanced_devices)
    }

@router.get("/{device_id}")
def get_device_details(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific device.
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    user_devices = get_user_devices(current_user["user_id"], is_admin=current_user.get("is_admin", False))
    user_device_ids = [device.device_id for device in user_devices]
    
    if device_id not in user_device_ids:
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Find the device in user's devices
    device = next((d for d in user_devices if d.device_id == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get additional info from manufacturer API
    p_mode = device.parking_mode if hasattr(device, 'parking_mode') else False
    device_info = {
        "id": device.id,
        "device_id": device.device_id,
        "name": device.name,
        "status": device.status,
        "org_id": device.org_id,
        "brand": device.brand,
        "model": device.model,
        "firmware_version": device.firmware_version,
        "created_at": device.created_at.isoformat() if device.created_at else None,
        "parking_mode": p_mode or False,
    }
    
    # Try to get real-time status and config
    try:
        status_result = manufacturer_api.get_device_status_list()
        if status_result.get("code") == 0:
            device_statuses = status_result.get("data", {}).get("devices", [])
            for status_info in device_statuses:
                if status_info.get("deviceId") == device_id:
                    device_info.update({
                        "online_status": status_info.get("status", "offline"),
                        "last_seen": status_info.get("lastSeen"),
                        "ip_address": status_info.get("ipAddress"),
                        "signal_strength": status_info.get("signalStrength")
                    })
                    break
    except Exception as e:
        device_info["api_error"] = str(e)
    
    return {
        "success": True,
        "device": device_info
    }

@router.post("/{device_id}/config")
def get_device_config(
    device_id: str,
    request: DeviceConfigRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get device configuration from manufacturer API.
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    user_devices = get_user_devices(current_user["user_id"], is_admin=current_user.get("is_admin", False))
    user_device_ids = [device.device_id for device in user_devices]
    
    if device_id not in user_device_ids:
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    config_data = {
        "deviceId": device_id,
        "configType": request.config_type
    }
    result = manufacturer_api.get_device_config(config_data)
    
    if result.get("code") == 0:
        config_info = result.get("data", {})
        return {
            "success": True,
            "device_id": device_id,
            "config_type": request.config_type,
            "configuration": config_info
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get device config: {result.get('message', 'Unknown error')}"
        )

@router.get("/status/all")
def get_all_device_statuses(current_user: dict = Depends(get_current_user)):
    """
    Get real-time status for all user devices.
    """
    user_devices = get_user_devices(current_user["user_id"], is_admin=current_user.get("is_admin", False))
    user_device_ids = [device.device_id for device in user_devices]
    
    if not user_device_ids:
        return {
            "success": True,
            "device_statuses": [],
            "message": "No devices assigned to this user"
        }
    
    # Get status from manufacturer API
    try:
        result = manufacturer_api.get_device_status_list()
        if result.get("code") == 0:
            all_statuses = result.get("data", {}).get("devices", [])
            
            # Filter to only include user's devices
            user_statuses = []
            for status in all_statuses:
                if status.get("deviceId") in user_device_ids:
                    # Find the device name from local database
                    device = next((d for d in user_devices if d.device_id == status.get("deviceId")), None)
                    device_name = device.name if device else status.get("deviceId")
                    
                    user_statuses.append({
                        "device_id": status.get("deviceId"),
                        "device_name": device_name,
                        "status": status.get("status"),
                        "last_seen": status.get("lastSeen"),
                        "ip_address": status.get("ipAddress"),
                        "signal_strength": status.get("signalStrength"),
                        "battery_level": status.get("batteryLevel"),
                        "storage_usage": status.get("storageUsage")
                    })
            
            return {
                "success": True,
                "device_statuses": user_statuses,
                "total_devices": len(user_statuses),
                "online_devices": len([s for s in user_statuses if s.get("status") == "online"]),
                "offline_devices": len([s for s in user_statuses if s.get("status") == "offline"])
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to get device statuses: {result.get('message', 'Unknown error')}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching device statuses: {str(e)}")

@router.get("/organization/tree")
def get_organization_tree(current_user: dict = Depends(get_current_user)):
    """
    Get organization tree structure.
    This shows the organizational hierarchy in the manufacturer system.
    """
    result = manufacturer_api.get_organization_tree()
    
    if result.get("code") == 0:
        org_data = result.get("data", {})
        return {
            "success": True,
            "organization_tree": org_data,
            "message": "Organization tree retrieved successfully"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get organization tree: {result.get('message', 'Unknown error')}"
        )

class AddDeviceRequest(BaseModel):
    device_id: str

@router.post("/add")
def add_device_to_user(
    request: AddDeviceRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a device to the current user's account.
    - If device exists and is unassigned: Link it to user
    - If device exists and is assigned to another user:
      * Admin (ADMIN001) can take it
      * Regular users get an error
    - If device doesn't exist: Create it and link to user
    """
    db = SessionLocal()
    try:
        device_id = request.device_id.strip()
        user_id = current_user["user_id"]
        invoice_no = current_user["invoice_no"]
        
        # Check if user is admin
        is_admin = invoice_no == "ADMIN001"
        
        # Check if device exists
        device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
        
        if device:
            # Device exists
            if device.assigned_user_id is None:
                # Device is unassigned - link it to user
                device.assigned_user_id = user_id
                db.commit()
                
                # Try to populate cache with VMS data (non-blocking)
                _populate_device_cache(device_id, db)
                
                # Create default notification settings (OFF by default)
                _create_default_notification_settings(user_id, device_id, db)
                
                return {
                    "success": True,
                    "message": f"Device {device_id} has been added to your account",
                    "device": {
                        "id": device.id,
                        "device_id": device.device_id,
                        "name": device.name,
                        "status": device.status
                    }
                }
            elif device.assigned_user_id == user_id:
                # Device already assigned to this user
                # Still try to populate cache in case it's missing
                _populate_device_cache(device_id, db)
                
                # Ensure notification settings exist (in case they were missed)
                _create_default_notification_settings(user_id, device_id, db)
                
                return {
                    "success": True,
                    "message": f"Device {device_id} is already in your account",
                    "device": {
                        "id": device.id,
                        "device_id": device.device_id,
                        "name": device.name,
                        "status": device.status
                    }
                }
            else:
                # Device assigned to another user
                if is_admin:
                    # Admin can take devices from other users
                    old_user_id = device.assigned_user_id
                    device.assigned_user_id = user_id
                    db.commit()
                    
                    # Try to populate cache with VMS data (non-blocking)
                    _populate_device_cache(device_id, db)
                    
                    # Create default notification settings for admin
                    _create_default_notification_settings(user_id, device_id, db)
                    
                    return {
                        "success": True,
                        "message": f"Device {device_id} has been transferred to your account (admin privilege)",
                        "device": {
                            "id": device.id,
                            "device_id": device.device_id,
                            "name": device.name,
                            "status": device.status
                        }
                    }
                else:
                    # Regular user cannot take device from another user
                    raise HTTPException(
                        status_code=403,
                        detail=f"Device {device_id} is already assigned to another user"
                    )
        else:
            # Device doesn't exist - create it
            new_device = DeviceDB(
                device_id=device_id,
                name=f"Device {device_id}",
                assigned_user_id=user_id,
                org_id="ORG001",
                status="offline",
                created_at=datetime.utcnow()
            )
            db.add(new_device)
            db.commit()
            db.refresh(new_device)
            
            # Try to populate cache with VMS data (non-blocking)
            _populate_device_cache(device_id, db)
            
            # Create default notification settings (OFF by default)
            _create_default_notification_settings(user_id, device_id, db)
            
            return {
                "success": True,
                "message": f"Device {device_id} has been created and added to your account",
                "device": {
                    "id": new_device.id,
                    "device_id": new_device.device_id,
                    "name": new_device.name,
                    "status": new_device.status
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding device: {str(e)}")
    finally:
        db.close()

class RemoveDeviceRequest(BaseModel):
    device_id: str

@router.post("/remove")
def remove_device_from_user(
    request: RemoveDeviceRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a device from the current user's account.
    The device is unassigned (not deleted from database) so it can be reassigned later.
    """
    db = SessionLocal()
    try:
        device_id = request.device_id.strip()
        user_id = current_user["user_id"]
        
        # Find the device
        device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Check if device belongs to current user (admin can remove any device)
        is_admin = current_user.get("is_admin", False)
        if device.assigned_user_id != user_id and not is_admin:
            raise HTTPException(status_code=403, detail="You don't have permission to remove this device")
        
        if is_admin:
            db.delete(device)
            db.commit()
            return {
                "success": True,
                "message": f"Device {device_id} has been permanently deleted"
            }
        else:
            device.assigned_user_id = None
            db.commit()
            return {
                "success": True,
                "message": f"Device {device_id} has been removed from your account"
            }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing device: {str(e)}")
    finally:
        db.close()

@router.put("/rename")
def rename_device(
    rename_request: DeviceRenameRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Rename a device. Only the user who owns the device can rename it.
    """
    db = SessionLocal()
    try:
        # Find the device
        device = db.query(DeviceDB).filter(
            DeviceDB.device_id == rename_request.device_id
        ).first()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Check if device belongs to current user
        if device.assigned_user_id != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="You don't have permission to rename this device")
        
        # Update device name
        device.name = rename_request.new_name
        db.commit()
        
        return {
            "success": True,
            "message": "Device renamed successfully",
            "device": {
                "device_id": device.device_id,
                "name": device.name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error renaming device: {str(e)}")
    finally:
        db.close()


@router.post("/{device_id}/activate")
def activate_device(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Activate a device by redirecting it from the manufacturer server (chinamdvr.com)
    to our own VMS server (vms.dashcamrd.com).
    
    This sends a server redirect command ($JTSVR1) to the device through
    the manufacturer's API. The device will then reconnect to our server.
    
    Use this when:
    - A new device is powered on for the first time (defaults to chinamdvr.com)
    - A device needs to be reconfigured to point to our server
    """
    # Verify user has access to this device
    user_devices = get_user_devices(current_user["user_id"], is_admin=current_user.get("is_admin", False))
    user_device_ids = [device.device_id for device in user_devices]
    
    if device_id not in user_device_ids:
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    logger.info(f"🚀 User {current_user['user_id']} activating device {device_id}")
    
    # Send activation command through ChinaMDVR service
    result = chinamdvr_service.activate_device(device_id)
    
    if result.get("success"):
        return {
            "success": True,
            "message": result.get("message"),
            "device_id": device_id,
            "command_sent": result.get("command"),
            "target_server": "vms.dashcamrd.com:9339"
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Failed to activate device")
        )


class ParkingModeRequest(BaseModel):
    enabled: bool


@router.post("/{device_id}/parking-mode")
def set_parking_mode(
    device_id: str,
    request: ParkingModeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Enable or disable parking mode for a device.

    When enabled the camera stays in a low-power monitoring state while
    ACC is OFF.  The VMS will show the device as ONLINE with acc_mode
    "orange" (سكون).

    Enabling queues a command to the device (command string TBD).
    Disabling sends the standard auto-config command to reset the device.
    """
    user_devices = get_user_devices(
        current_user["user_id"],
        is_admin=current_user.get("is_admin", False),
    )
    user_device_ids = [d.device_id for d in user_devices]

    if device_id not in user_device_ids:
        raise HTTPException(status_code=403, detail="Device not accessible")

    db = SessionLocal()
    try:
        device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        device.parking_mode = request.enabled
        db.commit()

        # Also update the cache so API responses reflect the change immediately
        cache = db.query(DeviceCacheDB).filter(
            DeviceCacheDB.device_id == device_id
        ).first()
        if cache:
            cache.parking_mode = request.enabled
            # If turning on parking mode while ACC is off, mark device online
            if request.enabled and not cache.acc_status:
                cache.is_online = True
                cache.last_online_time = datetime.utcnow()
            cache.updated_at = datetime.utcnow()
            db.commit()

        # Send the appropriate command to the device
        from services.device_auto_config_service import DeviceAutoConfigService

        command_sent = False
        if request.enabled:
            # Parking mode enable command — placeholder until firmware command is provided.
            # Once the actual command string is known, set it here.
            command_content = None
            if command_content:
                result = manufacturer_api.send_text({
                    "name": f"ParkingMode-Enable-{device_id}",
                    "content": command_content,
                    "contentTypes": ["1"],
                    "deviceId": device_id,
                    "operator": "system"
                })
                command_sent = result.get("code") in [0, 200] or result.get("message") == "success"
                logger.info(f"🅿️ Parking mode ENABLE command sent to {device_id}: {result}")
        else:
            result = manufacturer_api.send_text({
                "name": f"ParkingMode-Disable-{device_id}",
                "content": DeviceAutoConfigService.CONFIG_COMMAND,
                "contentTypes": ["1"],
                "deviceId": device_id,
                "operator": "system"
            })
            command_sent = result.get("code") in [0, 200] or result.get("message") == "success"
            logger.info(f"🅿️ Parking mode DISABLE command sent to {device_id}: {result}")

        acc_on = cache.acc_status if cache else False
        return {
            "success": True,
            "device_id": device_id,
            "parking_mode": request.enabled,
            "command_sent": command_sent,
            **acc_mode_response(acc_on, request.enabled),
            "message": (
                "وضع السكون مفعّل" if request.enabled
                else "وضع السكون معطّل"
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error setting parking mode for {device_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error setting parking mode: {str(e)}")
    finally:
        db.close()


@router.get("/{device_id}/sleep-sessions")
def get_sleep_sessions(
    device_id: str,
    limit: int = Query(5, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """
    Return recent sleep sessions for a device.

    A sleep session starts when ACC turns OFF (alarm_type 999003) and ends
    when ACC turns ON (alarm_type 999002).  If the latest ACC event is OFF
    and the device cache still shows acc_status=False, the session is
    marked as ongoing with end_time=null.
    """
    user_devices = get_user_devices(
        current_user["user_id"],
        is_admin=current_user.get("is_admin", False),
    )
    if device_id not in [d.device_id for d in user_devices]:
        raise HTTPException(status_code=403, detail="Device not accessible")

    db = SessionLocal()
    try:
        # Fetch ACC ON/OFF alarms ordered newest-first
        acc_alarms = (
            db.query(AlarmDB)
            .filter(
                AlarmDB.device_id == device_id,
                AlarmDB.alarm_type.in_([999002, 999003]),
            )
            .order_by(AlarmDB.alarm_time.desc())
            .limit(200)
            .all()
        )

        # Check current ACC status from cache
        cache = db.query(DeviceCacheDB).filter(
            DeviceCacheDB.device_id == device_id
        ).first()
        current_acc_on = cache.acc_status if cache else True

        # Build sessions by pairing ACC OFF → ACC ON
        sessions = []
        i = 0
        while i < len(acc_alarms):
            alarm = acc_alarms[i]

            if alarm.alarm_type == 999002:
                # ACC ON — this is the END of a sleep session.
                # Look ahead for the matching ACC OFF that started it.
                end_time = alarm.alarm_time
                i += 1
                # Find the next ACC OFF (going backwards in time)
                if i < len(acc_alarms) and acc_alarms[i].alarm_type == 999003:
                    start_time = acc_alarms[i].alarm_time
                    duration_sec = int((end_time - start_time).total_seconds())
                    sessions.append({
                        "start_time": int(start_time.replace(tzinfo=timezone.utc).timestamp()),
                        "end_time": int(end_time.replace(tzinfo=timezone.utc).timestamp()),
                        "duration_minutes": max(duration_sec // 60, 1),
                        "status": "completed",
                    })
                    i += 1
                else:
                    # ACC ON without a preceding ACC OFF in our window — skip
                    continue

            elif alarm.alarm_type == 999003:
                # ACC OFF — this could be an ongoing session
                start_time = alarm.alarm_time
                if not current_acc_on and len(sessions) == 0:
                    # Latest event is ACC OFF and cache confirms ACC is still off
                    now = datetime.utcnow()
                    duration_sec = int((now - start_time).total_seconds())
                    sessions.append({
                        "start_time": int(start_time.replace(tzinfo=timezone.utc).timestamp()),
                        "end_time": None,
                        "duration_minutes": max(duration_sec // 60, 1),
                        "status": "ongoing",
                    })
                i += 1
            else:
                i += 1

        # Apply pagination
        paginated = sessions[offset:offset + limit]

        return {
            "success": True,
            "device_id": device_id,
            "sessions": paginated,
            "total": len(sessions),
            "has_more": (offset + limit) < len(sessions),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching sleep sessions for {device_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

