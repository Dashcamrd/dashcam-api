"""
Alarms Router - Handles device alarms and alarm management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, time as dt_time
import logging
import uuid
import time
from adapters import StatisticsAdapter, GPSAdapter

logger = logging.getLogger(__name__)

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
    is_admin = current_user.get("is_admin", False)
    user_devices = get_user_devices(current_user["user_id"], is_admin=is_admin)
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
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Getting alarms for device {device_id} (last {hours}h)")
    
    # Build request using adapter
    current_time = int(time.time())
    start_time = current_time - (hours * 3600)
    query_data = StatisticsAdapter.build_alarm_query_request(
        device_ids=[device_id],
        start_time=start_time,
        end_time=current_time,
        page_size=100  # Increase page size to get more alarms
    )
    
    logger.info(f"[{correlation_id}] Alarm query request: {query_data}")
    
    # Call manufacturer API
    result = manufacturer_api.get_vehicle_alarms(query_data)
    
    # Log raw vendor response for debugging
    import json
    logger.info(f"[{correlation_id}] 🔍 RAW ALARM RESPONSE: {json.dumps(result)[:1000]}")
    
    # Parse response using adapter with correlation ID
    alarm_summary = StatisticsAdapter.parse_alarm_response(result, device_id, correlation_id)
    
    logger.info(f"[{correlation_id}] Parsed {alarm_summary.total_alarms} alarms")
    
    return {
        "success": True,
        "device_id": device_id,
        "time_range": f"Last {hours} hours",
        "alarms": [a.model_dump(by_alias=False) for a in alarm_summary.alarms],
        "total_alarms": alarm_summary.total_alarms,
        "alarm_summary": {
            "critical": alarm_summary.critical_count,
            "warning": alarm_summary.warning_count,
            "info": alarm_summary.info_count
        }
    }


@router.get("/gps/{device_id}")
def get_alarms_from_gps(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (default: today)"),
    hours: Optional[int] = Query(None, description="Alternative: hours to look back")
):
    """
    Get alarms extracted from GPS track data.
    
    This uses /api/v2/gps/search to fetch GPS points and extracts alarm flags.
    More reliable than the statistics alarms endpoint.
    
    Params:
        - date: Specific date to query (YYYY-MM-DD format)
        - hours: Hours to look back from now (alternative to date)
        
    Note: The vendor API limits queries to 3 days max.
    """
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    
    # Calculate time range
    current_time = int(time.time())
    
    if date:
        # Parse date string
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_datetime = datetime.combine(date_obj.date(), dt_time.min)
            end_datetime = datetime.combine(date_obj.date(), dt_time.max)
            start_time = int(start_datetime.timestamp())
            end_time = int(end_datetime.timestamp())
            time_range_label = date
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    elif hours:
        # Hours-based query
        start_time = current_time - (hours * 3600)
        end_time = current_time
        time_range_label = f"Last {hours} hours"
    else:
        # Default: today
        today = datetime.now()
        start_datetime = datetime.combine(today.date(), dt_time.min)
        end_datetime = datetime.combine(today.date(), dt_time.max)
        start_time = int(start_datetime.timestamp())
        end_time = int(end_datetime.timestamp())
        time_range_label = "Today"
    
    # Ensure we don't exceed 3-day limit
    max_duration = 3 * 24 * 3600  # 3 days in seconds
    if end_time - start_time > max_duration:
        start_time = end_time - max_duration
        logger.warning(f"[{correlation_id}] Time range exceeded 3 days, limiting to last 3 days")
    
    logger.info(f"[{correlation_id}] Getting GPS-based alarms for device {device_id} ({time_range_label})")
    logger.info(f"[{correlation_id}] Time range: {datetime.fromtimestamp(start_time)} to {datetime.fromtimestamp(end_time)}")
    
    # Build GPS search request
    track_data = {
        "deviceId": device_id,
        "startTime": start_time,
        "endTime": end_time
    }
    
    # Call manufacturer API (same as track playback)
    result = manufacturer_api.query_detailed_track(track_data)
    
    # Log response for debugging
    import json
    logger.info(f"[{correlation_id}] 🔍 GPS SEARCH RESPONSE CODE: {result.get('code')}")
    
    # Check for errors
    if result.get("code") not in [200, 0]:
        error_msg = result.get("message", "Unknown error")
        logger.error(f"[{correlation_id}] Vendor API error: {error_msg}")
        return {
            "success": False,
            "device_id": device_id,
            "time_range": time_range_label,
            "alarms": [],
            "total_alarms": 0,
            "message": f"Failed to fetch GPS data: {error_msg}"
        }
    
    # Parse alarms from GPS data
    alarms = GPSAdapter.parse_gps_alarms(result, device_id, correlation_id)
    
    # Count by severity
    critical_count = sum(1 for a in alarms if a.level == "critical")
    warning_count = sum(1 for a in alarms if a.level == "warning")
    info_count = sum(1 for a in alarms if a.level == "info")
    
    # 🔍 Detailed logging of alarm types found
    logger.info(f"[{correlation_id}] ===== GPS ALARMS SUMMARY =====")
    logger.info(f"[{correlation_id}] Total alarms found: {len(alarms)}")
    logger.info(f"[{correlation_id}] By severity - Critical: {critical_count}, Warning: {warning_count}, Info: {info_count}")
    
    # Log alarm type breakdown
    alarm_types = {}
    for a in alarms:
        alarm_type = a.message or "Unknown"
        alarm_types[alarm_type] = alarm_types.get(alarm_type, 0) + 1
    
    for alarm_type, count in sorted(alarm_types.items(), key=lambda x: -x[1]):
        logger.info(f"[{correlation_id}]   📍 {alarm_type}: {count}")
    
    logger.info(f"[{correlation_id}] ==============================")
    
    return {
        "success": True,
        "device_id": device_id,
        "time_range": time_range_label,
        "alarms": [a.model_dump(by_alias=False) for a in alarms],
        "total_alarms": len(alarms),
        "alarm_summary": {
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count
        }
    }

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


