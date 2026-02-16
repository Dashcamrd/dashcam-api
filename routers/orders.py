"""
Orders Router — Rekaz webhook + full order CRUD for workers & admin
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from database import SessionLocal
from models.order_db import OrderDB, OrderPhotoDB
from models.inventory_db import WorkerInventoryDB, InventoryTransactionDB, ProductDB
from models.user_db import UserDB
from models.fcm_token_db import FCMTokenDB
from services.notification_service import NotificationService
from services.auth_service import get_current_user
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])


# ════════════════════════════════════════════════════════════
#  Pydantic schemas
# ════════════════════════════════════════════════════════════

class ManualOrderRequest(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    district_name: Optional[str] = None
    city: Optional[str] = "الرياض"
    full_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    number_of_cars: Optional[int] = 1
    dashcam_type: str = "RASD 1.0"
    service_type: Optional[str] = "delivery_and_install"
    notes: Optional[str] = None
    admin_notes: Optional[str] = None
    payment_status: Optional[str] = None
    total_amount: Optional[float] = None
    assigned_worker_id: Optional[int] = None


class AssignOrderRequest(BaseModel):
    worker_id: int


class UpdateStatusRequest(BaseModel):
    status: str                        # new / contacted / completed
    worker_notes: Optional[str] = None


class AddPhotoRequest(BaseModel):
    photo_url: str
    photo_type: Optional[str] = None   # before / after / receipt


# ════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _order_to_dict(order: OrderDB, db: Session) -> dict:
    """Convert OrderDB row to JSON-serialisable dict."""
    # Get photos
    photos = db.query(OrderPhotoDB).filter(OrderPhotoDB.order_id == order.id).all()

    # Get worker name
    worker_name = None
    if order.assigned_worker_id:
        worker = db.query(UserDB).filter(UserDB.id == order.assigned_worker_id).first()
        if worker:
            worker_name = worker.name

    return {
        "id": order.id,
        "rekaz_order_id": order.rekaz_order_id,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "customer_email": order.customer_email,
        "district_name": order.district_name,
        "city": order.city,
        "full_address": order.full_address,
        "latitude": order.latitude,
        "longitude": order.longitude,
        "number_of_cars": order.number_of_cars,
        "dashcam_type": order.dashcam_type,
        "product_sku": order.product_sku,
        "service_type": order.service_type,
        "assigned_worker_id": order.assigned_worker_id,
        "assigned_worker_name": worker_name,
        "status": order.status,
        "notes": order.notes,
        "admin_notes": order.admin_notes,
        "worker_notes": order.worker_notes,
        "payment_status": order.payment_status,
        "total_amount": order.total_amount,
        "discount": order.discount,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "assigned_at": order.assigned_at.isoformat() if order.assigned_at else None,
        "started_at": order.started_at.isoformat() if order.started_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "photos": [
            {
                "id": p.id,
                "photo_url": p.photo_url,
                "photo_type": p.photo_type,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in photos
        ],
    }


def _notify_workers_new_order(order: OrderDB, db: Session):
    """Send push notification about new order."""
    try:
        # If order is assigned to a specific worker, notify only that worker
        if order.assigned_worker_id:
            worker_ids = [order.assigned_worker_id]
        else:
            # Notify all workers
            workers = db.query(UserDB).filter(UserDB.role == "worker").all()
            worker_ids = [w.id for w in workers]

        if not worker_ids:
            return

        tokens = db.query(FCMTokenDB).filter(
            FCMTokenDB.user_id.in_(worker_ids),
            FCMTokenDB.is_active == True,
        ).all()

        title = f"طلب جديد! #{order.id}"
        body = f"{order.customer_name} - {order.district_name or order.city}\n{order.number_of_cars} × {order.dashcam_type}"

        for t in tokens:
            result = NotificationService.send_notification(
                token=t.fcm_token,
                title=title,
                body=body,
                data={"type": "new_order", "order_id": str(order.id)},
            )
            if result is True:
                t.last_used_at = datetime.utcnow()
            elif result is False:
                t.is_active = False

        db.commit()
        logger.info(f"📲 Notified {len(tokens)} worker devices about order #{order.id}")
    except Exception as e:
        logger.error(f"⚠️ Worker notification failed: {e}")


def _notify_admin_low_stock(worker: UserDB, product: ProductDB, qty: int, db: Session):
    """Send push notification to all admins about low stock."""
    try:
        admins = db.query(UserDB).filter(
            (UserDB.is_admin == True) | (UserDB.role == "admin")
        ).all()
        admin_ids = [a.id for a in admins]
        if not admin_ids:
            return

        tokens = db.query(FCMTokenDB).filter(
            FCMTokenDB.user_id.in_(admin_ids),
            FCMTokenDB.is_active == True,
        ).all()

        title = "⚠️ مخزون منخفض"
        body = f"{worker.name} لديه فقط {qty} قطعة من {product.name}، يحتاج تزويد!"

        for t in tokens:
            result = NotificationService.send_notification(
                token=t.fcm_token,
                title=title,
                body=body,
                data={"type": "low_stock", "worker_id": str(worker.id), "product_id": str(product.id)},
            )
            if result is True:
                t.last_used_at = datetime.utcnow()
            elif result is False:
                t.is_active = False

        db.commit()
        logger.info(f"📲 Notified admins about low stock: {worker.name} / {product.name}")
    except Exception as e:
        logger.error(f"⚠️ Low-stock notification failed: {e}")


def _deduct_inventory(order: OrderDB, db: Session):
    """
    Deduct inventory from the assigned worker when order is completed.
    Matches order.dashcam_type → product.name and deducts order.number_of_cars.
    """
    if not order.assigned_worker_id:
        return

    product = db.query(ProductDB).filter(
        (ProductDB.name == order.dashcam_type) | (ProductDB.sku == order.product_sku)
    ).first()
    if not product:
        logger.warning(f"⚠️ Product not found for deduction: {order.dashcam_type}")
        return

    inv = db.query(WorkerInventoryDB).filter(
        WorkerInventoryDB.worker_id == order.assigned_worker_id,
        WorkerInventoryDB.product_id == product.id,
    ).first()

    if inv:
        inv.quantity = max(0, inv.quantity - order.number_of_cars)
        inv.updated_at = datetime.utcnow()
    else:
        inv = WorkerInventoryDB(
            worker_id=order.assigned_worker_id,
            product_id=product.id,
            quantity=0,
        )
        db.add(inv)

    # Create transaction
    txn = InventoryTransactionDB(
        worker_id=order.assigned_worker_id,
        product_id=product.id,
        quantity_change=-order.number_of_cars,
        reason="order_completed",
        order_id=order.id,
    )
    db.add(txn)
    db.commit()

    # Check low-stock threshold
    if inv.quantity <= product.low_stock_threshold:
        worker = db.query(UserDB).filter(UserDB.id == order.assigned_worker_id).first()
        if worker:
            _notify_admin_low_stock(worker, product, inv.quantity, db)


def _geocode_district(district: str, city: str = "الرياض") -> tuple:
    """
    Forward-geocode a district name to (lat, lng).
    Uses the Nominatim free API (same as geocoding_service).
    Returns (None, None) on failure.
    """
    import requests as _requests
    try:
        query = f"{district}, {city}, Saudi Arabia"
        resp = _requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "RoadApp/1.0"},
            timeout=5,
        )
        if resp.status_code == 200 and resp.json():
            hit = resp.json()[0]
            return float(hit["lat"]), float(hit["lon"])
    except Exception as e:
        logger.warning(f"⚠️ Geocode failed for '{district}': {e}")
    return None, None


# ════════════════════════════════════════════════════════════
#  REKAZ WEBHOOK — auto-receive orders
# ════════════════════════════════════════════════════════════

@router.post("/webhook/rekaz")
async def rekaz_webhook(request: Request):
    """
    Receive order from Rekaz webhook.
    URL: https://dashcam-api.onrender.com/orders/webhook/rekaz
    """
    db = SessionLocal()
    try:
        payload = await request.json()

        event_name = payload.get("EventName", "")
        logger.info(f"📦 Rekaz webhook: {event_name}")
        logger.info(f"📦 Payload: {json.dumps(payload, ensure_ascii=False)[:1000]}")

        # Only process reservation created / confirmed
        if event_name not in ("ReservationCreatedEvent", "ReservationConfirmedEvent"):
            return {"status": "ignored", "event": event_name}

        data = payload.get("Data", {})
        customer = data.get("customer", {}) or data.get("Customer", {})
        custom_fields = data.get("CustomFields", []) or data.get("customFields", []) or []

        # Parse custom fields into a dict
        cf = {}
        for field in custom_fields:
            label = field.get("Label", "") or field.get("label", "")
            value = field.get("Value", "") or field.get("value", "")
            if isinstance(value, dict):
                value = value.get("Selected", str(value))
            cf[label] = value

        # Rekaz reference
        rekaz_number = str(data.get("number") or data.get("Number") or payload.get("Id", ""))

        # Duplicate check
        existing = db.query(OrderDB).filter(OrderDB.rekaz_order_id == rekaz_number).first()
        if existing:
            logger.info(f"⚠️ Duplicate Rekaz order {rekaz_number}")
            return {"status": "duplicate", "order_id": existing.id}

        # Map fields
        district = (
            cf.get("حي", "") or cf.get("الحي", "") or
            cf.get("District", "") or cf.get("Location Details", "") or ""
        )
        num_cars_str = cf.get("عدد السيارات", "") or cf.get("Number of Cars", "") or "1"
        try:
            num_cars = int(num_cars_str)
        except (ValueError, TypeError):
            num_cars = 1

        service_type_raw = cf.get("نوع الخدمة", "") or cf.get("Service Type", "")
        service_type = "install_only" if ("تركيب فقط" in service_type_raw or "install only" in service_type_raw.lower()) else "delivery_and_install"

        notes = cf.get("ملاحظات", "") or cf.get("Notes", "") or ""
        product_name = data.get("productName") or data.get("ProductName") or "RASD 1.0"
        sku = data.get("Sku") or data.get("sku") or ""
        branch = data.get("BranchName") or data.get("branchName") or "الرياض"

        # Geocode district
        lat, lng = None, None
        if district:
            lat, lng = _geocode_district(district, branch)

        order = OrderDB(
            rekaz_order_id=rekaz_number,
            rekaz_reservation_id=str(payload.get("Id", "")),
            customer_name=customer.get("Name") or customer.get("name") or "Unknown",
            customer_phone=customer.get("MobileNumber") or customer.get("phone") or "",
            customer_email=customer.get("Email") or customer.get("email"),
            district_name=district,
            city=branch,
            latitude=lat,
            longitude=lng,
            number_of_cars=num_cars,
            dashcam_type=product_name,
            product_sku=sku,
            service_type=service_type,
            status="new",
            notes=notes,
            payment_status=data.get("status") or data.get("Status"),
            total_amount=data.get("price") or data.get("Price") or 0,
            discount=data.get("discount") or data.get("Discount") or 0,
        )

        # Auto-assign by city (status stays "new")
        worker = db.query(UserDB).filter(
            UserDB.role == "worker",
            UserDB.city == branch,
        ).first()
        if worker:
            order.assigned_worker_id = worker.id
            order.assigned_at = datetime.utcnow()

        db.add(order)
        db.commit()
        db.refresh(order)

        logger.info(f"✅ Order #{order.id} created from Rekaz (ref: {rekaz_number})")

        _notify_workers_new_order(order, db)

        return {"status": "created", "order_id": order.id}
    except Exception as e:
        logger.error(f"❌ Rekaz webhook error: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  ADMIN — Manual order creation
# ════════════════════════════════════════════════════════════

@router.post("/manual")
def create_manual_order(
    req: ManualOrderRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Create order manually (admin only)."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    lat, lng = req.latitude, req.longitude
    if not lat and req.district_name:
        lat, lng = _geocode_district(req.district_name, req.city or "الرياض")

    order = OrderDB(
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        customer_email=req.customer_email,
        district_name=req.district_name,
        city=req.city,
        full_address=req.full_address,
        latitude=lat,
        longitude=lng,
        number_of_cars=req.number_of_cars,
        dashcam_type=req.dashcam_type,
        service_type=req.service_type,
        status="new",
        notes=req.notes,
        admin_notes=req.admin_notes,
        payment_status=req.payment_status,
        total_amount=req.total_amount,
        assigned_worker_id=req.assigned_worker_id,
    )
    if req.assigned_worker_id:
        order.assigned_at = datetime.utcnow()

    db.add(order)
    db.commit()
    db.refresh(order)

    _notify_workers_new_order(order, db)

    return {"success": True, "order_id": order.id}


# ════════════════════════════════════════════════════════════
#  LIST / GET orders
# ════════════════════════════════════════════════════════════

@router.get("")
def list_orders(
    status: Optional[str] = None,
    worker_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """
    List orders.
    - Admin: all orders (optionally filtered by status / worker_id).
    - Worker: only orders assigned to them.
    - search: filter by customer name or phone (partial match).
    """
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = db.query(OrderDB)

    if user.role == "worker":
        q = q.filter(OrderDB.assigned_worker_id == user.id)
    elif not user.is_admin and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorised")

    if status:
        q = q.filter(OrderDB.status == status)
    if worker_id and (user.is_admin or user.role == "admin"):
        q = q.filter(OrderDB.assigned_worker_id == worker_id)
    if search:
        q = q.filter(
            (OrderDB.customer_name.ilike(f"%{search}%")) |
            (OrderDB.customer_phone.ilike(f"%{search}%"))
        )

    total = q.count()
    orders = q.order_by(OrderDB.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "orders": [_order_to_dict(o, db) for o in orders],
    }


@router.get("/{order_id}")
def get_order(
    order_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Get single order detail."""
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if user.role == "worker" and order.assigned_worker_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    return _order_to_dict(order, db)


