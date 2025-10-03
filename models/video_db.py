from sqlalchemy import Column, String, Integer, ForeignKey
from database import Base

class VideoDB(Base):
    __tablename__ = "videos"

    id = Column(String(50), primary_key=True, index=True)
    device_id = Column(String(50), ForeignKey("devices.id"))
    filename = Column(String(200))
    duration = Column(Integer, nullable=True)   # seconds
    resolution = Column(String(50), nullable=True) 
    owner_username = Column(String(50), ForeignKey("users.username"))

