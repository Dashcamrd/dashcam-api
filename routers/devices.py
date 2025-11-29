"""
Devices Router - Handles device management and configuration
"""
from fastapi import APIRouter, Depends, HTTPException
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter(prefix="/devices", tags=["Devices"])

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
        device_info = {
            "id": device.id,
            "device_id": device.device_id,
            "name": device.name,
            "status": device.status,
            "org_id": device.org_id,
            "brand": device.brand,
            "model": device.model,
            "firmware_version": device.firmware_version,
            "created_at": device.created_at.isoformat(),
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
    device_info = {
        "id": device.id,
        "device_id": device.device_id,
        "name": device.name,
        "status": device.status,
        "org_id": device.org_id,
        "brand": device.brand,
        "model": device.model,
        "firmware_version": device.firmware_version,
        "created_at": device.created_at.isoformat()
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


