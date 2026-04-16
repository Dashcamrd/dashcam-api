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

from database import engine
from google.cloud import storage
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

GCS_BUCKET = os.getenv("GCS_BUCKET_NAME", "dashcamrd-media")
API_BASE = os.getenv("API_BASE_URL", "https://api.dashcamrd.com")


def migrate():
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(GCS_BUCKET)

    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, order_id, photo_url FROM order_photos WHERE photo_url LIKE '%cloudinary%'"
        )).fetchall()

        logger.info(f"Found {len(rows)} Cloudinary photos to migrate")

        success = 0
        failed = 0

        for row in rows:
            photo_id, order_id, url = row[0], row[1], row[2]
            try:
                if "/dashcam_orders/" in url:
                    path = "dashcam_orders/" + url.split("/dashcam_orders/")[1]
                else:
                    ext = url.rsplit(".", 1)[-1] if "." in url else "jpg"
                    path = f"dashcam_orders/order_{order_id}/photo_{photo_id}.{ext}"

                resp = requests.get(url, timeout=30)
                if resp.status_code != 200:
                    logger.warning(f"[{photo_id}] Download failed (HTTP {resp.status_code}): {url[:80]}")
                    failed += 1
                    continue

                content_type = resp.headers.get("content-type", "image/jpeg")

                blob = bucket.blob(path)
                blob.upload_from_string(resp.content, content_type=content_type)

                new_url = f"{API_BASE}/uploads/media/{path}"
                conn.execute(
                    text("UPDATE order_photos SET photo_url = :new_url WHERE id = :id"),
                    {"new_url": new_url, "id": photo_id}
                )
                conn.commit()

                success += 1
                logger.info(f"[{photo_id}] Migrated: {path}")

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"[{photo_id}] Error: {e}")
                failed += 1

        logger.info(f"Migration complete: {success} success, {failed} failed out of {len(rows)} total")


if __name__ == "__main__":
    migrate()
