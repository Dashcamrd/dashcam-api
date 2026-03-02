"""
Inventory Management Models
- Products catalog (RASD 1.0, RASD 2.0, etc.)
- Per-worker inventory tracking
- Transaction audit log
- Worker payment transactions
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, Text, UniqueConstraint
from database import Base
from datetime import datetime


class ProductDB(Base):
    """Product catalog"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False)   # "RASD 1.0"
    sku = Column(String(100), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    low_stock_threshold = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkerInventoryDB(Base):
    """Current inventory count per worker per product"""
    __tablename__ = "worker_inventory"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('worker_id', 'product_id', name='unique_worker_product'),
    )


class InventoryTransactionDB(Base):
    """Audit log for every inventory change"""
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity_change = Column(Integer, nullable=False)  # +N = consignment, -N = order completed
    reason = Column(String(50), nullable=False)        # "consignment", "order_completed", "adjustment"
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ManualCarsDB(Base):
    """
    Manual car additions for installations done outside the system.
    Admin adds these to track total installations that don't have orders.
    """
    __tablename__ = "manual_cars"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    cars_count = Column(Integer, nullable=False)
    notes = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by_name = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkerPaymentDB(Base):
    """
    Manual payment records from company to worker.
    Admin records when money is transferred to a worker.
    """
    __tablename__ = "worker_payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)              # Amount in SAR
    description = Column(String(500), nullable=True)    # e.g. "January salary transfer"
    payment_date = Column(DateTime, nullable=False)     # When the payment was made
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Admin who added it
    created_by_name = Column(String(200), nullable=True)  # Cached admin name
    created_at = Column(DateTime, default=datetime.utcnow)

