from fastapi import HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.device_db import DeviceDB
from models.device import Device

def register_device(device: Device, current_user: str) -> Device:
    db: Session = SessionLocal()
    existing = db.query(DeviceDB).filter(DeviceDB.id == device.id, DeviceDB.owner_username == current_user).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Device ID already exists for this user")

    db_device = DeviceDB(**device.dict(), owner_username=current_user)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    db.close()
    return device

def list_devices(current_user: str) -> list[Device]:
    db: Session = SessionLocal()
    devices = db.query(DeviceDB).filter(DeviceDB.owner_username == current_user).all()
    db.close()
    return [Device(**d.__dict__) for d in devices]

