#!/usr/bin/env python3
"""
Migration script to move from local MySQL to cloud database
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def export_local_data():
    """Export data from local MySQL database"""
    print("📤 Exporting data from local database...")
    
    # Load local database config
    load_dotenv()
    local_db_url = os.getenv("DATABASE_URL")
    
    if not local_db_url:
        print("❌ DATABASE_URL not found in .env file")
        return False
    
    try:
        engine = create_engine(local_db_url)
        
        with engine.connect() as conn:
            # Get all users
            users_result = conn.execute(text("SELECT * FROM users"))
            users = users_result.fetchall()
            
            # Get all devices
            devices_result = conn.execute(text("SELECT * FROM devices"))
            devices = devices_result.fetchall()
            
            print(f"✅ Found {len(users)} users and {len(devices)} devices")
            
            return {
                'users': [dict(row._mapping) for row in users],
                'devices': [dict(row._mapping) for row in devices]
            }
            
    except Exception as e:
        print(f"❌ Error exporting data: {e}")
        return False

def import_to_cloud(cloud_db_url, data):
    """Import data to cloud database"""
    print("📥 Importing data to cloud database...")
    
    try:
        engine = create_engine(cloud_db_url)
        
        with engine.connect() as conn:
            # Create tables first
            from database import Base
            Base.metadata.create_all(bind=engine)
            
            # Import users
            for user in data['users']:
                conn.execute(text("""
                    INSERT INTO users (id, invoice_no, password_hash, name, email, created_at)
                    VALUES (:id, :invoice_no, :password_hash, :name, :email, :created_at)
                    ON DUPLICATE KEY UPDATE
                    password_hash = VALUES(password_hash),
                    name = VALUES(name),
                    email = VALUES(email)
                """), user)
            
            # Import devices
            for device in data['devices']:
                conn.execute(text("""
                    INSERT INTO devices (id, device_id, name, assigned_user_id, org_id, status, brand, model, firmware_version, created_at)
                    VALUES (:id, :device_id, :name, :assigned_user_id, :org_id, :status, :brand, :model, :firmware_version, :created_at)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    assigned_user_id = VALUES(assigned_user_id),
                    org_id = VALUES(org_id),
                    status = VALUES(status),
                    brand = VALUES(brand),
                    model = VALUES(model),
                    firmware_version = VALUES(firmware_version)
                """), device)
            
            conn.commit()
            print("✅ Data imported successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error importing data: {e}")
        return False

def test_cloud_connection(cloud_db_url):
    """Test connection to cloud database"""
    print("🔍 Testing cloud database connection...")
    
    try:
        engine = create_engine(cloud_db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            
            if test_value == 1:
                print("✅ Cloud database connection successful!")
                return True
            else:
                print("❌ Cloud database connection failed!")
                return False
                
    except Exception as e:
        print(f"❌ Error connecting to cloud database: {e}")
        return False

def main():
    print("🚀 Cloud Database Migration Tool")
    print("=" * 40)
    
    # Check if cloud database URL is provided
    if len(sys.argv) < 2:
        print("Usage: python migrate_to_cloud.py <cloud_database_url>")
        print("Example: python migrate_to_cloud.py 'mysql+pymysql://user:pass@host:port/db'")
        return
    
    cloud_db_url = sys.argv[1]
    
    # Step 1: Test cloud connection
    if not test_cloud_connection(cloud_db_url):
        return
    
    # Step 2: Export local data
    data = export_local_data()
    if not data:
        return
    
    # Step 3: Import to cloud
    if import_to_cloud(cloud_db_url, data):
        print("\n🎉 Migration completed successfully!")
        print("📝 Update your .env file with the new DATABASE_URL")
        print(f"   DATABASE_URL={cloud_db_url}")
    else:
        print("\n❌ Migration failed!")

if __name__ == "__main__":
    main()


