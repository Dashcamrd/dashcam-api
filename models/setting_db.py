from sqlalchemy import Column, String, Boolean, ForeignKey
from database import Base

class SettingDB(Base):
    __tablename__ = "settings"

    device_id = Column(String(50), ForeignKey("devices.id"), primary_key=True)
    resolution = Column(String(50), default="1080p")
    loop_recording = Column(Boolean, default=True)
    sensitivity = Column(String(50), default="medium")  # low, medium, high
    owner_username = Column(String(50), ForeignKey("users.username"))
