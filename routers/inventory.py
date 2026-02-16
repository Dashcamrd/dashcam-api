"""
Inventory Router — Products, worker inventory, consignment
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import SessionLocal
from models.inventory_db import ProductDB, WorkerInventoryDB, InventoryTransactionDB
from models.user_db import UserDB
from models.fcm_token_db import FCMTokenDB
from services.notification_service import NotificationService
from services.auth_service import get_current_user
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ════════════════════════════════════════════════════════════
#  Pydantic schemas
# ════════════════════════════════════════════════════════════

class ProductCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    description: Optional[str] = None
    low_stock_threshold: Optional[int] = 3


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    low_stock_threshold: Optional[int] = None


class ConsignmentRequest(BaseModel):
    worker_id: int
    product_id: int
    quantity: int           # positive number to add
    notes: Optional[str] = None


class AdjustmentRequest(BaseModel):
    worker_id: int
    product_id: int
    new_quantity: int       # set exact amount
    notes: Optional[str] = None


# ════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_admin(current_user: dict):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")


# ════════════════════════════════════════════════════════════
#  PRODUCTS — CRUD (admin)
# ════════════════════════════════════════════════════════════

@router.post("/products")
def create_product(
    req: ProductCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _require_admin(current_user)

    existing = db.query(ProductDB).filter(ProductDB.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this name already exists")

    product = ProductDB(
        name=req.name,
        sku=req.sku,
        description=req.description,
        low_stock_threshold=req.low_stock_threshold or 3,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return {
        "success": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "description": product.description,
            "low_stock_threshold": product.low_stock_threshold,
        },
    }


@router.get("/products")
def list_products(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """List all products (admin + worker)."""
    products = db.query(ProductDB).order_by(ProductDB.name).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "description": p.description,
            "low_stock_threshold": p.low_stock_threshold,
        }
        for p in products
    ]


@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    req: ProductUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _require_admin(current_user)

    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if req.name is not None:
        product.name = req.name
    if req.sku is not None:
        product.sku = req.sku
    if req.description is not None:
        product.description = req.description
    if req.low_stock_threshold is not None:
        product.low_stock_threshold = req.low_stock_threshold

    db.commit()
    return {"success": True}


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _require_admin(current_user)

    product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"success": True}


# ════════════════════════════════════════════════════════════
#  CONSIGNMENT — admin sends inventory to worker
# ════════════════════════════════════════════════════════════

@router.post("/consign")
def consign_inventory(
    req: ConsignmentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Admin sends N units of a product to a worker."""
    _require_admin(current_user)

    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    worker = db.query(UserDB).filter(UserDB.id == req.worker_id, UserDB.role == "worker").first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    product = db.query(ProductDB).filter(ProductDB.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Upsert worker_inventory
    inv = db.query(WorkerInventoryDB).filter(
        WorkerInventoryDB.worker_id == req.worker_id,
        WorkerInventoryDB.product_id == req.product_id,
    ).first()

    if inv:
        inv.quantity += req.quantity
        inv.updated_at = datetime.utcnow()
    else:
        inv = WorkerInventoryDB(
            worker_id=req.worker_id,
            product_id=req.product_id,
            quantity=req.quantity,
        )
        db.add(inv)

    # Audit log
    txn = InventoryTransactionDB(
        worker_id=req.worker_id,
        product_id=req.product_id,
        quantity_change=req.quantity,
        reason="consignment",
        notes=req.notes,
        created_by=current_user["user_id"],
    )
    db.add(txn)
    db.commit()

    # Notify worker
    try:
        tokens = db.query(FCMTokenDB).filter(
            FCMTokenDB.user_id == req.worker_id,
            FCMTokenDB.is_active == True,
        ).all()
        for t in tokens:
            NotificationService.send_notification(
                token=t.fcm_token,
                title="📦 مخزون جديد!",
                body=f"تم إضافة {req.quantity} × {product.name} إلى مخزونك",
                data={"type": "inventory_update", "product_id": str(product.id)},
            )
    except Exception as e:
        logger.warning(f"⚠️ Consignment notification failed: {e}")

    return {
        "success": True,
        "worker_id": req.worker_id,
        "product_id": req.product_id,
        "new_quantity": inv.quantity,
    }


# ════════════════════════════════════════════════════════════
#  ADJUSTMENT — admin fixes inventory count
# ════════════════════════════════════════════════════════════

@router.post("/adjust")
def adjust_inventory(
    req: AdjustmentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Admin sets exact quantity (correction)."""
    _require_admin(current_user)

    inv = db.query(WorkerInventoryDB).filter(
        WorkerInventoryDB.worker_id == req.worker_id,
        WorkerInventoryDB.product_id == req.product_id,
    ).first()

    old_qty = inv.quantity if inv else 0
    diff = req.new_quantity - old_qty

    if inv:
        inv.quantity = req.new_quantity
        inv.updated_at = datetime.utcnow()
    else:
        inv = WorkerInventoryDB(
            worker_id=req.worker_id,
            product_id=req.product_id,
            quantity=req.new_quantity,
        )
        db.add(inv)

    txn = InventoryTransactionDB(
        worker_id=req.worker_id,
        product_id=req.product_id,
        quantity_change=diff,
        reason="adjustment",
        notes=req.notes,
        created_by=current_user["user_id"],
    )
    db.add(txn)
    db.commit()

    return {
        "success": True,
        "old_quantity": old_qty,
        "new_quantity": req.new_quantity,
    }


# ════════════════════════════════════════════════════════════
#  WORKER — my inventory
# ════════════════════════════════════════════════════════════

@router.get("/my")
def my_inventory(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Get current worker's inventory."""
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user or user.role != "worker":
        raise HTTPException(status_code=403, detail="Workers only")

    rows = (
        db.query(WorkerInventoryDB, ProductDB)
        .join(ProductDB, WorkerInventoryDB.product_id == ProductDB.id)
        .filter(WorkerInventoryDB.worker_id == user.id)
        .all()
    )

    return [
        {
            "product_id": product.id,
            "product_name": product.name,
            "product_sku": product.sku,
            "quantity": inv.quantity,
            "low_stock_threshold": product.low_stock_threshold,
            "is_low": inv.quantity <= product.low_stock_threshold,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        }
        for inv, product in rows
    ]


# ════════════════════════════════════════════════════════════
#  ADMIN — view any worker's inventory
# ════════════════════════════════════════════════════════════

@router.get("/worker/{worker_id}")
def worker_inventory(
    worker_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """View a specific worker's inventory (admin only)."""
    _require_admin(current_user)

    worker = db.query(UserDB).filter(UserDB.id == worker_id, UserDB.role == "worker").first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    rows = (
        db.query(WorkerInventoryDB, ProductDB)
        .join(ProductDB, WorkerInventoryDB.product_id == ProductDB.id)
        .filter(WorkerInventoryDB.worker_id == worker_id)
        .all()
    )

    return {
        "worker": {"id": worker.id, "name": worker.name, "city": worker.city},
        "inventory": [
            {
                "product_id": product.id,
                "product_name": product.name,
                "product_sku": product.sku,
                "quantity": inv.quantity,
                "low_stock_threshold": product.low_stock_threshold,
                "is_low": inv.quantity <= product.low_stock_threshold,
            }
            for inv, product in rows
        ],
    }


# ════════════════════════════════════════════════════════════
#  ADMIN — all workers inventory overview
# ════════════════════════════════════════════════════════════

@router.get("/overview")
def inventory_overview(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Overview of all workers' inventory (admin)."""
    _require_admin(current_user)

    workers = db.query(UserDB).filter(UserDB.role == "worker").all()
    result = []

    for w in workers:
        rows = (
            db.query(WorkerInventoryDB, ProductDB)
            .join(ProductDB, WorkerInventoryDB.product_id == ProductDB.id)
            .filter(WorkerInventoryDB.worker_id == w.id)
            .all()
        )
        result.append({
            "worker": {"id": w.id, "name": w.name, "city": w.city},
            "inventory": [
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": inv.quantity,
                    "is_low": inv.quantity <= product.low_stock_threshold,
                }
                for inv, product in rows
            ],
        })

    return result


# ════════════════════════════════════════════════════════════
#  Transaction history
# ════════════════════════════════════════════════════════════

@router.get("/transactions")
def list_transactions(
    worker_id: Optional[int] = None,
    product_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """View inventory transaction history (admin only)."""
    _require_admin(current_user)

    q = db.query(InventoryTransactionDB)
    if worker_id:
        q = q.filter(InventoryTransactionDB.worker_id == worker_id)
    if product_id:
        q = q.filter(InventoryTransactionDB.product_id == product_id)

    txns = q.order_by(InventoryTransactionDB.created_at.desc()).limit(limit).all()

    return [
        {
            "id": t.id,
            "worker_id": t.worker_id,
            "product_id": t.product_id,
            "quantity_change": t.quantity_change,
            "reason": t.reason,
            "order_id": t.order_id,
            "notes": t.notes,
            "created_by": t.created_by,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns
    ]

