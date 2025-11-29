#!/usr/bin/env python3
"""
Quick database checker - view tables and data
Usage: python3 check_db.py
"""
import os
import sys
from sqlalchemy import create_engine, text

def check_database():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set")
        print("Usage: export DATABASE_URL='postgresql://...' && python3 check_db.py")
        sys.exit(1)
    
    engine = create_engine(DATABASE_URL)
    
    print("=" * 80)
    print("📊 DATABASE STATUS")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Show tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]
        
        print(f"\n✅ Connected to database")
        print(f"📋 Tables: {', '.join(tables)}")
        
        # Users
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()
        print(f"👥 Users: {user_count}")
        
        # Devices
        result = conn.execute(text("SELECT COUNT(*) FROM devices"))
        device_count = result.scalar()
        print(f"📱 Devices: {device_count}")
        
        # Show users
        print("\n" + "=" * 80)
        print("👥 USERS")
        print("=" * 80)
        result = conn.execute(text("""
            SELECT id, invoice_no, name, email 
            FROM users ORDER BY id
        """))
        print(f"\n{'ID':<5} {'Invoice':<15} {'Name':<30} {'Email'}")
        print("-" * 80)
        for row in result:
            print(f"{row[0]:<5} {row[1]:<15} {row[2]:<30} {row[3]}")
        
        # Show devices with users
        print("\n" + "=" * 80)
        print("📱 DEVICES")
        print("=" * 80)
        result = conn.execute(text("""
            SELECT d.id, d.device_id, d.name, u.name as owner, d.status
            FROM devices d
            LEFT JOIN users u ON d.assigned_user_id = u.id
            ORDER BY d.id
        """))
        print(f"\n{'ID':<5} {'Device ID':<15} {'Name':<25} {'Owner':<25} {'Status'}")
        print("-" * 80)
        for row in result:
            owner = row[3] if row[3] else "Unassigned"
            print(f"{row[0]:<5} {row[1]:<15} {row[2]:<25} {owner:<25} {row[4]}")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    check_database()

