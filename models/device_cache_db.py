from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from database import Base
from datetime import datetime


class DeviceCacheDB(Base):
    """
    Cached device data received from vendor data forwarding (webhooks).
    This table stores real-time device status pushed by the vendor,
    enabling fast queries without hitting the vendor API.
    """
    __tablename__ = "device_cache"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(100), unique=True, index=True, nullable=False)
    
    # GPS Data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)  # km/h
    direction = Column(Integer, nullable=True)  # 0-360 degrees
    altitude = Column(Float, nullable=True)
    
    # Location info
    address = Column(Text, nullable=True)  # Geocoded address
    
    # Device Status
    acc_status = Column(Boolean, default=False)  # ACC ON/OFF
    is_online = Column(Boolean, default=False)  # Device online status
    
    # Timestamps
    gps_time = Column(DateTime, nullable=True)  # GPS timestamp from device
    last_online_time = Column(DateTime, nullable=True)  # Last time device was online
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional data (JSON string for flexibility)
    extra_data = Column(Text, nullable=True)


class AlarmDB(Base):
    """
    Alarm records received from vendor data forwarding.
    Stores all alarm events for historical tracking and notifications.
    """
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(100), index=True, nullable=False)
    
    # Alarm info
    alarm_type = Column(Integer, nullable=False)  # Vendor alarm type code
    alarm_type_name = Column(String(100), nullable=True)  # Human-readable name
    alarm_level = Column(Integer, default=1)  # Severity: 1=info, 2=warning, 3=critical
    
    # Location at time of alarm
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    
    # Alarm details
    alarm_time = Column(DateTime, nullable=False)  # When alarm occurred
    alarm_data = Column(Text, nullable=True)  # Full alarm data as JSON
    
    # Processing status
    is_read = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, nullable=True)  # User ID who acknowledged
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

