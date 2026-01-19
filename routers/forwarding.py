"""
Data Forwarding Router - Receives real-time data pushed by vendor.

This implements the webhook/data forwarding pattern where the vendor
pushes GPS, Alarm, and Device Status data to our backend instead of
us polling the vendor API repeatedly.

Flow:
1. Vendor detects device event (GPS update, alarm, status change)
2. Vendor POSTs data to our /api/forwarding/receive endpoint
3. We store data in device_cache table
4. Mobile app fetches from our cached data (fast!)
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional
import json
import logging
import os

from database import SessionLocal
from models.device_cache_db import DeviceCacheDB, AlarmDB
from services.geocoding_service import GeocodingService
from services.notification_service import NotificationService

router = APIRouter(prefix="/api/forwarding", tags=["Data Forwarding"])
logger = logging.getLogger(__name__)

# Vendor authentication secret key (set in environment variables)
# If not set, authentication is disabled (for development)
VENDOR_SECRET_KEY = os.getenv("VENDOR_FORWARDING_SECRET", None)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# ALARM TYPE MAPPINGS - Based on Vendor Documentation (6-digit typeId format)
# Format: AABBCC where AA=primary, BB=secondary, CC=tertiary category
# =============================================================================

# Alarm Category Mapping (alarm.type field → category prefix)
ALARM_CATEGORY_MAP = {
    1: {"prefix": 64, "name": "ADAS", "field": "adas"},   # Advanced Driver Assistance
    2: {"prefix": 65, "name": "DSM", "field": "dsm"},     # Driver Status Monitoring
    3: {"prefix": 66, "name": "BSD", "field": "bsd"},     # Blind Spot Detection
    4: {"prefix": 70, "name": "SDA", "field": "sda"},     # Severe Driving Alarms
}

# Complete Alarm Type Names (vendor 6-digit typeId → human-readable name)
ALARM_TYPE_NAMES = {
    # ADAS - Advanced Driver Assistance System (64xxxx)
    640001: "Forward Collision Warning",
    640002: "Lane Departure Warning",
    640003: "Following Distance Warning",
    640004: "Pedestrian Collision Warning",
    640005: "Frequent Lane Change Warning",
    640006: "Road Sign Recognition",
    640101: "Road Sign Recognition",
    
    # DSM - Driver Status Monitoring (65xxxx)
    650001: "Fatigue Driving Warning",
    650002: "Phone Call Warning",
    650003: "Smoking Warning",
    650004: "Distracted Driving Warning",
    650005: "Driver Abnormal Warning",
    650006: "Driver Change Warning",
    650007: "Infrared Blocking Warning",
    650008: "Sunglasses Warning",
    650009: "Yawning Warning",
    650010: "Camera Covered Warning",
    650011: "Seatbelt Warning",
    650012: "Driver Not Detected",
    
    # BSD - Blind Spot Detection (66xxxx)
    660001: "Rear Approach Warning",
    660002: "Left Rear Approach Warning",
    660003: "Right Rear Approach Warning",
    
    # SDA - Severe Driving Alarms (70xxxx)
    700001: "Rapid Acceleration Warning",
    700002: "Rapid Deceleration Warning",
    700003: "Sharp Turn Warning",
    700004: "Idling Warning",
    700005: "Abnormal Shutdown Warning",
    700006: "Neutral Sliding Warning",
    700007: "Engine Over-rev Warning",
    
    # Common Alarms (11xxxx)
    110100: "Emergency SOS",
    110101: "Speeding Alarm",
    110102: "Fatigue Driving Alarm",
    110103: "Danger Warning",
    110104: "GNSS Module Fault",
    110105: "GNSS Antenna Cut",
    110106: "GNSS Antenna Short Circuit",
    110107: "Main Power Undervoltage",
    110108: "Main Power Failure",
    110201: "Illegal Ignition",
    110202: "Illegal Movement",
    110203: "Collision Warning",
    110204: "Rollover Warning",
    110205: "Fuel Abnormal",
    110206: "Vehicle Stolen",
    110301: "Overtime Driving (Day)",
    110302: "Rest Time Insufficient",
    110303: "Route Deviation",
    110304: "VSS Fault",
    110305: "Oil Cut Circuit",
    
    # Channel Alarms (12xxxx)
    120101: "Video Loss Alarm",
    120102: "Video Signal Blocking",
    120103: "Storage Fault",
    120104: "Other Video Equipment Fault",
    120105: "Bus Overload",
    
    # Geofence Alarms (13xxxx)
    130101: "Enter Geofence",
    130102: "Exit Geofence",
    130103: "Route Entry",
    130104: "Route Exit",
    130105: "Route Driving Time Abnormal",
}

# Alarm severity levels by typeId prefix
CRITICAL_ALARM_PREFIXES = [110100, 110107, 110108, 110201, 110202, 110203, 110204, 110206]  # Emergency, Power, Collision, Theft
WARNING_ALARM_PREFIXES = [64, 65, 66, 70]  # ADAS, DSM, BSD, SDA categories

def get_alarm_type_id(alarm_item: dict) -> int:
    """
    Extract the full 6-digit alarm typeId from vendor alarm data.
    
    Vendor sends alarms with:
    - alarm.type: Category number (1=ADAS, 2=DSM, 3=BSD, 4=SDA)
    - alarm.{adas|dsm|bsd|sda}.alarmEventType: Specific alarm within category
    
    Returns the 6-digit typeId (e.g., 700003 for Sharp Turn Warning)
    """
    category_type = alarm_item.get("type")
    
    # Check if it's a categorized alarm (ADAS, DSM, BSD, SDA)
    if category_type in ALARM_CATEGORY_MAP:
        category = ALARM_CATEGORY_MAP[category_type]
        prefix = category["prefix"]
        field_name = category["field"]
        
        # Get the nested alarm details
        alarm_details = alarm_item.get(field_name, {})
        event_type = alarm_details.get("alarmEventType", 1)
        
        # Construct the 6-digit typeId: prefix * 10000 + event_type
        type_id = prefix * 10000 + event_type
        return type_id
    
    # For non-categorized alarms, check if typeId is directly provided
    if "typeId" in alarm_item:
        return alarm_item["typeId"]
    
    # Fallback: return the raw type if it looks like a 6-digit code
    if category_type and category_type > 100000:
        return category_type
    
    # Unknown format - return raw type with placeholder prefix
    return 999900 + (category_type or 0)

def get_alarm_name(type_id: int) -> str:
    """Get human-readable alarm name from typeId."""
    if type_id in ALARM_TYPE_NAMES:
        return ALARM_TYPE_NAMES[type_id]
    
    # Try to determine category from prefix
    prefix = type_id // 10000
    category_names = {64: "ADAS", 65: "DSM", 66: "BSD", 70: "SDA", 11: "Common", 12: "Channel", 13: "Geofence"}
    category = category_names.get(prefix, "Unknown")
    
    return f"{category} Alarm ({type_id})"

def get_alarm_level(type_id: int) -> int:
    """
    Determine alarm severity level.
    Returns: 3=Critical, 2=Warning, 1=Info
    """
    # Critical alarms
    if type_id in CRITICAL_ALARM_PREFIXES:
        return 3
    
    # Warning alarms (ADAS, DSM, BSD, SDA, Speeding)
    prefix = type_id // 10000
    if prefix in WARNING_ALARM_PREFIXES or type_id == 110101:
        return 2
    
    # Default: Info level
    return 1

def get_alarm_category(type_id: int) -> str:
    """Get alarm category name from typeId."""
    prefix = type_id // 10000
    categories = {
        64: "ADAS",
        65: "DSM", 
        66: "BSD",
        70: "SDA",
        11: "Common",
        12: "Channel",
        13: "Geofence",
    }
    return categories.get(prefix, "Unknown")


@router.post("/receive")
async def receive_forwarded_data(request: Request, db: Session = Depends(get_db)):
    """
    Receives real-time data forwarded from vendor.
    
    This endpoint is called automatically by the vendor when a device
    sends GPS data, triggers an alarm, or changes status.
    
    Message Types (msgId):
    - 1: GPS Location Data
    - 2: Alarm Data
    - 3: Device Status Notification (ACC, Online/Offline)
    
    Authentication:
    - Set VENDOR_FORWARDING_SECRET env var to enable
    - Vendor must send matching key in Authorization header or X-API-Key header
    """
    # Vendor authentication (if secret is configured)
    if VENDOR_SECRET_KEY:
        auth_header = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key", "")
        
        # Check Bearer token format
        if auth_header.startswith("Bearer "):
            provided_key = auth_header[7:]  # Remove "Bearer " prefix
        else:
            provided_key = api_key
        
        if provided_key != VENDOR_SECRET_KEY:
            logger.warning(f"⚠️ Unauthorized forwarding request from {request.client.host}")
            raise HTTPException(status_code=401, detail="Invalid vendor authentication key")
    
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    
    msg_id = data.get("msgId")
    
    # Extract device_id from appropriate location based on msgId
    if msg_id == 1:  # GPS - nested in gps.list[0].deviceId
        gps_list = data.get("gps", {}).get("list", [])
        device_id = gps_list[0].get("deviceId") if gps_list else None
    elif msg_id == 2:  # Alarm - nested in alarm.base.deviceId
        device_id = data.get("alarm", {}).get("base", {}).get("deviceId")
    elif msg_id == 3:  # Device Status
        device_id = data.get("deviceId") or data.get("imei")
    else:
        device_id = data.get("deviceId") or data.get("imei") or data.get("device_id")
    
    logger.info(f"📨 Received forwarded data: msgId={msg_id}, device={device_id}")
    
    try:
        if msg_id == 1:  # GPS Data
            await handle_gps_data(db, data)
        elif msg_id == 2:  # Alarm Data
            await handle_alarm_data(db, data)
        elif msg_id == 3:  # Device Status (ACC, Online/Offline)
            await handle_device_status(db, data)
        else:
            # Unknown message type - log and accept
            logger.warning(f"⚠️ Unknown msgId: {msg_id}, data: {json.dumps(data)[:500]}")
        
        return {
            "status": "received",
            "msgId": msg_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error processing forwarded data: {e}")
        # Still return 200 to prevent vendor from retrying
        # We don't want to lose data due to processing errors
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def handle_gps_data(db: Session, data: dict):
    """
    Process forwarded GPS data.
    
    Vendor format:
    {
        "msgId": 1,
        "gps": {
            "list": [{
                "deviceId": "18260010855",
                "latitude": 31.060734,
                "longitude": 121.414273,
                "speed": 0,
                "direction": 0,
                "time": 1765457419,
                "altitude": 0,
                "statusFlags": {"acc": true, ...}
            }]
        }
    }
    """
    # Extract GPS list from vendor's nested structure
    gps_container = data.get("gps", {})
    gps_list = gps_container.get("list", [])
    
    # Fallback: if no nested structure, try flat structure
    if not gps_list:
        gps_list = data.get("list", [data])
    
    if not isinstance(gps_list, list):
        gps_list = [gps_list]
    
    processed_count = 0
    
    for gps in gps_list:
        device_id = gps.get("deviceId") or gps.get("imei") or gps.get("device_id")
        if not device_id:
            logger.warning(f"⚠️ GPS data without device_id: {json.dumps(gps)[:200]}")
            continue
        
        lat = gps.get("latitude") or gps.get("lat")
        lng = gps.get("longitude") or gps.get("lng") or gps.get("lon")
        speed = gps.get("speed") or gps.get("spd")
        direction = gps.get("direction") or gps.get("course") or gps.get("dir")
        altitude = gps.get("altitude") or gps.get("alt")
        
        # Extract ACC status from statusFlags
        status_flags = gps.get("statusFlags", {})
        acc_status = status_flags.get("acc", False)
        
        # Parse GPS timestamp
        gps_timestamp = gps.get("time") or gps.get("gpsTime") or gps.get("timestamp")
        gps_time = None
        if gps_timestamp:
            if isinstance(gps_timestamp, int):
                # Unix timestamp in seconds
                gps_time = datetime.fromtimestamp(gps_timestamp)
            elif isinstance(gps_timestamp, str):
                try:
                    gps_time = datetime.fromisoformat(gps_timestamp.replace("Z", "+00:00"))
                except:
                    pass
        
        # Get geocoded address (optional, can be slow)
        address = None
        if lat and lng:
            try:
                address = GeocodingService.get_location_name(lat, lng)
            except:
                pass  # Don't fail on geocoding errors
        
        # Upsert device cache
        existing = db.query(DeviceCacheDB).filter(
            DeviceCacheDB.device_id == device_id
        ).first()
        
        # Track previous ACC status for notification
        previous_acc_status = None
        
        if existing:
            previous_acc_status = existing.acc_status
            existing.latitude = lat
            existing.longitude = lng
            existing.speed = speed
            existing.direction = direction
            existing.altitude = altitude
            existing.gps_time = gps_time
            existing.address = address
            existing.acc_status = acc_status  # Update ACC from GPS data
            existing.is_online = True  # Device sending GPS = online
            existing.last_online_time = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
        else:
            new_cache = DeviceCacheDB(
                device_id=device_id,
                latitude=lat,
                longitude=lng,
                speed=speed,
                direction=direction,
                altitude=altitude,
                gps_time=gps_time,
                address=address,
                acc_status=acc_status,
                is_online=True,
                last_online_time=datetime.utcnow()
            )
            db.add(new_cache)
        
        # Send push notification if ACC status changed
        if previous_acc_status is not None and previous_acc_status != acc_status:
            try:
                NotificationService.send_acc_notification(
                    db=db,
                    device_id=device_id,
                    acc_on=acc_status,
                    previous_acc_status=previous_acc_status
                )
                logger.info(f"📱 ACC change notification sent for {device_id}: {previous_acc_status} → {acc_status}")
            except Exception as e:
                logger.error(f"❌ Failed to send ACC notification: {e}")
        
        processed_count += 1
        logger.info(f"✅ Stored GPS for device {device_id}: lat={lat}, lng={lng}, acc={acc_status}")
    
    db.commit()
    logger.info(f"✅ Processed {processed_count} GPS records")


async def handle_device_status(db: Session, data: dict):
    """
    Process device status changes (ACC ON/OFF, Online/Offline).
    """
    device_id = data.get("deviceId") or data.get("imei") or data.get("device_id")
    if not device_id:
        logger.warning("⚠️ Device status without device_id")
        return
    
    # Extract status values
    acc_status = data.get("accStatus") or data.get("acc") or data.get("accState")
    online_status = data.get("online") or data.get("isOnline") or data.get("onlineStatus")
    
    # Convert to boolean
    if acc_status is not None:
        acc_status = acc_status in [True, 1, "1", "on", "ON"]
    
    if online_status is not None:
        online_status = online_status in [True, 1, "1", "on", "ON", "online"]
    
    # Upsert device cache
    existing = db.query(DeviceCacheDB).filter(
        DeviceCacheDB.device_id == device_id
    ).first()
    
    # Track previous ACC status for notification
    previous_acc_status = None
    
    if existing:
        previous_acc_status = existing.acc_status
        if acc_status is not None:
            existing.acc_status = acc_status
        if online_status is not None:
            existing.is_online = online_status
            if online_status:
                existing.last_online_time = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
    else:
        new_cache = DeviceCacheDB(
            device_id=device_id,
            acc_status=acc_status if acc_status is not None else False,
            is_online=online_status if online_status is not None else False,
            last_online_time=datetime.utcnow() if online_status else None
        )
        db.add(new_cache)
    
    db.commit()
    
    # Send push notification if ACC status changed
    if acc_status is not None and previous_acc_status is not None and previous_acc_status != acc_status:
        try:
            NotificationService.send_acc_notification(
                db=db,
                device_id=device_id,
                acc_on=acc_status,
                previous_acc_status=previous_acc_status
            )
            logger.info(f"📱 ACC change notification sent for {device_id}: {previous_acc_status} → {acc_status}")
        except Exception as e:
            logger.error(f"❌ Failed to send ACC notification: {e}")
    
    logger.info(f"✅ Updated status for {device_id}: ACC={acc_status}, Online={online_status}")


async def handle_alarm_data(db: Session, data: dict):
    """
    Process alarm events from vendor.
    
    Vendor format:
    {
        "msgId": 2,
        "alarm": {
            "base": {
                "deviceId": "18260010855",
                "latitude": 31.060734,
                "longitude": 121.414273,
                "time": 1765457449,
                "statusFlags": {"acc": true, ...}
            },
            "list": [
                {"type": 27, "Status": 0},
                {"type": 29, "Status": 0}
            ]
        }
    }
    """
    # Extract from vendor's nested structure
    alarm_container = data.get("alarm", {})
    base_info = alarm_container.get("base", {})
    alarm_list = alarm_container.get("list", [])
    
    # Get device ID from base info
    device_id = base_info.get("deviceId") or base_info.get("imei") or data.get("deviceId")
    if not device_id:
        logger.warning(f"⚠️ Alarm without device_id: {json.dumps(data)[:300]}")
        return
    
    # Extract location from base info
    lat = base_info.get("latitude") or base_info.get("lat")
    lng = base_info.get("longitude") or base_info.get("lng") or base_info.get("lon")
    speed = base_info.get("speed")
    direction = base_info.get("direction")
    
    # Parse alarm time from base info
    alarm_timestamp = base_info.get("time") or base_info.get("alarmTime") or base_info.get("timestamp")
    alarm_time = datetime.utcnow()
    if alarm_timestamp:
        if isinstance(alarm_timestamp, int):
            alarm_time = datetime.fromtimestamp(alarm_timestamp)
        elif isinstance(alarm_timestamp, str):
            try:
                alarm_time = datetime.fromisoformat(alarm_timestamp.replace("Z", "+00:00"))
            except:
                pass
    
    # Also update device cache with this location data (device is online if sending alarms)
    existing_cache = db.query(DeviceCacheDB).filter(
        DeviceCacheDB.device_id == device_id
    ).first()
    
    status_flags = base_info.get("statusFlags", {})
    acc_status = status_flags.get("acc", False)
    
    if existing_cache:
        if lat and lng:
            existing_cache.latitude = lat
            existing_cache.longitude = lng
        existing_cache.acc_status = acc_status
        existing_cache.is_online = True
        existing_cache.last_online_time = datetime.utcnow()
        existing_cache.updated_at = datetime.utcnow()
    elif lat and lng:
        new_cache = DeviceCacheDB(
            device_id=device_id,
            latitude=lat,
            longitude=lng,
            acc_status=acc_status,
            is_online=True,
            last_online_time=datetime.utcnow()
        )
        db.add(new_cache)
    
    # Process each alarm type in the list
    processed_count = 0
    
    for alarm_item in alarm_list:
        raw_type = alarm_item.get("type")
        alarm_status = alarm_item.get("Status", 0)  # 0 = inactive, 1 = active
        
        # Extract full 6-digit typeId using new parsing logic
        type_id = get_alarm_type_id(alarm_item)
        alarm_type_name = get_alarm_name(type_id)
        alarm_category = get_alarm_category(type_id)
        alarm_level = get_alarm_level(type_id)
        
        # Extract attachment count if available (from nested sda/adas/dsm/bsd object)
        attachment_count = 0
        for field in ["sda", "adas", "dsm", "bsd"]:
            if field in alarm_item:
                alarm_identifier = alarm_item[field].get("alarmIdentifier", {})
                attachment_count = alarm_identifier.get("attachmentCount", 0)
                break
        
        # Log ALL alarms received (for visibility)
        logger.info(
            f"📋 Alarm received: {alarm_type_name} "
            f"(typeId={type_id}, category={alarm_category}, rawType={raw_type}, status={alarm_status}, attachments={attachment_count}) - "
            f"{'ACTIVE ✓' if alarm_status == 1 else 'inactive, skipping'}"
        )
        
        # Only store ACTIVE alarms (Status=1) to save database space
        # Status=0 means "alarm cleared/inactive" - no need to store
        if alarm_status != 1:
            continue  # Skip inactive alarms
        
        # Create alarm record with full vendor typeId
        new_alarm = AlarmDB(
            device_id=device_id,
            alarm_type=type_id,  # Now stores 6-digit vendor typeId
            alarm_type_name=alarm_type_name,
            alarm_level=alarm_level,
            latitude=lat,
            longitude=lng,
            speed=speed,
            alarm_time=alarm_time,
            alarm_data=json.dumps({
                "base": base_info, 
                "alarm": alarm_item,
                "parsed": {
                    "typeId": type_id,
                    "category": alarm_category,
                    "attachmentCount": attachment_count
                }
            })
        )
        db.add(new_alarm)
        processed_count += 1
        
        logger.info(f"🚨 Alarm for {device_id}: {alarm_type_name} (typeId={type_id}, category={alarm_category})")
    
    db.commit()
    logger.info(f"✅ Processed {processed_count} alarms for device {device_id}")


# ============================================================================
# Endpoints for Mobile App to fetch cached data
# ============================================================================

@router.get("/device/{device_id}/status")
async def get_cached_device_status(device_id: str, db: Session = Depends(get_db)):
    """
    Get cached device status for a single device.
    This is FAST because it reads from our database, not vendor API.
    """
    cache = db.query(DeviceCacheDB).filter(
        DeviceCacheDB.device_id == device_id
    ).first()
    
    if not cache:
        raise HTTPException(status_code=404, detail="Device not found in cache")
    
    return {
        "device_id": cache.device_id,
        "latitude": cache.latitude,
        "longitude": cache.longitude,
        "speed": cache.speed,
        "direction": cache.direction,
        "address": cache.address,
        "acc_status": cache.acc_status,
        "is_online": cache.is_online,
        "gps_time": cache.gps_time.isoformat() if cache.gps_time else None,
        "last_online_time": cache.last_online_time.isoformat() if cache.last_online_time else None,
        "updated_at": cache.updated_at.isoformat() if cache.updated_at else None
    }


@router.get("/devices/status")
async def get_all_cached_device_statuses(db: Session = Depends(get_db)):
    """
    Get cached status for ALL devices in one call.
    Much more efficient than calling vendor API for each device.
    """
    caches = db.query(DeviceCacheDB).all()
    
    return {
        "count": len(caches),
        "devices": [
            {
                "device_id": c.device_id,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "speed": c.speed,
                "direction": c.direction,
                "address": c.address,
                "acc_status": c.acc_status,
                "is_online": c.is_online,
                "gps_time": c.gps_time.isoformat() if c.gps_time else None,
                "last_online_time": c.last_online_time.isoformat() if c.last_online_time else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            }
            for c in caches
        ]
    }


@router.get("/device/{device_id}/alarms")
async def get_device_alarms(
    device_id: str,
    limit: int = 50,
    unread_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get alarm history for a device.
    """
    query = db.query(AlarmDB).filter(AlarmDB.device_id == device_id)
    
    if unread_only:
        query = query.filter(AlarmDB.is_read == False)
    
    alarms = query.order_by(AlarmDB.alarm_time.desc()).limit(limit).all()
    
    return {
        "device_id": device_id,
        "count": len(alarms),
        "alarms": [
            {
                "id": a.id,
                "alarm_type": a.alarm_type,
                "alarm_type_name": a.alarm_type_name,
                "alarm_level": a.alarm_level,
                "latitude": a.latitude,
                "longitude": a.longitude,
                "speed": a.speed,
                "alarm_time": a.alarm_time.isoformat() if a.alarm_time else None,
                "is_read": a.is_read,
                "is_acknowledged": a.is_acknowledged,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in alarms
        ]
    }


@router.post("/device/{device_id}/alarms/{alarm_id}/acknowledge")
async def acknowledge_alarm(
    device_id: str,
    alarm_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark an alarm as acknowledged.
    """
    alarm = db.query(AlarmDB).filter(
        AlarmDB.id == alarm_id,
        AlarmDB.device_id == device_id
    ).first()
    
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    alarm.is_read = True
    alarm.is_acknowledged = True
    alarm.acknowledged_at = datetime.utcnow()
    db.commit()
    
    return {"status": "acknowledged", "alarm_id": alarm_id}


@router.get("/stats")
async def get_forwarding_stats(db: Session = Depends(get_db)):
    """
    Get statistics about cached data.
    Useful for monitoring the data forwarding system.
    """
    total_devices = db.query(DeviceCacheDB).count()
    online_devices = db.query(DeviceCacheDB).filter(DeviceCacheDB.is_online == True).count()
    acc_on_devices = db.query(DeviceCacheDB).filter(DeviceCacheDB.acc_status == True).count()
    
    total_alarms = db.query(AlarmDB).count()
    unread_alarms = db.query(AlarmDB).filter(AlarmDB.is_read == False).count()
    
    # Get most recent update
    latest_update = db.query(DeviceCacheDB).order_by(
        DeviceCacheDB.updated_at.desc()
    ).first()
    
    return {
        "devices": {
            "total": total_devices,
            "online": online_devices,
            "acc_on": acc_on_devices
        },
        "alarms": {
            "total": total_alarms,
            "unread": unread_alarms
        },
        "latest_update": latest_update.updated_at.isoformat() if latest_update and latest_update.updated_at else None
    }

