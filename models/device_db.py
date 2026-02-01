from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean
from database import Base
from datetime import datetime

class DeviceDB(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(100), unique=True, index=True, nullable=False)  # from manufacturer
    name = Column(String(200), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    org_id = Column(String(100), nullable=False)  # from manufacturer
    status = Column(String(50), default="offline")  # online/offline
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Auto-configuration tracking fields
    configured = Column(String(10), default="no")  # "yes" or "no"
    config_last_attempt = Column(DateTime, nullable=True)  # Last configuration attempt timestamp
    config_attempts = Column(Integer, default=0)  # Number of configuration attempts
    last_online_at = Column(DateTime, nullable=True)  # When device came online (for 3-min delay)
