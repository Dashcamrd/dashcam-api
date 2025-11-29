import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user_db import UserDB

def set_admin(invoice_no: str, is_admin: bool = True):
    db: Session = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.invoice_no == invoice_no).first()
        if not user:
            print(f"❌ User with invoice {invoice_no} not found!")
            return
        
        user.is_admin = is_admin
        db.commit()
        status = "ADMIN" if is_admin else "USER"
        print(f"✅ User {user.name} ({invoice_no}) is now an {status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_admin.py <invoice_no> [true/false]")
        print("Example: python set_admin.py INV-123 true")
        sys.exit(1)
    
    invoice = sys.argv[1]
    admin_status = True
    if len(sys.argv) > 2:
        admin_status = sys.argv[2].lower() == "true"
        
    set_admin(invoice, admin_status)

