"""
Admin Router - Handles administrative functions, user management, and system configuration
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, create_user
from services.manufacturer_api_service import manufacturer_api
from models.user import UserCreate, UserResponse
from models.user_db import UserDB
from models.device_db import DeviceDB
from database import SessionLocal
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])

class DeviceAssignment(BaseModel):
    device_id: str
    device_name: str
    user_id: int
    org_id: str

class SystemConfigRequest(BaseModel):
    config_key: str
    config_value: str
    config_type: Optional[str] = "general"
    description: Optional[str] = None

class ForwardingPlatformRequest(BaseModel):
    platform_name: str
    platform_url: str
    api_key: Optional[str] = None
    platform_type: str  # webhook, api, ftp, etc.

class ForwardingPolicyRequest(BaseModel):
    policy_name: str
    platform_id: str
    event_types: List[str]  # alarm, gps, video, etc.
    filters: Optional[dict] = None

def is_admin_user(current_user: dict) -> bool:
    """Check if current user has admin privileges"""
    # For now, simple check - in production you'd have role-based access
    # You can implement role checking based on your business logic
    return True  # Placeholder - implement proper admin role checking

@router.post("/users", response_model=UserResponse)
def create_new_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new user (admin only).
    This creates customers who will log in with invoice numbers.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = SessionLocal()
    try:
        result = create_user({
            "invoice_no": user_data.invoice_no,
            "password": user_data.password,
            "name": user_data.name,
            "email": user_data.email
        }, db)
        
        # Get the created user
        db_user = db.query(UserDB).filter(UserDB.invoice_no == user_data.invoice_no).first()
        return db_user
    finally:
        db.close()

@router.get("/users")
def list_all_users(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(20, description="Items per page")
):
    """
    List all users in the system (admin only).
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = SessionLocal()
    try:
        offset = (page - 1) * page_size
        users = db.query(UserDB).offset(offset).limit(page_size).all()
        total = db.query(UserDB).count()
        
        user_list = []
        for user in users:
            # Get device count for each user
            device_count = db.query(DeviceDB).filter(DeviceDB.assigned_user_id == user.id).count()
            
            user_list.append({
                "id": user.id,
                "invoice_no": user.invoice_no,
                "name": user.name,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
                "device_count": device_count
            })
        
        return {
            "success": True,
            "users": user_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    finally:
        db.close()

@router.post("/devices/assign")
def assign_device_to_user(
    assignment: DeviceAssignment,
    current_user: dict = Depends(get_current_user)
):
    """
    Assign a device to a user (admin only).
    Creates device record in local database and links to user.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(UserDB).filter(UserDB.id == assignment.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if device already exists
        existing_device = db.query(DeviceDB).filter(DeviceDB.device_id == assignment.device_id).first()
        if existing_device:
            raise HTTPException(status_code=400, detail="Device already assigned")
        
        # Create device assignment
        new_device = DeviceDB(
            device_id=assignment.device_id,
            name=assignment.device_name,
            assigned_user_id=assignment.user_id,
            org_id=assignment.org_id,
            status="offline"
        )
        
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        
        return {
            "success": True,
            "message": "Device assigned successfully",
            "assignment": {
                "device_id": assignment.device_id,
                "device_name": assignment.device_name,
                "user_invoice": user.invoice_no,
                "user_name": user.name
            }
        }
    finally:
        db.close()

@router.get("/devices/unassigned")
def get_unassigned_devices(current_user: dict = Depends(get_current_user)):
    """
    Get devices from manufacturer API that are not yet assigned to users.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all devices from manufacturer API
    result = manufacturer_api.get_user_device_list()
    
    if result.get("code") != 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get device list: {result.get('message', 'Unknown error')}"
        )
    
    manufacturer_devices = result.get("data", {}).get("devices", [])
    
    # Get assigned devices from local database
    db = SessionLocal()
    try:
        assigned_device_ids = db.query(DeviceDB.device_id).all()
        assigned_device_ids = [device_id[0] for device_id in assigned_device_ids]
        
        # Filter unassigned devices
        unassigned_devices = []
        for device in manufacturer_devices:
            device_id = device.get("deviceId")
            if device_id not in assigned_device_ids:
                unassigned_devices.append({
                    "device_id": device_id,
                    "device_name": device.get("deviceName", device_id),
                    "org_id": device.get("orgId"),
                    "status": device.get("status", "unknown"),
                    "device_type": device.get("deviceType"),
                    "last_seen": device.get("lastSeen")
                })
        
        return {
            "success": True,
            "unassigned_devices": unassigned_devices,
            "total_unassigned": len(unassigned_devices),
            "total_manufacturer_devices": len(manufacturer_devices),
            "total_assigned": len(assigned_device_ids)
        }
    finally:
        db.close()

