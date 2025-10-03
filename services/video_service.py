from fastapi import HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.video_db import VideoDB
from models.device_db import DeviceDB
from models.video import Video
import os

UPLOAD_DIR = "uploads/videos"

def get_video_file_path(video_id: str, current_user: str) -> str:
    """
    Get the file path for a video owned by the current user.
    Ensures ownership before returning the file path.
    """
    db: Session = SessionLocal()
    video = db.query(VideoDB).filter(
        VideoDB.id == video_id, VideoDB.owner_username == current_user
    ).first()
    db.close()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found for this user")

    return os.path.join(UPLOAD_DIR, video.filename)

# Allowed video resolutions
ALLOWED_RESOLUTIONS = {"720p", "1080p", "1440p", "2160p"}


def register_video(video: Video, current_user: str) -> Video:
    """
    Register a video (metadata only, no file upload).
    """
    db: Session = SessionLocal()

    # Ensure video ID is unique per user
    existing = db.query(VideoDB).filter(
        VideoDB.id == video.id, VideoDB.owner_username == current_user
    ).first()
    if existing:
        db.close()
        raise HTTPException(
            status_code=400, detail="Video ID already exists for this user"
        )

    # Ensure device exists and belongs to the current user
    device = (
        db.query(DeviceDB)
        .filter(DeviceDB.id == video.device_id, DeviceDB.owner_username == current_user)
        .first()
    )
    if not device:
        db.close()
        raise HTTPException(status_code=404, detail="Device not found for this user")

    # Validate resolution
    if video.resolution and video.resolution not in ALLOWED_RESOLUTIONS:
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Resolution must be one of {ALLOWED_RESOLUTIONS}",
        )

    # Save video metadata
    db_video = VideoDB(**video.dict(), owner_username=current_user)
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    db.close()

    return video


def list_videos(current_user: str) -> list[Video]:
    """
    List all videos belonging to the current user.
    """
    db: Session = SessionLocal()
    videos = db.query(VideoDB).filter(VideoDB.owner_username == current_user).all()
    db.close()
    return [Video(**v.__dict__) for v in videos]


def save_uploaded_video(device_id: str, filename: str, current_user: str) -> dict:
    """
    Save metadata for an uploaded video file.
    The file itself is handled in the router; here we just register it in the DB.
    """
    db: Session = SessionLocal()

    # Ensure device exists and belongs to the current user
    device = (
        db.query(DeviceDB)
        .filter(DeviceDB.id == device_id, DeviceDB.owner_username == current_user)
        .first()
    )
    if not device:
        db.close()
        raise HTTPException(status_code=404, detail="Device not found for this user")

    # Generate a unique video ID based on device + filename
    video_id = f"{device_id}_{filename}"

    # Ensure it doesn't already exist
    existing = db.query(VideoDB).filter(
        VideoDB.id == video_id, VideoDB.owner_username == current_user
    ).first()
    if existing:
        db.close()
        raise HTTPException(
            status_code=400, detail="This video file is already registered"
        )

    # Save metadata in DB
    db_video = VideoDB(
        id=video_id,
        device_id=device_id,
        filename=filename,
        resolution=None,
        duration=None,
        owner_username=current_user,
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    db.close()

    return {
        "msg": "Upload successful",
        "video_id": video_id,
        "filename": filename,
    }
