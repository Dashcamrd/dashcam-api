import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user_db import UserDB
from models.device_db import DeviceDB

def check_user(invoice_no: str):
    db: Session = SessionLocal()
    try:
        # Check User
        user = db.query(UserDB).filter(UserDB.invoice_no == invoice_no).first()
        if not user:
            print(f"❌ User {invoice_no} not found!")
            return
        
        print(f"👤 User Found: {user.name}")
        print(f"   ID: {user.id}")
        print(f"   Invoice: {user.invoice_no}")
        print(f"   Is Admin: {user.is_admin}")
        
        # Check Devices
        if user.is_admin:
            count = db.query(DeviceDB).count()
            print(f"📱 Admin View: Should see all {count} devices")
        else:
            devices = db.query(DeviceDB).filter(DeviceDB.assigned_user_id == user.id).all()
            print(f"📱 User View: Has {len(devices)} assigned devices")
            for d in devices:
                print(f"   - {d.device_id} ({d.name})")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_user.py <invoice_no>")
        sys.exit(1)
    
    check_user(sys.argv[1])

