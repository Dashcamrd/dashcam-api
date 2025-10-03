"""
Setup script to create initial admin user and test data
"""
from database import SessionLocal
from models.user_db import UserDB
from services.auth_service import hash_password
from datetime import datetime

def create_initial_data():
    """Create initial admin user and sample data"""
    db = SessionLocal()
    
    try:
        # Check if admin user already exists
        admin_user = db.query(UserDB).filter(UserDB.invoice_no == "ADMIN001").first()
        
        if not admin_user:
            # Create admin user
            admin_user = UserDB(
                invoice_no="ADMIN001",
                password_hash=hash_password("admin123"),
                name="System Administrator",
                email="admin@dashcam-platform.com",
                created_at=datetime.utcnow()
            )
            
            db.add(admin_user)
            db.commit()
            print("✅ Created admin user:")
            print(f"   Invoice Number: ADMIN001")
            print(f"   Password: admin123")
            print(f"   Email: admin@dashcam-platform.com")
        else:
            print("ℹ️  Admin user already exists")
        
        # Create sample customer user
        customer_user = db.query(UserDB).filter(UserDB.invoice_no == "INV2024001").first()
        
        if not customer_user:
            customer_user = UserDB(
                invoice_no="INV2024001",
                password_hash=hash_password("customer123"),
                name="Demo Customer",
                email="customer@example.com",
                created_at=datetime.utcnow()
            )
            
            db.add(customer_user)
            db.commit()
            print("✅ Created sample customer:")
            print(f"   Invoice Number: INV2024001")
            print(f"   Password: customer123")
            print(f"   Email: customer@example.com")
        else:
            print("ℹ️  Sample customer already exists")
            
        print("\n🎉 Initial data setup complete!")
        print("\nNext steps:")
        print("1. Start the server: python start.py")
        print("2. Visit http://localhost:8000/docs for API documentation")
        print("3. Login with admin credentials to assign devices")
        print("4. Configure manufacturer API credentials in .env file")
        
    except Exception as e:
        print(f"❌ Error setting up initial data: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Setting up initial data for Dashcam Management Platform...")
    create_initial_data()
