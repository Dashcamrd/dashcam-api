"""
Push Notification Router

Endpoints for managing FCM tokens and notification preferences.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from database import SessionLocal
from models.fcm_token_db import FCMTokenDB, UserNotificationSettingsDB, NotificationPreference
from models.device_db import DeviceDB
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])
logger = logging.getLogger(__name__)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Request/Response Models
# =============================================================================

class RegisterTokenRequest(BaseModel):
    """Request to register an FCM token"""
    fcm_token: str = Field(..., min_length=10, description="Firebase Cloud Messaging token")
    device_type: Optional[str] = Field(None, description="Device type: ios, android, web")
    device_name: Optional[str] = Field(None, description="Human-readable device name")


class UpdateNotificationSettingsRequest(BaseModel):
    """Request to update notification settings for a device"""
    device_id: str = Field(..., description="Dashcam device ID")
    acc_notification: str = Field(
        default="both",
        description="ACC notification preference: none, on_only, off_only, both"
    )
    language: Optional[str] = Field(
        default="en",
        description="Notification language: en (English), ar (Arabic)"
    )


class NotificationSettingsResponse(BaseModel):
    """Response with notification settings"""
    device_id: str
    device_name: Optional[str]
    acc_notification: str
    language: str


class TokenResponse(BaseModel):
    """Response with token info"""
    id: int
    device_type: Optional[str]
    device_name: Optional[str]
    is_active: bool
    created_at: datetime


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/register-token")
def register_fcm_token(
    request: RegisterTokenRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register or update an FCM token for push notifications.
    
    Called by the mobile app on startup and when the FCM token is refreshed.
    Each device (phone/tablet) gets its own token.
    """
    user_id = current_user["user_id"]
    
    # Check if token already exists
    existing = db.query(FCMTokenDB).filter(
        FCMTokenDB.fcm_token == request.fcm_token
    ).first()
    
    if existing:
        # Update existing token
        existing.user_id = user_id  # Re-assign to current user (in case of re-login)
        existing.device_type = request.device_type
        existing.device_name = request.device_name
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Updated FCM token for user {user_id}")
        return {
            "success": True,
            "message": "Token updated successfully",
            "token_id": existing.id
        }
    
    # Create new token
    new_token = FCMTokenDB(
        user_id=user_id,
        fcm_token=request.fcm_token,
        device_type=request.device_type,
        device_name=request.device_name,
        is_active=True
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    
    logger.info(f"✅ Registered new FCM token for user {user_id}")
    return {
        "success": True,
        "message": "Token registered successfully",
        "token_id": new_token.id
    }


@router.delete("/unregister-token")
def unregister_fcm_token(
    fcm_token: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unregister an FCM token (e.g., on logout).
    """
    user_id = current_user["user_id"]
    
    token = db.query(FCMTokenDB).filter(
        FCMTokenDB.fcm_token == fcm_token,
        FCMTokenDB.user_id == user_id
    ).first()
    
    if token:
        token.is_active = False
        db.commit()
        logger.info(f"✅ Unregistered FCM token for user {user_id}")
        return {"success": True, "message": "Token unregistered"}
    
    return {"success": True, "message": "Token not found (already unregistered)"}


@router.get("/tokens", response_model=List[TokenResponse])
def get_user_tokens(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all registered FCM tokens for the current user.
    """
    tokens = db.query(FCMTokenDB).filter(
        FCMTokenDB.user_id == current_user["user_id"]
    ).all()
    
    return [
        TokenResponse(
            id=t.id,
            device_type=t.device_type,
            device_name=t.device_name,
            is_active=t.is_active,
            created_at=t.created_at
        )
        for t in tokens
    ]


@router.post("/settings")
def update_notification_settings(
    request: UpdateNotificationSettingsRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update notification settings for a specific device.
    
    Allows users to choose which notifications they want:
    - none: No ACC notifications
    - on_only: Only when ACC turns ON
    - off_only: Only when ACC turns OFF  
    - both: Both ON and OFF notifications
    """
    user_id = current_user["user_id"]
    
    # Validate acc_notification value
    valid_prefs = [e.value for e in NotificationPreference]
    if request.acc_notification not in valid_prefs:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid acc_notification. Must be one of: {valid_prefs}"
        )
    
    # Validate language
    valid_languages = ["en", "ar"]
    if request.language and request.language not in valid_languages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language. Must be one of: {valid_languages}"
        )
    
    # Check if setting exists
    existing = db.query(UserNotificationSettingsDB).filter(
        UserNotificationSettingsDB.user_id == user_id,
        UserNotificationSettingsDB.device_id == request.device_id
    ).first()
    
    if existing:
        existing.acc_notification = request.acc_notification
        existing.language = request.language or "en"
        existing.updated_at = datetime.utcnow()
    else:
        new_setting = UserNotificationSettingsDB(
            user_id=user_id,
            device_id=request.device_id,
            acc_notification=request.acc_notification,
            language=request.language or "en"
        )
        db.add(new_setting)
    
    db.commit()
    
    logger.info(f"✅ Updated notification settings for user {user_id}, device {request.device_id}")
    return {
        "success": True,
        "message": "Settings updated successfully",
        "device_id": request.device_id,
        "acc_notification": request.acc_notification,
        "language": request.language or "en"
    }


@router.get("/settings")
def get_notification_settings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get notification settings for all devices the user has configured.
    """
    user_id = current_user["user_id"]
    
    settings = db.query(UserNotificationSettingsDB).filter(
        UserNotificationSettingsDB.user_id == user_id
    ).all()
    
    result = []
    for s in settings:
        # Get device name
        device = db.query(DeviceDB).filter(DeviceDB.device_id == s.device_id).first()
        device_name = device.name if device else None
        
        result.append({
            "device_id": s.device_id,
            "device_name": device_name,
            "acc_notification": s.acc_notification,
            "language": s.language
        })
    
    return {
        "success": True,
        "settings": result
    }


@router.get("/settings/{device_id}")
def get_device_notification_settings(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get notification settings for a specific device.
    """
    user_id = current_user["user_id"]
    
    setting = db.query(UserNotificationSettingsDB).filter(
        UserNotificationSettingsDB.user_id == user_id,
        UserNotificationSettingsDB.device_id == device_id
    ).first()
    
    if not setting:
        # Return default settings
        return {
            "success": True,
            "device_id": device_id,
            "acc_notification": NotificationPreference.BOTH.value,
            "language": "en",
            "is_default": True
        }
    
    # Get device name
    device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
    
    return {
        "success": True,
        "device_id": device_id,
        "device_name": device.name if device else None,
        "acc_notification": setting.acc_notification,
        "language": setting.language,
        "is_default": False
    }


@router.delete("/settings/{device_id}")
def delete_device_notification_settings(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete notification settings for a specific device (reset to default).
    """
    user_id = current_user["user_id"]
    
    setting = db.query(UserNotificationSettingsDB).filter(
        UserNotificationSettingsDB.user_id == user_id,
        UserNotificationSettingsDB.device_id == device_id
    ).first()
    
    if setting:
        db.delete(setting)
        db.commit()
        return {"success": True, "message": "Settings deleted"}
    
    return {"success": True, "message": "No settings found (already default)"}


class UpdateLanguageRequest(BaseModel):
    """Request to update language for all notification settings"""
    language: str = Field(..., description="Language code: en or ar")


@router.put("/language")
def update_all_notification_language(
    request: UpdateLanguageRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the language for ALL notification settings of the current user.
    Called when user changes app language to keep notifications in sync.
    """
    user_id = current_user["user_id"]
    
    # Validate language
    valid_languages = ["en", "ar"]
    if request.language not in valid_languages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language. Must be one of: {valid_languages}"
        )
    
    # Update all settings for this user
    updated_count = db.query(UserNotificationSettingsDB).filter(
        UserNotificationSettingsDB.user_id == user_id
    ).update({"language": request.language, "updated_at": datetime.utcnow()})
    
    db.commit()
    
    logger.info(f"✅ Updated language to '{request.language}' for {updated_count} notification settings (user {user_id})")
    
    return {
        "success": True,
        "message": f"Language updated to '{request.language}' for all devices",
        "updated_count": updated_count
    }


@router.post("/migrate-existing-users")
def migrate_existing_users_notification_settings(
    db: Session = Depends(get_db)
):
    """
    One-time migration: Create notification settings for all existing user-device pairs.
    Sets acc_notification to 'none' (OFF) by default.
    
    This endpoint should be called once to populate settings for existing users
    who registered before notification settings were auto-created.
    """
    from models.device_db import DeviceDB
    
    # Find all devices with assigned users
    devices_with_users = db.query(DeviceDB).filter(
        DeviceDB.assigned_user_id.isnot(None)
    ).all()
    
    created_count = 0
    skipped_count = 0
    
    for device in devices_with_users:
        # Check if settings already exist
        existing = db.query(UserNotificationSettingsDB).filter(
            UserNotificationSettingsDB.user_id == device.assigned_user_id,
            UserNotificationSettingsDB.device_id == device.device_id
        ).first()
        
        if not existing:
            # Create default settings (OFF)
            new_setting = UserNotificationSettingsDB(
                user_id=device.assigned_user_id,
                device_id=device.device_id,
                acc_notification="none",  # OFF by default
                language="en"
            )
            db.add(new_setting)
            created_count += 1
        else:
            skipped_count += 1
    
    db.commit()
    
    logger.info(f"✅ Migration complete: Created {created_count} settings, skipped {skipped_count} existing")
    
    return {
        "success": True,
        "message": "Migration completed",
        "created": created_count,
        "skipped": skipped_count,
        "total_devices": len(devices_with_users)
    }

