"""
Worker Authentication Router
- Workers login with phone number + password
- Admin creates worker accounts
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user_db import UserDB
from services.auth_service import (
    get_current_user, hash_password, verify_password, create_access_token,
)
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/worker-auth", tags=["Worker Auth"])


# ════════════════════════════════════════════════════════════
#  Pydantic schemas
# ════════════════════════════════════════════════════════════

class WorkerLoginRequest(BaseModel):
    phone: str
    password: str


class CreateWorkerRequest(BaseModel):
    name: str
    phone: str
    password: str
    city: Optional[str] = None


class UpdateWorkerRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    password: Optional[str] = None


# ════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  Worker login
# ════════════════════════════════════════════════════════════

@router.post("/login")
def worker_login(req: WorkerLoginRequest, db: Session = Depends(_get_db)):
    """
    Worker login with phone number + password.
    Returns JWT token that works with all /orders and /inventory endpoints.
    """
    worker = db.query(UserDB).filter(
        UserDB.phone == req.phone,
        UserDB.role == "worker",
    ).first()

    if not worker or not verify_password(req.password, worker.password_hash):
        raise HTTPException(status_code=401, detail="رقم الجوال أو كلمة المرور غير صحيحة")

    token = create_access_token({
        "sub": worker.invoice_no,
        "user_id": worker.id,
        "name": worker.name,
        "is_admin": worker.is_admin,
        "role": "worker",
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": worker.id,
            "name": worker.name,
            "phone": worker.phone,
            "city": worker.city,
            "role": "worker",
        },
    }


# ════════════════════════════════════════════════════════════
#  Admin — create worker account
# ════════════════════════════════════════════════════════════

@router.post("/create")
def create_worker(
    req: CreateWorkerRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Admin creates a worker account."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    # Check phone uniqueness
    existing = db.query(UserDB).filter(UserDB.phone == req.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="رقم الجوال مستخدم مسبقاً")

    # Generate a unique invoice_no for the worker (workers don't need invoice, but DB requires it)
    import uuid
    invoice_no = f"WRK-{uuid.uuid4().hex[:8].upper()}"

    worker = UserDB(
        invoice_no=invoice_no,
        password_hash=hash_password(req.password),
        name=req.name,
        phone=req.phone,
        role="worker",
        city=req.city,
        is_admin=False,
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)

    logger.info(f"✅ Worker created: {worker.name} (phone: {worker.phone}, city: {worker.city})")

    return {
        "success": True,
        "worker": {
            "id": worker.id,
            "name": worker.name,
            "phone": worker.phone,
            "city": worker.city,
            "role": "worker",
        },
    }


# ════════════════════════════════════════════════════════════
#  Admin — update worker
# ════════════════════════════════════════════════════════════

@router.put("/workers/{worker_id}")
def update_worker(
    worker_id: int,
    req: UpdateWorkerRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Admin updates a worker's details."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    worker = db.query(UserDB).filter(UserDB.id == worker_id, UserDB.role == "worker").first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if req.name is not None:
        worker.name = req.name
    if req.phone is not None:
        worker.phone = req.phone
    if req.city is not None:
        worker.city = req.city
    if req.password is not None:
        worker.password_hash = hash_password(req.password)

    db.commit()

    return {
        "success": True,
        "worker": {
            "id": worker.id,
            "name": worker.name,
            "phone": worker.phone,
            "city": worker.city,
        },
    }


# ════════════════════════════════════════════════════════════
#  Admin — delete worker
# ════════════════════════════════════════════════════════════

@router.delete("/workers/{worker_id}")
def delete_worker(
    worker_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Admin deletes a worker account."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    worker = db.query(UserDB).filter(UserDB.id == worker_id, UserDB.role == "worker").first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    db.delete(worker)
    db.commit()

    return {"success": True, "message": f"Worker '{worker.name}' deleted"}

