"""
Migration script for Order Management System & Inventory tables.

Run once: python migrate_oms.py

Adds:
  - users.role column  (default 'user')
  - users.city column
  - orders table
  - order_photos table
  - products table
  - worker_inventory table
  - inventory_transactions table
"""
from database import engine, Base
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run():
    conn = engine.connect()
    inspector = inspect(engine)

    # ── 1. Add columns to 'users' table ──────────────────────
    existing_cols = {c["name"] for c in inspector.get_columns("users")}

    if "role" not in existing_cols:
        logger.info("Adding 'role' column to users...")
        conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
        conn.commit()
        logger.info("✅ role column added")
    else:
        logger.info("✔ role column already exists")

    if "city" not in existing_cols:
        logger.info("Adding 'city' column to users...")
        conn.execute(text("ALTER TABLE users ADD COLUMN city VARCHAR(100)"))
        conn.commit()
        logger.info("✅ city column added")
    else:
        logger.info("✔ city column already exists")

    # ── 2. Create new tables via SQLAlchemy ───────────────────
    # Import all models so Base.metadata knows about them
    from models.order_db import OrderDB, OrderPhotoDB
    from models.inventory_db import ProductDB, WorkerInventoryDB, InventoryTransactionDB

    existing_tables = set(inspector.get_table_names())
    new_tables = {"orders", "order_photos", "products", "worker_inventory", "inventory_transactions"}
    missing = new_tables - existing_tables

    if missing:
        logger.info(f"Creating tables: {missing}")
        Base.metadata.create_all(bind=engine, tables=[
            Base.metadata.tables[t] for t in missing if t in Base.metadata.tables
        ])
        logger.info(f"✅ Tables created: {missing}")
    else:
        logger.info("✔ All OMS tables already exist")

    # ── 3. Set admin user role ────────────────────────────────
    result = conn.execute(text(
        "UPDATE users SET role = 'admin' WHERE is_admin = true AND (role IS NULL OR role = 'user')"
    ))
    conn.commit()
    logger.info(f"✅ Updated {result.rowcount} admin users with role='admin'")

    conn.close()
    logger.info("🎉 OMS migration complete!")


if __name__ == "__main__":
    run()

