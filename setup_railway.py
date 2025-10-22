#!/usr/bin/env python3
"""
Railway Database Setup Helper
"""

import requests
import json
import os
from dotenv import load_dotenv

def create_railway_project():
    """Guide user through Railway setup"""
    print("🚂 Railway Database Setup")
    print("=" * 30)
    
    print("\n📋 Step-by-step instructions:")
    print("1. Go to https://railway.app")
    print("2. Sign up with GitHub")
    print("3. Click 'New Project'")
    print("4. Select 'Database' → 'MySQL'")
    print("5. Wait for database to provision")
    print("6. Go to 'Variables' tab")
    print("7. Copy the MYSQL_URL")
    
    print("\n🔗 Your connection string will look like:")
    print("mysql://root:password@containers-us-west-xxx.railway.app:port/railway")
    
    print("\n📝 After getting the URL:")
    print("1. Update your .env file:")
    print("   DATABASE_URL=mysql+pymysql://root:password@host:port/railway")
    print("2. Run migration:")
    print("   python migrate_to_cloud.py 'your_railway_url'")
    print("3. Test connection:")
    print("   python test_cloud_db.py")

def test_database_url(db_url):
    """Test if database URL is valid"""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def update_env_file(db_url):
    """Update .env file with new database URL"""
    env_file = ".env"
    
    # Read current .env
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update or add DATABASE_URL
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("DATABASE_URL="):
            lines[i] = f"DATABASE_URL={db_url}\n"
            updated = True
            break
    
    if not updated:
        lines.append(f"DATABASE_URL={db_url}\n")
    
    # Write back to .env
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Updated {env_file} with new database URL")

def main():
    print("Choose an option:")
    print("1. Show Railway setup instructions")
    print("2. Test database connection")
    print("3. Update .env file")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        create_railway_project()
    elif choice == "2":
        db_url = input("Enter database URL: ").strip()
        test_database_url(db_url)
    elif choice == "3":
        db_url = input("Enter database URL: ").strip()
        update_env_file(db_url)
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()