# ════════════════════════════════════════════════════════════
#  ASSIGN order to worker (admin)
# ════════════════════════════════════════════════════════════

@router.put("/{order_id}/assign")
def assign_order(
    order_id: int,
    req: AssignOrderRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Assign order to a worker (admin only)."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    worker = db.query(UserDB).filter(UserDB.id == req.worker_id, UserDB.role == "worker").first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    order.assigned_worker_id = worker.id
    order.assigned_at = datetime.utcnow()
    db.commit()

    _notify_workers_new_order(order, db)

    return {"success": True, "order": _order_to_dict(order, db)}


# ════════════════════════════════════════════════════════════
#  UPDATE order status (worker / admin)
# ════════════════════════════════════════════════════════════

@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
    req: UpdateStatusRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """
    Update order status.
    Workers can move: new → contacted → completed (requires 3 photos).
    Admins can set any status.
    """
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()

    # Permission check
    if user.role == "worker" and order.assigned_worker_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    valid_statuses = {"new", "contacted", "completed"}
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    # Block completing unless 3 photos are uploaded
    if req.status == "completed":
        photo_count = db.query(OrderPhotoDB).filter(OrderPhotoDB.order_id == order_id).count()
        if photo_count < 3:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot complete order: {photo_count}/3 photos uploaded. Please upload 3 photos first."
            )

    old_status = order.status
    order.status = req.status

    if req.worker_notes:
        order.worker_notes = req.worker_notes

    # Timestamp milestones
    now = datetime.utcnow()
    if req.status == "contacted" and not order.started_at:
        order.started_at = now
    elif req.status == "completed" and not order.completed_at:
        order.completed_at = now
        # Deduct inventory when order is completed
        _deduct_inventory(order, db)

    order.updated_at = now
    db.commit()

    logger.info(f"📋 Order #{order.id} status: {old_status} → {req.status}")

    return {"success": True, "order": _order_to_dict(order, db)}


# ════════════════════════════════════════════════════════════
#  ADD PHOTO to order (worker)
# ════════════════════════════════════════════════════════════

@router.post("/{order_id}/photos")
def add_order_photo(
    order_id: int,
    req: AddPhotoRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Add completion photo to an order (max 3)."""
    order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    existing_count = db.query(OrderPhotoDB).filter(OrderPhotoDB.order_id == order_id).count()
    if existing_count >= 3:
        raise HTTPException(status_code=400, detail="Maximum 3 photos per order")

    photo = OrderPhotoDB(
        order_id=order_id,
        photo_url=req.photo_url,
        photo_type=req.photo_type,
        uploaded_by=current_user["user_id"],
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    return {
        "success": True,
        "photo": {
            "id": photo.id,
            "photo_url": photo.photo_url,
            "photo_type": photo.photo_type,
        },
    }


# ════════════════════════════════════════════════════════════
#  ADMIN — list workers
# ════════════════════════════════════════════════════════════

@router.get("/workers/list")
def list_workers(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """List all workers (admin only)."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    workers = db.query(UserDB).filter(UserDB.role == "worker").all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "phone": w.phone,
            "city": w.city,
        }
        for w in workers
    ]

