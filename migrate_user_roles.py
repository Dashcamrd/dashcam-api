"""
Migration script to add role and city columns to users table.
Run this script against your Railway PostgreSQL database.

Usage:
    python migrate_user_roles.py
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def migrate():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    # Handle Railway's postgres:// URL (SQLAlchemy needs postgresql://)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print(f"🔗 Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if role column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'role'
            """))
            role_exists = result.fetchone() is not None
            
            # Check if city column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'city'
            """))
            city_exists = result.fetchone() is not None
            
            if role_exists and city_exists:
                print("✅ Columns 'role' and 'city' already exist. No migration needed.")
                return True
            
            # Add role column if it doesn't exist
            if not role_exists:
                print("📝 Adding 'role' column to users table...")
                conn.execute(text("""
                    ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'
                """))
                conn.commit()
                print("✅ Added 'role' column")
            
            # Add city column if it doesn't exist
            if not city_exists:
                print("📝 Adding 'city' column to users table...")
                conn.execute(text("""
                    ALTER TABLE users ADD COLUMN city VARCHAR(100)
                """))
                conn.commit()
                print("✅ Added 'city' column")
            
            # Update existing admin users
            print("📝 Updating existing admin users to have role='admin'...")
            conn.execute(text("""
                UPDATE users SET role = 'admin' WHERE is_admin = true AND (role IS NULL OR role = 'user')
            """))
            conn.commit()
            
            print("\n✅ Migration completed successfully!")
            print("   - role column: VARCHAR(20) DEFAULT 'user'")
            print("   - city column: VARCHAR(100)")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    migrate()

