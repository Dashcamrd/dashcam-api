"""
Income Router — Worker income tracking, chart data, and payment records
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, text
from database import SessionLocal
from models.order_db import OrderDB
from models.inventory_db import WorkerPaymentDB
from models.user_db import UserDB
from services.auth_service import get_current_user
from datetime import datetime, date, timedelta
from typing import Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/income", tags=["Income"])

RATE_PER_CAR = 100.0  # SAR per installed car

# Convert UTC stored timestamps to Saudi local time (UTC+3) for correct month/day grouping.
# Saudi Arabia does not observe DST, so a fixed +3h offset is always correct.
# Without this, orders completed between 12:00-2:59 AM Saudi time get counted in the wrong month.
_saudi_updated_at = OrderDB.updated_at + text("INTERVAL '3 hours'")


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
    Get income summary for a worker in a specific month/year.
    - Workers see only their own income.
    - Admins can query any worker by passing worker_id, or all workers if worker_id is omitted.
    - If month is omitted, returns the full year summary.
    Uses updated_at to determine which month an order belongs to.
    """
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine target worker
    if user.role == "worker":
        target_worker_id = user.id
    elif user.is_admin or user.role == "admin":
        target_worker_id = worker_id  # None = all workers
    else:
        raise HTTPException(status_code=403, detail="Not authorised")

    now = datetime.utcnow()
    target_year = year or now.year

    # Build query — use Saudi timezone for correct month/day boundaries
    query = db.query(OrderDB).filter(
        OrderDB.status == "completed",
        extract('year', _saudi_updated_at) == target_year,
    )

    # Filter by worker (None = all workers)
    if target_worker_id is not None:
        query = query.filter(OrderDB.assigned_worker_id == target_worker_id)

    # Filter by month only if provided (omitted = full year)
    if month is not None:
        query = query.filter(extract('month', _saudi_updated_at) == month)

    completed_orders = query.all()

    total_cars = sum(o.number_of_cars or 1 for o in completed_orders)
    total_income = total_cars * RATE_PER_CAR

    logger.info(f"📊 Income summary: worker={target_worker_id}, month={month}, year={target_year} → {len(completed_orders)} orders, {total_cars} cars")

    # Get worker name
    worker_name = "All"
    if target_worker_id is not None:
        target_worker = db.query(UserDB).filter(UserDB.id == target_worker_id).first()
        worker_name = target_worker.name if target_worker else "Unknown"

    return {
        "worker_id": target_worker_id,
        "worker_name": worker_name,
        "month": month,
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
        target_worker_id = worker_id  # None = all workers
    else:
        raise HTTPException(status_code=403, detail="Not authorised")

    now = datetime.utcnow()
    target_year = year or now.year

    if period == "year":
        # Monthly aggregation for the year — use Saudi timezone
        saudi_month = extract('month', _saudi_updated_at)
        base_query = db.query(
            saudi_month.label('period'),
            func.sum(OrderDB.number_of_cars).label('cars'),
            func.count(OrderDB.id).label('orders'),
        ).filter(
            OrderDB.status == "completed",
            extract('year', _saudi_updated_at) == target_year,
        )
        if target_worker_id is not None:
            base_query = base_query.filter(OrderDB.assigned_worker_id == target_worker_id)

        results = base_query.group_by(
            saudi_month
        ).order_by(
            saudi_month
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

        # Use Saudi timezone for correct day boundaries
        saudi_day = extract('day', _saudi_updated_at)
        base_query = db.query(
            saudi_day.label('period'),
            func.sum(OrderDB.number_of_cars).label('cars'),
            func.count(OrderDB.id).label('orders'),
        ).filter(
            OrderDB.status == "completed",
            extract('month', _saudi_updated_at) == target_month,
            extract('year', _saudi_updated_at) == target_year,
        )
        if target_worker_id is not None:
            base_query = base_query.filter(OrderDB.assigned_worker_id == target_worker_id)

        results = base_query.group_by(
            saudi_day
        ).order_by(
            saudi_day
        ).all()

        # For the current month, only include days up to today (Saudi time = UTC+3)
        from datetime import timezone as tz
        saudi_now = datetime.now(tz(timedelta(hours=3)))
        if target_year == saudi_now.year and target_month == saudi_now.month:
            max_day = saudi_now.day
        else:
            max_day = days_in_month

        data_points = []
        cumulative_cars = 0
        cumulative_income = 0.0
        for d in range(1, max_day + 1):
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
            "days_in_month": days_in_month,
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

