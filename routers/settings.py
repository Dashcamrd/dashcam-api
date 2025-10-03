from fastapi import APIRouter, Depends
from models.setting import Setting
import services.setting_service as setting_service
from services.auth_service import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.post("/{device_id}", response_model=Setting)
def update_settings(device_id: str, setting: Setting, current_user: str = Depends(get_current_user)):
    """
    Update settings for a device owned by the current user.
    - Resolution must be one of 720p, 1080p, 1440p, 2160p.
    - Sensitivity must be one of low, medium, high.
    """
    return setting_service.update_settings(device_id, setting, current_user)

@router.get("/{device_id}", response_model=Setting)
def get_settings(device_id: str, current_user: str = Depends(get_current_user)):
    """
    Get settings for a device owned by the current user.
    """
    return setting_service.get_settings(device_id, current_user)
