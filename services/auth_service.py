from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from database import SessionLocal
from models.user_db import UserDB
from models.user import UserCreate, UserLogin
import os
from dotenv import load_dotenv

load_dotenv()

# 🔑 Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing (use pbkdf2_sha256 for broad compatibility on macOS)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT creation
def create_access_token(data: dict, expires_delta: int = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Database helpers
def create_user(user_data: dict, db: Session = None):
    """Create a new user with invoice number (admin function)"""
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        existing = db.query(UserDB).filter(UserDB.invoice_no == user_data["invoice_no"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Invoice number already exists")
        
        db_user = UserDB(
            invoice_no=user_data["invoice_no"],
            password_hash=hash_password(user_data["password"]),
            name=user_data["name"],
            email=user_data.get("email")
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return {"msg": "User created successfully", "user_id": db_user.id}
    finally:
        if close_db:
            db.close()

def register_user(user: UserCreate):
    """Register a new user with invoice number, device ID, name, email, and password"""
    from models.device_db import DeviceDB
    db: Session = SessionLocal()
    try:
        # Check if invoice number already exists
        existing_user = db.query(UserDB).filter(UserDB.invoice_no == user.invoice_no).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Invoice number already exists")
        
        # Check if email already exists
        if user.email:
            existing_email = db.query(UserDB).filter(UserDB.email == user.email).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create new user
        db_user = UserDB(
            invoice_no=user.invoice_no,
            password_hash=hash_password(user.password),
            name=user.name,
            email=user.email,
            device_id=user.device_id if user.device_id else None,
            is_admin=False  # Default to regular user
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Link device to user if device_id is provided
        if user.device_id:
            device = db.query(DeviceDB).filter(DeviceDB.device_id == user.device_id).first()
            if device:
                # Device exists - link it to the user
                device.assigned_user_id = db_user.id
                db.commit()
            else:
                # Device doesn't exist - create it
                new_device = DeviceDB(
                    device_id=user.device_id,
                    name=f"Device {user.device_id}",
                    assigned_user_id=db_user.id,
                    org_id="ORG001",  # Default org
                    status="offline",
                    created_at=datetime.utcnow()
                )
                db.add(new_device)
                db.commit()
        
        # Create access token for immediate login
        token = create_access_token({
            "sub": db_user.invoice_no,
            "user_id": db_user.id,
            "name": db_user.name,
            "is_admin": db_user.is_admin
        })
        
        return {
            "access_token": token, 
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "invoice_no": db_user.invoice_no,
                "name": db_user.name,
                "email": db_user.email,
                "device_id": db_user.device_id,
                "is_admin": db_user.is_admin
            }
        }
    finally:
        db.close()

def login_user(user: UserLogin):
    """Login with invoice number and password"""
    db: Session = SessionLocal()
    try:
        # Assuming UserLogin now has invoice_no instead of username
        db_user = db.query(UserDB).filter(UserDB.invoice_no == user.invoice_no).first()
        if not db_user or not verify_password(user.password, db_user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid invoice number or password")
        
        token = create_access_token({
            "sub": db_user.invoice_no,
            "user_id": db_user.id,
            "name": db_user.name,
            "is_admin": db_user.is_admin
        })
        return {
            "access_token": token, 
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "invoice_no": db_user.invoice_no,
                "name": db_user.name,
                "email": db_user.email,
                "is_admin": db_user.is_admin
            }
        }
    finally:
        db.close()

def change_password(invoice_no: str, current_password: str, new_password: str, db: Session = None):
    """Change user password after verifying current password"""
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        db_user = db.query(UserDB).filter(UserDB.invoice_no == invoice_no).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify current password
        if not verify_password(current_password, db_user.password_hash):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Update to new password
        db_user.password_hash = hash_password(new_password)
        db.commit()
        return {"message": "Password changed successfully"}
    finally:
        if close_db:
            db.close()

# 🔒 Dependency for protected routes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Decodes JWT and returns user information.
    Raises 401 if token is missing or invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        invoice_no = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not invoice_no or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "invoice_no": invoice_no,
            "user_id": user_id,
            "name": payload.get("name"),
            "is_admin": payload.get("is_admin", False)
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_devices(user_id: int, is_admin: bool = False, db: Session = None) -> list:
    """Get devices assigned to a user. If admin, return all devices."""
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        from models.device_db import DeviceDB
        
        if is_admin:
            # Admin sees ALL devices
            devices = db.query(DeviceDB).all()
        else:
            # Regular user sees only assigned devices
            devices = db.query(DeviceDB).filter(DeviceDB.assigned_user_id == user_id).all()
            
        return devices
    finally:
        if close_db:
            db.close()

def delete_user_account(user_id: int, db: Session = None):
    """
    Delete a user account and all associated data.
    This permanently removes the user from the database.
    """
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        # Get user
        db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Unlink devices from user (set assigned_user_id to None)
        from models.device_db import DeviceDB
        devices = db.query(DeviceDB).filter(DeviceDB.assigned_user_id == user_id).all()
        for device in devices:
            device.assigned_user_id = None
        db.commit()
        
        # Delete user
        db.delete(db_user)
        db.commit()
        
        return {"message": "Account deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting account: {str(e)}")
    finally:
        if close_db:
            db.close()

def request_password_reset(email: str):
    """
    Request password reset via email.
    Generates a temporary password and sends it via email using Resend.
    
    Required environment variables:
    - RESEND_API_KEY: Your Resend API key from https://resend.com
    - FROM_EMAIL: Your verified sender email (e.g., noreply@yourdomain.com)
    """
    import secrets
    import string
    import resend
    import os
    from dotenv import load_dotenv
    
    # Ensure environment variables are loaded
    load_dotenv()
    
    db: Session = SessionLocal()
    try:
        # Find user by email
        db_user = db.query(UserDB).filter(UserDB.email == email).first()
        if not db_user:
            # For security, don't reveal if email exists or not
            return {"message": "If the email exists, a password reset link has been sent."}
        
        # Generate a secure temporary password
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Update user's password
        db_user.password_hash = hash_password(temp_password)
        db.commit()
        
        # Send email using Resend
        try:
            # Get API key and sender email from environment
            api_key = os.getenv("RESEND_API_KEY")
            from_email = os.getenv("FROM_EMAIL", "noreply@app.dashcamrd.com")
            
            if not api_key:
                raise Exception("RESEND_API_KEY environment variable not set")
            
            # Set Resend API key
            resend.api_key = api_key
            
            # Send password reset email
            response = resend.Emails.send({
                "from": from_email,
                "to": email,
                "subject": "Password Reset Request - Road App",
                "html": f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #C93A2B;">Password Reset Request</h2>
                        <p>Hello {db_user.name},</p>
                        <p>You requested a password reset for your Road App account.</p>
                        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p style="margin: 0;"><strong>Invoice Number:</strong> {db_user.invoice_no}</p>
                            <p style="margin: 10px 0;"><strong>Temporary Password:</strong> <code style="background-color: #fff; padding: 5px 10px; border-radius: 3px; font-size: 16px;">{temp_password}</code></p>
                        </div>
                        <p><strong>⚠️ Important:</strong> Please login and change your password immediately for security.</p>
                        <p>If you didn't request this password reset, please ignore this email.</p>
                        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                        <p style="color: #999; font-size: 12px;">This is an automated email. Please do not reply.</p>
                    </div>
                """
            })
            
            print(f"✅ Password reset email sent to {email} (ID: {response.get('id', 'N/A')})")
            
        except Exception as email_error:
            # Log email error but don't reveal to user
            print(f"❌ Failed to send email to {email}: {str(email_error)}")
            # In production, you might want to log this to a monitoring service
            # For now, print temporary password as backup
            print(f"🔐 Backup - Temporary password for {email}: {temp_password}")
        
        return {"message": "If the email exists, a password reset link has been sent."}
    finally:
        db.close()