@router.post("/config/system")
def manage_system_config(
    request: SystemConfigRequest,
    action: str = Query(..., description="Action: add, modify, delete"),
    current_user: dict = Depends(get_current_user)
):
    """
    Manage system configuration via manufacturer API.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    config_data = {
        "configKey": request.config_key,
        "configValue": request.config_value,
        "configType": request.config_type,
        "description": request.description
    }
    
    if action == "add":
        result = manufacturer_api.add_system_config(config_data)
    elif action == "modify":
        result = manufacturer_api.modify_system_config(config_data)
    elif action == "delete":
        result = manufacturer_api.delete_system_config({"configKey": request.config_key})
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use: add, modify, delete")
    
    if result.get("code") == 0:
        return {
            "success": True,
            "action": action,
            "config_key": request.config_key,
            "message": f"Configuration {action} successful"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to {action} configuration: {result.get('message', 'Unknown error')}"
        )

@router.get("/config/system")
def query_system_config(
    current_user: dict = Depends(get_current_user),
    config_type: Optional[str] = Query(None, description="Filter by config type")
):
    """
    Query system configuration.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query_data = {"configType": config_type} if config_type else {}
    result = manufacturer_api.query_system_config(query_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "configurations": result.get("data", {}),
            "filter": {"config_type": config_type}
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to query configuration: {result.get('message', 'Unknown error')}"
        )

@router.post("/forwarding/platform")
def create_forwarding_platform(
    request: ForwardingPlatformRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a forwarding platform for data integration.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    platform_data = {
        "platformName": request.platform_name,
        "platformUrl": request.platform_url,
        "apiKey": request.api_key,
        "platformType": request.platform_type
    }
    
    result = manufacturer_api.create_forwarding_platform(platform_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "platform": {
                "name": request.platform_name,
                "url": request.platform_url,
                "type": request.platform_type,
                "platform_id": result.get("data", {}).get("platformId")
            },
            "message": "Forwarding platform created successfully"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to create platform: {result.get('message', 'Unknown error')}"
        )

@router.post("/forwarding/policy")
def create_forwarding_policy(
    request: ForwardingPolicyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a forwarding policy for automatic data forwarding.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    policy_data = {
        "policyName": request.policy_name,
        "platformId": request.platform_id,
        "eventTypes": request.event_types,
        "filters": request.filters or {}
    }
    
    result = manufacturer_api.create_forwarding_policy(policy_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "policy": {
                "name": request.policy_name,
                "platform_id": request.platform_id,
                "event_types": request.event_types,
                "policy_id": result.get("data", {}).get("policyId")
            },
            "message": "Forwarding policy created successfully"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to create policy: {result.get('message', 'Unknown error')}"
        )

@router.get("/dashboard/overview")
def get_admin_dashboard_overview(current_user: dict = Depends(get_current_user)):
    """
    Get overview data for admin dashboard.
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = SessionLocal()
    try:
        # Get basic statistics
        total_users = db.query(UserDB).count()
        total_devices = db.query(DeviceDB).count()
        
        # Get device status counts
        online_devices = 0
        offline_devices = 0
        
        try:
            status_result = manufacturer_api.get_device_status_list()
            if status_result.get("code") == 0:
                device_statuses = status_result.get("data", {}).get("devices", [])
                for status in device_statuses:
                    if status.get("status") == "online":
                        online_devices += 1
                    else:
                        offline_devices += 1
        except:
            pass
        
        # Get recent users (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = db.query(UserDB).filter(UserDB.created_at >= week_ago).count()
        
        return {
            "success": True,
            "overview": {
                "total_users": total_users,
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": offline_devices,
                "recent_users": recent_users,
                "system_status": "operational",
                "api_connection": "connected" if manufacturer_api.token else "disconnected"
            }
        }
    finally:
        db.close()


