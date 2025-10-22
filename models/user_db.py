from sqlalchemy import Column, String, Integer, DateTime
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
    created_at = Column(DateTime, default=datetime.utcnow)
