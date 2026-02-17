"""
Import Airtable CSV records into the orders database.
Usage: python import_airtable.py

1. Deletes all existing orders + photos
2. Reads CSV files from a folder
3. Matches workers by name
4. Inserts all orders
"""

import csv
import os
import sys
from datetime import datetime
from database import engine, SessionLocal
from models.order_db import OrderDB, OrderPhotoDB
from models.user_db import UserDB
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────
CSV_FOLDER = os.getenv("CSV_FOLDER", "/Users/fahadalmanee/Desktop/airtable records")

# Worker name → CSV filename (without .csv)
# The script matches CSV filename to worker name in DB
WORKER_FILES = {
    "Khaled.csv": "khaled",      # Worker name in DB
    "Waleed.csv": "waleed",      # Worker name in DB
    "Tareq.csv": "tareq",        # Worker name in DB
}

# Status mapping: Airtable Arabic → our status
STATUS_MAP = {
    "تم التركيب": "completed",
    "جديد": "new",
    "ملغي": "completed",       # Cancelled orders → treat as completed (historical)
    "تركيب مجدول": "contacted",  # Scheduled → contacted
    "مؤجل": "contacted",        # Postponed → contacted
    "تم التواصل": "contacted",
}

# Service type mapping
SERVICE_MAP = {
    "توصيل وتركيب": "delivery_and_install",
    "تركيب فقط": "install_only",
    "صيانة": "maintenance",
    "استرجاع": "return",
}


def parse_location(location: str):
    """Parse 'الرياض حي المروج' → city='الرياض', district='حي المروج'"""
    if not location:
        return None, None

    location = location.strip()

    # Known city prefixes
    cities = ["الرياض", "جدة", "جده", "الدمام", "الخبر", "الظهران", "مكة", "المدينة", "الشرقيه", "الجبيله"]

    for city in cities:
        if location.startswith(city):
            rest = location[len(city):].strip()
            return city, rest if rest else None
            
    # If it starts with حي directly, assume الرياض
    if location.startswith("حي "):
        return None, location

    # Otherwise the whole thing might be a city name
    return location, None


def parse_date(date_str: str):
    """Parse '4/23/2024 5:11pm' → datetime"""
    if not date_str or not date_str.strip():
        return None
    try:
        # Handle formats like "4/23/2024 5:11pm"
        return datetime.strptime(date_str.strip(), "%m/%d/%Y %I:%M%p")
    except ValueError:
        try:
            return datetime.strptime(date_str.strip(), "%m/%d/%Y %I:%M %p")
        except ValueError:
            logger.warning(f"Could not parse date: '{date_str}'")
            return None


def main():
    db = SessionLocal()

    try:
        # ── Step 1: Look up worker IDs ──
        logger.info("🔍 Looking up workers in database...")
        worker_map = {}  # CSV filename → worker_id
        
        for csv_file, worker_name in WORKER_FILES.items():
            worker = db.query(UserDB).filter(
                UserDB.role == "worker",
                UserDB.name.ilike(f"%{worker_name}%")
            ).first()
            
            if worker:
                worker_map[csv_file] = worker.id
                logger.info(f"  ✅ {csv_file} → Worker '{worker.name}' (ID: {worker.id})")
            else:
                logger.warning(f"  ⚠️ {csv_file} → Worker '{worker_name}' NOT FOUND in DB!")
                worker_map[csv_file] = None

        # ── Step 2: Delete existing orders ──
        logger.info("\n🗑️ Deleting existing orders...")
        photo_count = db.query(OrderPhotoDB).count()
        order_count = db.query(OrderDB).count()
        
        db.execute(text("DELETE FROM order_photos"))
        db.execute(text("DELETE FROM orders"))
        # Reset auto-increment
        db.execute(text("ALTER SEQUENCE orders_id_seq RESTART WITH 1"))
        db.commit()
        logger.info(f"  Deleted {photo_count} photos and {order_count} orders")

        # ── Step 3: Import CSVs ──
        total_imported = 0
        total_skipped = 0

        for csv_file, worker_name in WORKER_FILES.items():
            csv_path = os.path.join(CSV_FOLDER, csv_file)
            if not os.path.exists(csv_path):
                logger.warning(f"⚠️ CSV file not found: {csv_path}")
                continue

            worker_id = worker_map.get(csv_file)
            logger.info(f"\n📄 Importing {csv_file} (worker_id={worker_id})...")

            imported = 0
            skipped = 0

            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        name = (row.get('Name') or '').strip()
                        phone = (row.get('Phone') or '').strip()
                        
                        if not name or not phone:
                            skipped += 1
                            continue

                        location = (row.get('Location') or '').strip()
                        city, district = parse_location(location)

                        num_cars_str = (row.get('Number of Cars') or '1').strip()
                        try:
                            num_cars = int(num_cars_str)
                        except ValueError:
                            num_cars = 1

                        install_type = (row.get('Type') or '').strip()  # الفيوز / الولاعة
                        service_type_ar = (row.get('Type of Service') or '').strip()
                        service_type = SERVICE_MAP.get(service_type_ar, 'delivery_and_install')

                        dashcam_type = (row.get('Type of Dashcam') or '').strip()
                        if not dashcam_type:
                            dashcam_type = 'Unknown'

                        status_ar = (row.get('Status') or '').strip()
                        status = STATUS_MAP.get(status_ar, 'new')

                        last_updated_str = (row.get('Last updated') or '').strip()
                        last_updated = parse_date(last_updated_str)

                        notes_text = (row.get('Notes') or '').strip()
                        # Add install type to notes if present
                        if install_type and install_type not in ('', notes_text):
                            notes_text = f"[{install_type}] {notes_text}" if notes_text else f"[{install_type}]"

                        # Detect payment status from notes
                        payment_status = "paid"
                        if notes_text and "مادفع" in notes_text:
                            payment_status = "unpaid"

                        # Build timestamps
                        created_at = last_updated or datetime.utcnow()
                        updated_at = last_updated or datetime.utcnow()
                        completed_at = last_updated if status == "completed" else None
                        started_at = last_updated if status in ("contacted", "completed") else None
                        assigned_at = created_at if worker_id else None

                        order = OrderDB(
                            customer_name=name,
                            customer_phone=phone,
                            district_name=district,
                            city=city,
                            number_of_cars=num_cars,
                            dashcam_type=dashcam_type,
                            service_type=service_type,
                            status=status,
                            notes=notes_text if notes_text else None,
                            payment_status=payment_status,
                            assigned_worker_id=worker_id,
                            created_at=created_at,
                            updated_at=updated_at,
                            assigned_at=assigned_at,
                            started_at=started_at,
                            completed_at=completed_at,
                        )
                        db.add(order)
                        imported += 1

                    except Exception as e:
                        logger.error(f"  ❌ Row {row_num} error: {e} | Data: {row}")
                        skipped += 1

            db.commit()
            logger.info(f"  ✅ Imported {imported} orders, skipped {skipped}")
            total_imported += imported
            total_skipped += skipped

        logger.info(f"\n{'='*50}")
        logger.info(f"🎉 IMPORT COMPLETE: {total_imported} orders imported, {total_skipped} skipped")
        logger.info(f"{'='*50}")

        # Show summary by worker
        for csv_file, worker_name in WORKER_FILES.items():
            worker_id = worker_map.get(csv_file)
            if worker_id:
                count = db.query(OrderDB).filter(OrderDB.assigned_worker_id == worker_id).count()
                logger.info(f"  {worker_name}: {count} orders")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Import failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

