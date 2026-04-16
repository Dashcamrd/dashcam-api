from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    invoice_no: str
    device_id: Optional[str] = None  # Single device (backward compatible)
    device_ids: Optional[List[str]] = None  # Multiple devices
    name: str
    email: Optional[str] = None
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

class UserLogin(BaseModel):
    invoice_no: str
    password: str

class UserResponse(BaseModel):
    id: int
    invoice_no: str
    name: str
    email: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    email: str

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ProfileResponse(BaseModel):
    invoice_no: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    
    class Config:
        from_attributes = True
