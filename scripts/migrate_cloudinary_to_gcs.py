"""
One-time migration: Download all Cloudinary photos and upload to GCS.
Updates database URLs to point to the new API-served GCS path.

Run inside Docker: python scripts/migrate_cloudinary_to_gcs.py
"""
import os
import sys
import requests
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.order_db import OrderPhotoDB
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

GCS_BUCKET = os.getenv("GCS_BUCKET_NAME", "dashcamrd-media")
API_BASE = os.getenv("API_BASE_URL", "https://api.dashcamrd.com")


def migrate():
    db = SessionLocal()
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(GCS_BUCKET)

    photos = db.query(OrderPhotoDB).filter(
        OrderPhotoDB.photo_url.like("%cloudinary%")
    ).all()

    logger.info(f"Found {len(photos)} Cloudinary photos to migrate")

    success = 0
    failed = 0

    for photo in photos:
        try:
            # Extract GCS path from Cloudinary URL
            # e.g. .../dashcam_orders/order_759/before_1_1771590517.jpg
            url = photo.photo_url
            if "/dashcam_orders/" in url:
                path = "dashcam_orders/" + url.split("/dashcam_orders/")[1]
            else:
                # Fallback: use order_id and photo id
                ext = url.rsplit(".", 1)[-1] if "." in url else "jpg"
                path = f"dashcam_orders/order_{photo.order_id}/photo_{photo.id}.{ext}"

            # Download from Cloudinary
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"[{photo.id}] Download failed (HTTP {resp.status_code}): {url[:80]}")
                failed += 1
                continue

            content_type = resp.headers.get("content-type", "image/jpeg")

            # Upload to GCS
            blob = bucket.blob(path)
            blob.upload_from_string(resp.content, content_type=content_type)

            # Update database URL
            new_url = f"{API_BASE}/uploads/media/{path}"
            photo.photo_url = new_url
            db.commit()

            success += 1
            logger.info(f"[{photo.id}] Migrated: {path}")

            time.sleep(0.1)

        except Exception as e:
            logger.error(f"[{photo.id}] Error: {e}")
            db.rollback()
            failed += 1

    logger.info(f"Migration complete: {success} success, {failed} failed out of {len(photos)} total")
    db.close()


if __name__ == "__main__":
    migrate()
