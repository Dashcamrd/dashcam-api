"""
Migration: Add parking_mode column to devices and device_cache tables.

Run on the server with:
    python migrations/add_parking_mode.py

Safe to run multiple times — uses IF NOT EXISTS / exception handling.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text


def migrate():
    statements = [
        "ALTER TABLE devices ADD COLUMN parking_mode BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE device_cache ADD COLUMN parking_mode BOOLEAN NOT NULL DEFAULT FALSE",
    ]

    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
                col = stmt.split("ADD COLUMN ")[1].split(" ")[0]
                tbl = stmt.split("TABLE ")[1].split(" ")[0]
                print(f"  ✅  Added column {col} to {tbl}")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"  ⏭️  Column already exists, skipping: {stmt.split('ADD COLUMN ')[1].split(' ')[0]}")
                else:
                    print(f"  ❌  Error: {e}")
                    raise

    print("\n✅ Migration complete.")


if __name__ == "__main__":
    migrate()
