"""
Standalone database setup script - minimal dependencies
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from datetime import datetime

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set")
    exit(1)

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Define models
class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))
    name = Column(String(100))
    email = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class DeviceDB(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, index=True)
    name = Column(String(200))
    assigned_user_id = Column(Integer, ForeignKey("users.id"))
    org_id = Column(String(100))
    status = Column(String(50), default="offline")
    brand = Column(String(100))
    model = Column(String(100))
    firmware_version = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

def setup_database():
    """Create tables and initial data"""
    print("🔄 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created")
    
    db = SessionLocal()
    
    try:
        # Create admin user
        admin_user = db.query(UserDB).filter(UserDB.invoice_no == "ADMIN001").first()
        if not admin_user:
            admin_user = UserDB(
                invoice_no="ADMIN001",
                password_hash=hash_password("admin123"),
                name="System Administrator",
                email="admin@dashcam-platform.com",
                created_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print("✅ Created admin user:")
            print(f"   Invoice Number: ADMIN001")
            print(f"   Password: admin123")
        else:
            print("ℹ️  Admin user already exists")
        
        # Create test user
        test_user = db.query(UserDB).filter(UserDB.invoice_no == "INV-001").first()
        if not test_user:
            test_user = UserDB(
                invoice_no="INV-001",
                password_hash=hash_password("test123"),
                name="Test User",
                email="test@example.com",
                created_at=datetime.utcnow()
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            print("✅ Created test user:")
            print(f"   Invoice Number: INV-001")
            print(f"   Password: test123")
        else:
            print("ℹ️  Test user already exists")
        
        # Create test device
        test_device = db.query(DeviceDB).filter(DeviceDB.device_id == "cam001").first()
        if not test_device:
            test_device = DeviceDB(
                device_id="cam001",
                name="Test Camera 001",
                assigned_user_id=test_user.id,
                org_id="ORG001",
                status="online",
                brand="Generic",
                model="CAM-001",
                firmware_version="1.0.0",
                created_at=datetime.utcnow()
            )
            db.add(test_device)
            db.commit()
            print("✅ Created test device:")
            print(f"   Device ID: cam001")
            print(f"   Assigned to: {test_user.name}")
        else:
            print("ℹ️  Test device already exists")
        
        print("\n" + "="*60)
        print("✅ DATABASE SETUP COMPLETE!")
        print("="*60)
        print("\nYou can now login to your app with:")
        print("  Invoice: INV-001")
        print("  Password: test123")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_database()

