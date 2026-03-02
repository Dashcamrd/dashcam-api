"""
Order Management Models
- Orders from Rekaz webhook or manual entry
- Completion photos uploaded by workers
- Activity timeline for tracking order events
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, Text
from database import Base
from datetime import datetime


class OrderDB(Base):
    """Installation/delivery orders"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Rekaz reference
    rekaz_order_id = Column(String(100), unique=True, nullable=True, index=True)
    rekaz_reservation_id = Column(String(200), nullable=True)
    
    # Customer info
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(50), nullable=False)
    customer_email = Column(String(200), nullable=True)
    district_name = Column(String(200), nullable=True)
    city = Column(String(100), default="الرياض")
    full_address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Order details
    number_of_cars = Column(Integer, default=1)
    dashcam_type = Column(String(100), nullable=False)       # "RASD 1.0"
    product_sku = Column(String(100), nullable=True)
    service_type = Column(String(50), default="delivery_and_install")
    
    # Assignment
    assigned_worker_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Status: new → contacted → completed
    status = Column(String(30), default="new", index=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    worker_notes = Column(Text, nullable=True)
    
    # Payment
    payment_status = Column(String(50), nullable=True)
    total_amount = Column(Float, nullable=True)
    discount = Column(Float, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderPhotoDB(Base):
    """Completion photos uploaded by worker (up to 3 per order)"""
    __tablename__ = "order_photos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    photo_url = Column(String(500), nullable=False)
    photo_type = Column(String(50), nullable=True)      # "before", "after", "receipt"
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderActivityDB(Base):
    """
    Activity timeline for orders — tracks every significant event.
    Events: order_created, status_changed, payment_changed,
            order_updated, photo_added, worker_assigned
    """
    __tablename__ = "order_activities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)      # e.g. "status_changed"
    description = Column(String(500), nullable=False)     # Human-readable description
    old_value = Column(String(200), nullable=True)        # Previous value (for changes)
    new_value = Column(String(200), nullable=True)        # New value (for changes)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who did it
    performer_name = Column(String(200), nullable=True)   # Cached name for display
    created_at = Column(DateTime, default=datetime.utcnow)

