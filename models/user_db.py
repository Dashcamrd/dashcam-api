from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float
from database import Base
from datetime import datetime

class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_no = Column(String(100), unique=True, index=True, nullable=False)
    device_id = Column(String(100), nullable=True)
    password_hash = Column(String(200), nullable=False)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    is_admin = Column(Boolean, default=False)
    role = Column(String(20), default="user")  # "user", "worker", "admin"
    city = Column(String(100), nullable=True)   # Worker's assigned city
    geofence_lat = Column(Float, nullable=True)       # Center latitude of service area
    geofence_lng = Column(Float, nullable=True)       # Center longitude of service area
    geofence_radius_km = Column(Float, nullable=True)  # Radius in km
    created_at = Column(DateTime, default=datetime.utcnow)
