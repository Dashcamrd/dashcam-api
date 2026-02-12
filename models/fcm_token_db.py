"""
FCM Token and Notification Preferences Model

Stores Firebase Cloud Messaging tokens for push notifications
and user notification preferences (ACC ON/OFF alerts).
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum, Float
from database import Base
from datetime import datetime
import enum


class NotificationPreference(str, enum.Enum):
    """User notification preference for ACC status changes"""
    NONE = "none"           # No notifications
    ON_ONLY = "on_only"     # Only when ACC turns ON
    OFF_ONLY = "off_only"   # Only when ACC turns OFF
    BOTH = "both"           # Both ON and OFF notifications


class FCMTokenDB(Base):
    """
    Stores FCM tokens for push notifications.
    Each user can have multiple devices (phone, tablet, etc.)
    """
    __tablename__ = "fcm_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # FCM Token (unique per device)
    fcm_token = Column(String(500), unique=True, nullable=False, index=True)
    
    # Device info (for managing multiple devices)
    device_type = Column(String(50), nullable=True)  # ios, android, web
    device_name = Column(String(200), nullable=True)  # "iPhone 15 Pro", etc.
    
    # Token status
    is_active = Column(Boolean, default=True)  # Set to False if token becomes invalid
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)  # Last time a notification was sent


class UserNotificationSettingsDB(Base):
    """
    User notification preferences for each device (dashcam).
    Allows users to enable/disable ACC notifications per device.
    """
    __tablename__ = "user_notification_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(100), nullable=False, index=True)  # Dashcam device ID
    
    # Notification preferences
    acc_notification = Column(
        String(20), 
        default=NotificationPreference.BOTH.value,
        nullable=False
    )  # none, on_only, off_only, both
    
    # User's preferred language for notifications
    language = Column(String(10), default="en")  # en, ar
    
    # Speed limit alert (km/h). NULL or 0 = disabled
    speed_limit = Column(Integer, nullable=True, default=None)
    
    # Cooldown tracking for speed alerts (avoid spamming)
    last_speed_alert_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one setting per user per device
    __table_args__ = (
        # UniqueConstraint('user_id', 'device_id', name='unique_user_device_setting'),
    )

