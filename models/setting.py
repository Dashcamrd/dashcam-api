from typing import Optional, Literal
from pydantic import BaseModel

class Setting(BaseModel):
    device_id: str
    resolution: Optional[Literal["720p", "1080p", "1440p", "2160p"]] = "1080p"
    loop_recording: Optional[bool] = True
    sensitivity: Optional[Literal["low", "medium", "high"]] = "medium"
