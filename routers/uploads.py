"""
Uploads Router — Cloudinary photo upload for order completion photos
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.auth_service import get_current_user
from typing import Optional
import cloudinary
import cloudinary.uploader
import logging
import os
import base64

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["Uploads"])

# ════════════════════════════════════════════════════════════
#  Configure Cloudinary
# ════════════════════════════════════════════════════════════

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dkhf8b9oj"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "665622679134625"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "UtFDJHPjS85NCdYkiTcxN264X40"),
    secure=True,
)


# ════════════════════════════════════════════════════════════
#  Pydantic schemas
# ════════════════════════════════════════════════════════════

class UploadPhotoRequest(BaseModel):
    image_base64: str          # Base64 encoded image data
    order_id: int              # Which order this photo belongs to
    photo_type: Optional[str] = None  # before / after / receipt
    filename: Optional[str] = None    # Original filename


# ════════════════════════════════════════════════════════════
#  Upload photo to Cloudinary
# ════════════════════════════════════════════════════════════

@router.post("/photo")
def upload_photo(
    req: UploadPhotoRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Upload an order completion photo to Cloudinary.
    Returns the secure URL for the uploaded image.
    """
    try:
        # Build the data URI for Cloudinary upload
        # Try to detect image type from base64 or filename
        ext = "jpg"
        if req.filename:
            lower_name = req.filename.lower()
            if lower_name.endswith(".png"):
                ext = "png"
            elif lower_name.endswith(".heic") or lower_name.endswith(".heif"):
                ext = "heic"
            elif lower_name.endswith(".webp"):
                ext = "webp"

        data_uri = f"data:image/{ext};base64,{req.image_base64}"

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            data_uri,
            folder=f"dashcam_orders/order_{req.order_id}",
            public_id=f"{req.photo_type or 'photo'}_{current_user['user_id']}_{int(__import__('time').time())}",
            resource_type="image",
            transformation=[
                {"quality": "auto:good", "fetch_format": "auto"},
            ],
        )

        secure_url = result.get("secure_url", "")
        logger.info(f"✅ Photo uploaded to Cloudinary: {secure_url} (order={req.order_id})")

        return {
            "success": True,
            "url": secure_url,
            "public_id": result.get("public_id", ""),
            "width": result.get("width"),
            "height": result.get("height"),
        }

    except Exception as e:
        logger.error(f"❌ Cloudinary upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")

