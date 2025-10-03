from typing import Optional
from pydantic import BaseModel

class Device(BaseModel):
    id: str
    brand: str
    model: str
    firmware_version: Optional[str] = None
