from typing import Optional, Literal
from pydantic import BaseModel

class Video(BaseModel):
    id: str
    device_id: str
    filename: str
    duration: Optional[int] = None   # in seconds
    resolution: Optional[Literal["720p", "1080p", "1440p", "2160p"]] = None
