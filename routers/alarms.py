"""
Alarms Router - Handles device alarms and alarm management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/alarms", tags=["Alarms"])

class AlarmQueryRequest(BaseModel):
    device_id: str
    start_time: Optional[str] = None  # format: "2024-01-01 10:00:00"
    end_time: Optional[str] = None    # format: "2024-01-01 11:00:00"

class AttachmentRequest(BaseModel):
    alarm_id: str
    attachment_type: Optional[str] = "image"  # image, video, etc.

def verify_device_access(device_id: str, current_user: dict) -> bool:
    """Verify that the current user has access to the specified device"""
    user_devices = get_user_devices(current_user["user_id"])
    user_device_ids = [device.device_id for device in user_devices]
    return device_id in user_device_ids

@router.get("/recent/{device_id}")
def get_recent_alarms(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    hours: Optional[int] = Query(3, description="Hours to look back (default: 3)")
):
    """
    Get recent alarms for a device (default: last 3 hours).
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    query_data = {
        "deviceId": device_id,
        "hours": hours
    }
    result = manufacturer_api.get_vehicle_alarms(query_data)
    
    if result.get("code") == 0:
        alarms_data = result.get("data", {})
        alarms = alarms_data.get("alarms", [])
        
        # Process alarms to add user-friendly information
        processed_alarms = []
        for alarm in alarms:
            processed_alarms.append({
                "alarm_id": alarm.get("id"),
                "device_id": device_id,
                "type": alarm.get("type"),
                "level": alarm.get("level"),  # warning, critical, etc.
                "message": alarm.get("message"),
                "timestamp": alarm.get("timestamp"),
                "location": {
                    "latitude": alarm.get("latitude"),
                    "longitude": alarm.get("longitude"),
                    "address": alarm.get("address")
                },
                "has_attachment": alarm.get("hasAttachment", False),
                "status": alarm.get("status", "active")
            })
        
        return {
            "success": True,
            "device_id": device_id,
            "time_range": f"Last {hours} hours",
            "alarms": processed_alarms,
            "total_alarms": len(processed_alarms),
            "alarm_summary": {
                "critical": len([a for a in processed_alarms if a.get("level") == "critical"]),
                "warning": len([a for a in processed_alarms if a.get("level") == "warning"]),
                "info": len([a for a in processed_alarms if a.get("level") == "info"])
            }
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get alarms: {result.get('message', 'Unknown error')}"
        )

@router.post("/query")
def query_alarms_by_time_range(
    request: AlarmQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Query alarms for a device within a specific time range.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    query_data = {
        "deviceId": request.device_id,
        "startTime": request.start_time,
        "endTime": request.end_time
    }
    result = manufacturer_api.get_vehicle_alarms(query_data)
    
    if result.get("code") == 0:
        alarms_data = result.get("data", {})
        return {
            "success": True,
            "device_id": request.device_id,
            "time_range": f"{request.start_time} to {request.end_time}",
            "alarms": alarms_data.get("alarms", []),
            "total_alarms": len(alarms_data.get("alarms", []))
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to query alarms: {result.get('message', 'Unknown error')}"
        )

@router.get("/types")
def get_alarm_types(current_user: dict = Depends(get_current_user)):
    """
    Get available alarm type descriptions.
    This helps frontend display user-friendly alarm names.
    """
    result = manufacturer_api.get_alarm_type_descriptions()
    
    if result.get("code") == 0:
        types_data = result.get("data", {})
        return {
            "success": True,
            "alarm_types": types_data.get("types", {}),
            "message": "Alarm type descriptions retrieved successfully"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get alarm types: {result.get('message', 'Unknown error')}"
        )

@router.post("/attachment")
def get_alarm_attachment(
    request: AttachmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get attachment (image/video) for a specific alarm.
    Returns base64 encoded file data.
    """
    # Note: We should verify that the alarm belongs to a device the user has access to
    # For now, we'll call the API and let it handle permissions
    
    attachment_data = {
        "alarmId": request.alarm_id,
        "type": request.attachment_type
    }
    result = manufacturer_api.get_attachment(attachment_data)
    
    if result.get("code") == 0:
        attachment_data = result.get("data", {})
        return {
            "success": True,
            "alarm_id": request.alarm_id,
            "attachment_type": request.attachment_type,
            "file_data": attachment_data.get("fileData"),  # base64 encoded
            "file_name": attachment_data.get("fileName"),
            "file_size": attachment_data.get("fileSize"),
            "content_type": attachment_data.get("contentType")
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get attachment: {result.get('message', 'Unknown error')}"
        )

@router.get("/summary")
def get_alarms_summary(
    current_user: dict = Depends(get_current_user),
    hours: Optional[int] = Query(24, description="Hours to look back (default: 24)")
):
    """
    Get alarm summary for all user devices.
    Provides a dashboard overview of alarm activity.
    """
    user_devices = get_user_devices(current_user["user_id"])
    
    if not user_devices:
        return {
            "success": True,
            "summary": {
                "total_devices": 0,
                "total_alarms": 0,
                "devices_with_alarms": 0,
                "alarm_breakdown": {},
                "recent_critical_alarms": []
            }
        }
    
    summary = {
        "total_devices": len(user_devices),
        "total_alarms": 0,
        "devices_with_alarms": 0,
        "alarm_breakdown": {"critical": 0, "warning": 0, "info": 0},
        "recent_critical_alarms": [],
        "device_summaries": []
    }
    
    for device in user_devices:
        try:
            query_data = {
                "deviceId": device.device_id,
                "hours": hours
            }
            result = manufacturer_api.get_vehicle_alarms(query_data)
            
            if result.get("code") == 0:
                alarms_data = result.get("data", {})
                device_alarms = alarms_data.get("alarms", [])
                
                if device_alarms:
                    summary["devices_with_alarms"] += 1
                    summary["total_alarms"] += len(device_alarms)
                    
                    # Count alarm levels
                    for alarm in device_alarms:
                        level = alarm.get("level", "info")
                        if level in summary["alarm_breakdown"]:
                            summary["alarm_breakdown"][level] += 1
                        
                        # Collect critical alarms
                        if level == "critical":
                            summary["recent_critical_alarms"].append({
                                "device_id": device.device_id,
                                "device_name": device.name,
                                "alarm_type": alarm.get("type"),
                                "message": alarm.get("message"),
                                "timestamp": alarm.get("timestamp")
                            })
                
                summary["device_summaries"].append({
                    "device_id": device.device_id,
                    "device_name": device.name,
                    "alarm_count": len(device_alarms),
                    "last_alarm": device_alarms[0].get("timestamp") if device_alarms else None
                })
                
        except Exception as e:
            # If alarm fetch fails for a device, still include it
            summary["device_summaries"].append({
                "device_id": device.device_id,
                "device_name": device.name,
                "alarm_count": 0,
                "last_alarm": None,
                "error": str(e)
            })
    
    # Sort critical alarms by timestamp (most recent first)
    summary["recent_critical_alarms"] = sorted(
        summary["recent_critical_alarms"], 
        key=lambda x: x.get("timestamp", ""), 
        reverse=True
    )[:10]  # Limit to 10 most recent
    
    return {
        "success": True,
        "time_range": f"Last {hours} hours",
        "summary": summary
    }


