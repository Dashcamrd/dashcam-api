"""
Income Router — Worker income tracking, chart data, and payment records
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from database import SessionLocal
from models.order_db import OrderDB
from models.inventory_db import WorkerPaymentDB
from models.user_db import UserDB
from services.auth_service import get_current_user
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/income", tags=["Income"])

RATE_PER_CAR = 100.0  # SAR per installed car


# ════════════════════════════════════════════════════════════
#  Pydantic schemas
# ════════════════════════════════════════════════════════════

class AddPaymentRequest(BaseModel):
    worker_id: int
    amount: float
    description: Optional[str] = None
    payment_date: Optional[str] = None  # ISO format, defaults to now


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  INCOME SUMMARY — monthly cars installed + income
# ════════════════════════════════════════════════════════════

@router.get("/summary")
def get_income_summary(
    worker_id: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """
    Get income summary for a worker in a specific month.
    - Workers see only their own income.
    - Admins can query any worker by passing worker_id.
    Uses updated_at to determine which month an order belongs to.
    """
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine target worker
    if user.role == "worker":
        target_worker_id = user.id
    elif user.is_admin or user.role == "admin":
        target_worker_id = worker_id if worker_id else user.id
    else:
        raise HTTPException(status_code=403, detail="Not authorised")

    now = datetime.utcnow()
    target_month = month or now.month
    target_year = year or now.year

    # Query completed orders for this worker in the target month
    # Use updated_at as the determining timestamp
    completed_orders = db.query(OrderDB).filter(
        OrderDB.assigned_worker_id == target_worker_id,
        OrderDB.status == "completed",
        extract('month', OrderDB.updated_at) == target_month,
        extract('year', OrderDB.updated_at) == target_year,
    ).all()

    total_cars = sum(o.number_of_cars or 1 for o in completed_orders)
    total_income = total_cars * RATE_PER_CAR

    # Get worker name
    target_worker = db.query(UserDB).filter(UserDB.id == target_worker_id).first()
    worker_name = target_worker.name if target_worker else "Unknown"

    return {
        "worker_id": target_worker_id,
        "worker_name": worker_name,
        "month": target_month,
        "year": target_year,
        "total_orders": len(completed_orders),
        "total_cars": total_cars,
        "rate_per_car": RATE_PER_CAR,
        "total_income": total_income,
    }


# ════════════════════════════════════════════════════════════
#  CHART DATA — daily/monthly breakdown for graph
# ════════════════════════════════════════════════════════════

@router.get("/chart")
def get_income_chart(
    worker_id: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    period: str = Query("month"),  # "month" = daily in that month, "year" = monthly in that year
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """
    Get chart data for income visualization.
    - period="month": Returns daily data points for a specific month.
    - period="year": Returns monthly data points for a specific year.
    """
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "worker":
        target_worker_id = user.id
    elif user.is_admin or user.role == "admin":
        target_worker_id = worker_id if worker_id else user.id
    else:
        raise HTTPException(status_code=403, detail="Not authorised")

    now = datetime.utcnow()
    target_year = year or now.year

    if period == "year":
        # Monthly aggregation for the year
        results = db.query(
            extract('month', OrderDB.updated_at).label('period'),
            func.sum(OrderDB.number_of_cars).label('cars'),
            func.count(OrderDB.id).label('orders'),
        ).filter(
            OrderDB.assigned_worker_id == target_worker_id,
            OrderDB.status == "completed",
            extract('year', OrderDB.updated_at) == target_year,
        ).group_by(
            extract('month', OrderDB.updated_at)
        ).order_by(
            extract('month', OrderDB.updated_at)
        ).all()

        data_points = []
        for m in range(1, 13):
            row = next((r for r in results if int(r.period) == m), None)
            cars = int(row.cars or 0) if row else 0
            orders = int(row.orders or 0) if row else 0
            data_points.append({
                "label": str(m),
                "month": m,
                "cars": cars,
                "orders": orders,
                "income": cars * RATE_PER_CAR,
            })

        return {"period": "year", "year": target_year, "data": data_points}
    else:
        # Daily aggregation for a specific month
        target_month = month or now.month

        import calendar
        days_in_month = calendar.monthrange(target_year, target_month)[1]

        results = db.query(
            extract('day', OrderDB.updated_at).label('period'),
            func.sum(OrderDB.number_of_cars).label('cars'),
            func.count(OrderDB.id).label('orders'),
        ).filter(
            OrderDB.assigned_worker_id == target_worker_id,
            OrderDB.status == "completed",
            extract('month', OrderDB.updated_at) == target_month,
            extract('year', OrderDB.updated_at) == target_year,
        ).group_by(
            extract('day', OrderDB.updated_at)
        ).order_by(
            extract('day', OrderDB.updated_at)
        ).all()

        data_points = []
        cumulative_cars = 0
        cumulative_income = 0.0
        for d in range(1, days_in_month + 1):
            row = next((r for r in results if int(r.period) == d), None)
            daily_cars = int(row.cars or 0) if row else 0
            daily_orders = int(row.orders or 0) if row else 0
            cumulative_cars += daily_cars
            cumulative_income += daily_cars * RATE_PER_CAR
            data_points.append({
                "label": str(d),
                "day": d,
                "daily_cars": daily_cars,
                "daily_orders": daily_orders,
                "daily_income": daily_cars * RATE_PER_CAR,
                "cumulative_cars": cumulative_cars,
                "cumulative_income": cumulative_income,
            })

        return {
            "period": "month",
            "month": target_month,
            "year": target_year,
            "data": data_points,
        }


# ════════════════════════════════════════════════════════════
#  PAYMENT TRANSACTIONS — list & create
# ════════════════════════════════════════════════════════════

@router.get("/payments")
def get_payments(
    worker_id: Optional[int] = Query(None),
    limit: int = Query(50),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """
    Get payment transactions for a worker.
    Workers see their own payments. Admins can see any worker's payments.
    """
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "worker":
        target_worker_id = user.id
    elif user.is_admin or user.role == "admin":
        target_worker_id = worker_id if worker_id else None  # None = all workers
    else:
        raise HTTPException(status_code=403, detail="Not authorised")

    query = db.query(WorkerPaymentDB).order_by(WorkerPaymentDB.payment_date.desc())
    if target_worker_id:
        query = query.filter(WorkerPaymentDB.worker_id == target_worker_id)
    
    payments = query.limit(limit).all()

    return {
        "payments": [
            {
                "id": p.id,
                "worker_id": p.worker_id,
                "amount": p.amount,
                "description": p.description,
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                "created_by_name": p.created_by_name,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ]
    }


@router.post("/payments")
def add_payment(
    req: AddPaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """
    Add a manual payment record. Admin only.
    """
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user or (not user.is_admin and user.role != "admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    # Verify target worker exists
    worker = db.query(UserDB).filter(UserDB.id == req.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    payment_date = datetime.utcnow()
    if req.payment_date:
        try:
            payment_date = datetime.fromisoformat(req.payment_date.replace("Z", "+00:00"))
        except ValueError:
            payment_date = datetime.utcnow()

    payment = WorkerPaymentDB(
        worker_id=req.worker_id,
        amount=req.amount,
        description=req.description,
        payment_date=payment_date,
        created_by=user.id,
        created_by_name=user.name,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    logger.info(f"💰 Payment of {req.amount} SAR added for worker #{req.worker_id} by {user.name}")

    return {
        "success": True,
        "payment": {
            "id": payment.id,
            "worker_id": payment.worker_id,
            "amount": payment.amount,
            "description": payment.description,
            "payment_date": payment.payment_date.isoformat(),
            "created_by_name": payment.created_by_name,
        },
    }


@router.delete("/payments/{payment_id}")
def delete_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Delete a payment record. Admin only."""
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user or (not user.is_admin and user.role != "admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    payment = db.query(WorkerPaymentDB).filter(WorkerPaymentDB.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    db.delete(payment)
    db.commit()

    logger.info(f"🗑️ Payment #{payment_id} deleted by {user.name}")
    return {"success": True}

