from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    invoice_no: str
    password: str
    name: str
    email: Optional[str] = None

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
    new_password: str
