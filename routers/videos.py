import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import List

router = APIRouter(prefix="/videos", tags=["videos"])

UPLOAD_DIR = "uploads/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 📌 Upload video for a device
@router.post("/upload")
async def upload_video(device_id: str = Form(...), file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    filename = f"{device_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"filename": filename, "device_id": device_id}


# 📌 Download video by video_id
@router.get("/download/{video_id}")
def download_video(video_id: str):
    file_path = os.path.join(UPLOAD_DIR, video_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="video/mp4", filename=video_id)


# 📌 List videos belonging to a device
@router.get("/list/{device_id}", response_model=List[str])
def list_videos(device_id: str):
    if not os.path.exists(UPLOAD_DIR):
        return []

    videos = [
        f for f in os.listdir(UPLOAD_DIR)
        if f.startswith(device_id + "_")
    ]
    return videos
