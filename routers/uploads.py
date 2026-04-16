"""
Uploads Router — Google Cloud Storage photo/video upload for order completion
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.auth_service import get_current_user
from typing import Optional
from google.cloud import storage
import logging
import os
import base64
import time
import io

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["Uploads"])

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "dashcamrd-media")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.dashcamrd.com")

_gcs_client = None
_gcs_bucket = None


def _get_bucket():
    global _gcs_client, _gcs_bucket
    if _gcs_bucket is None:
        _gcs_client = storage.Client()
        _gcs_bucket = _gcs_client.bucket(GCS_BUCKET_NAME)
    return _gcs_bucket


class UploadPhotoRequest(BaseModel):
    image_base64: str
    order_id: int
    photo_type: Optional[str] = None
    filename: Optional[str] = None


@router.post("/photo")
def upload_photo(
    req: UploadPhotoRequest,
    current_user: dict = Depends(get_current_user),
):
    """Upload an order completion photo to GCS. Returns the serving URL."""
    try:
        image_data = base64.b64decode(req.image_base64)

        timestamp = int(time.time())
        photo_type = req.photo_type or "photo"
        user_id = current_user["user_id"]
        blob_name = f"dashcam_orders/order_{req.order_id}/{photo_type}_{user_id}_{timestamp}.jpg"

        bucket = _get_bucket()
        blob = bucket.blob(blob_name)
        blob.upload_from_string(image_data, content_type="image/jpeg")

        serving_url = f"{API_BASE_URL}/uploads/media/{blob_name}"
        logger.info(f"Uploaded photo to GCS: {blob_name} (order={req.order_id})")

        return {
            "success": True,
            "url": serving_url,
            "public_id": blob_name,
            "width": None,
            "height": None,
        }

    except Exception as e:
        logger.error(f"GCS upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")


@router.get("/media/{file_path:path}")
async def serve_media(file_path: str):
    """Serve a file from GCS. Caches heavily since order photos are immutable."""
    try:
        bucket = _get_bucket()
        blob = bucket.blob(file_path)

        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found")

        content = blob.download_as_bytes()
        content_type = blob.content_type or "image/jpeg"

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve media {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve file")
