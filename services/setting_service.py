from fastapi import HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.setting_db import SettingDB
from models.device_db import DeviceDB
from models.setting import Setting

ALLOWED_RESOLUTIONS = {"720p", "1080p", "1440p", "2160p"}
ALLOWED_SENSITIVITY = {"low", "medium", "high"}

def update_settings(device_id: str, setting: Setting, current_user: str) -> Setting:
    if device_id != setting.device_id:
        raise HTTPException(status_code=400, detail="Device ID mismatch")

    db: Session = SessionLocal()

    device = db.query(DeviceDB).filter(DeviceDB.id == device_id, DeviceDB.owner_username == current_user).first()
    if not device:
        db.close()
        raise HTTPException(status_code=404, detail="Device not found for this user")

    if setting.resolution and setting.resolution not in ALLOWED_RESOLUTIONS:
        db.close()
        raise HTTPException(status_code=400, detail=f"Resolution must be one of {ALLOWED_RESOLUTIONS}")

    if setting.sensitivity and setting.sensitivity not in ALLOWED_SENSITIVITY:
        db.close()
        raise HTTPException(status_code=400, detail=f"Sensitivity must be one of {ALLOWED_SENSITIVITY}")

    db_setting = db.query(SettingDB).filter(SettingDB.device_id == device_id, SettingDB.owner_username == current_user).first()
    if db_setting:
        db_setting.resolution = setting.resolution
        db_setting.loop_recording = setting.loop_recording
        db_setting.sensitivity = setting.sensitivity
    else:
        db_setting = SettingDB(**setting.dict(), owner_username=current_user)
        db.add(db_setting)

    db.commit()
    db.refresh(db_setting)
    db.close()
    return setting

def get_settings(device_id: str, current_user: str) -> Setting:
    db: Session = SessionLocal()
    db_setting = db.query(SettingDB).filter(SettingDB.device_id == device_id, SettingDB.owner_username == current_user).first()
    db.close()
    if db_setting:
        return Setting(**db_setting.__dict__)
    return Setting(device_id=device_id)
