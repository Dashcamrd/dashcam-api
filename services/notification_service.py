"""
Push Notification Service

Handles sending push notifications via Firebase Cloud Messaging (FCM).
Supports ACC status change notifications with multi-language support.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from models.fcm_token_db import FCMTokenDB, UserNotificationSettingsDB, NotificationPreference
from models.device_db import DeviceDB

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
_firebase_initialized = False


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    
    Requires FIREBASE_CREDENTIALS_JSON environment variable containing
    the service account JSON as a string, OR FIREBASE_CREDENTIALS_PATH
    pointing to the JSON file.
    """
    global _firebase_initialized
    
    if _firebase_initialized:
        return True
    
    try:
        # Try environment variable with JSON content first
        creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if creds_json:
            creds_dict = json.loads(creds_json)
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("✅ Firebase initialized from FIREBASE_CREDENTIALS_JSON")
            return True
        
        # Try file path
        creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if creds_path and os.path.exists(creds_path):
            cred = credentials.Certificate(creds_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info(f"✅ Firebase initialized from file: {creds_path}")
            return True
        
        logger.warning("⚠️ Firebase credentials not configured. Push notifications disabled.")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firebase: {e}")
        return False


class NotificationService:
    """Service for sending push notifications."""
    
    # Notification messages in different languages
    MESSAGES = {
        "en": {
            "acc_on_title": "Vehicle Started 🚗",
            "acc_on_body": 'Your car "{device_name}" is ON now!',
            "acc_off_title": "Vehicle Stopped 🚗",
            "acc_off_body": 'Your car "{device_name}" is OFF now!',
        },
        "ar": {
            "acc_on_title": "السيارة شغالة 🚗",
            "acc_on_body": 'سيارتك "{device_name}" شغاله الآن!',
            "acc_off_title": "السيارة مطفية 🚗",
            "acc_off_body": 'سيارتك "{device_name}" مطفية الآن!',
        }
    }
    
    @staticmethod
    def get_message(language: str, acc_on: bool, device_name: str) -> Dict[str, str]:
        """
        Get notification message in the specified language.
        
        Args:
            language: Language code (en, ar)
            acc_on: True if ACC turned ON, False if turned OFF
            device_name: Device name to show in notification
            
        Returns:
            Dict with 'title' and 'body' keys
        """
        # Default to English if language not supported
        if language not in NotificationService.MESSAGES:
            language = "en"
        
        msgs = NotificationService.MESSAGES[language]
        
        if acc_on:
            return {
                "title": msgs["acc_on_title"],
                "body": msgs["acc_on_body"].format(device_name=device_name)
            }
        else:
            return {
                "title": msgs["acc_off_title"],
                "body": msgs["acc_off_body"].format(device_name=device_name)
            }
    
    @staticmethod
    def send_notification(
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send a push notification to a single device.
        
        Args:
            token: FCM token
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            True if successful, False otherwise
        """
        if not initialize_firebase():
            logger.warning("⚠️ Firebase not initialized, skipping notification")
            return False
        
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                        )
                    )
                ),
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        priority="high",
                    )
                )
            )
            
            response = messaging.send(message)
            logger.info(f"✅ Notification sent: {response}")
            return True
            
        except messaging.UnregisteredError:
            logger.warning(f"⚠️ Token unregistered: {token[:20]}...")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
            return False
    
    @staticmethod
    def send_acc_notification(
        db: Session,
        device_id: str,
        acc_on: bool,
        previous_acc_status: Optional[bool] = None
    ) -> int:
        """
        Send ACC status change notification to all users subscribed to this device.
        
        Args:
            db: Database session
            device_id: The dashcam device ID
            acc_on: Current ACC status (True = ON, False = OFF)
            previous_acc_status: Previous ACC status (to detect actual change)
            
        Returns:
            Number of notifications sent successfully
        """
        # Skip if no actual change
        if previous_acc_status is not None and previous_acc_status == acc_on:
            logger.debug(f"📝 ACC status unchanged for {device_id}, skipping notification")
            return 0
        
        # Get device name from DeviceDB
        device = db.query(DeviceDB).filter(DeviceDB.device_id == device_id).first()
        device_name = device.name if device else device_id
        
        # Find all users with notification settings for this device
        settings = db.query(UserNotificationSettingsDB).filter(
            UserNotificationSettingsDB.device_id == device_id
        ).all()
        
        if not settings:
            logger.debug(f"📝 No notification settings for device {device_id}")
            return 0
        
        sent_count = 0
        
        for setting in settings:
            # Check if user wants this type of notification
            pref = setting.acc_notification
            
            if pref == NotificationPreference.NONE.value:
                continue
            elif pref == NotificationPreference.ON_ONLY.value and not acc_on:
                continue
            elif pref == NotificationPreference.OFF_ONLY.value and acc_on:
                continue
            # BOTH: send for both ON and OFF
            
            # Get user's FCM tokens
            tokens = db.query(FCMTokenDB).filter(
                FCMTokenDB.user_id == setting.user_id,
                FCMTokenDB.is_active == True
            ).all()
            
            if not tokens:
                logger.debug(f"📝 No active FCM tokens for user {setting.user_id}")
                continue
            
            # Get message in user's preferred language
            msg = NotificationService.get_message(
                language=setting.language or "en",
                acc_on=acc_on,
                device_name=device_name
            )
            
            # Send to all user's devices
            for token_record in tokens:
                success = NotificationService.send_notification(
                    token=token_record.fcm_token,
                    title=msg["title"],
                    body=msg["body"],
                    data={
                        "type": "acc_change",
                        "device_id": device_id,
                        "acc_status": "on" if acc_on else "off",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                if success:
                    # Update last_used_at
                    token_record.last_used_at = datetime.utcnow()
                    sent_count += 1
                else:
                    # Mark token as inactive if unregistered
                    token_record.is_active = False
        
        db.commit()
        logger.info(f"📱 Sent {sent_count} ACC notifications for device {device_id} (ACC={'ON' if acc_on else 'OFF'})")
        return sent_count
    
    @staticmethod
    def send_multicast_notification(
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Send notification to multiple devices at once.
        
        Args:
            tokens: List of FCM tokens
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            Number of successful sends
        """
        if not initialize_firebase():
            return 0
        
        if not tokens:
            return 0
        
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                tokens=tokens,
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                        )
                    )
                ),
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        priority="high",
                    )
                )
            )
            
            response = messaging.send_each_for_multicast(message)
            logger.info(f"✅ Multicast: {response.success_count} success, {response.failure_count} failed")
            return response.success_count
            
        except Exception as e:
            logger.error(f"❌ Failed to send multicast: {e}")
            return 0

