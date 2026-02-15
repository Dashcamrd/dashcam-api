from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from models.user import UserCreate, UserLogin, ChangePassword, UserResponse, PasswordResetRequest, ProfileUpdateRequest, ProfileResponse
import services.auth_service as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/delete-account-info", response_class=HTMLResponse)
def delete_account_info():
    """
    Public web page explaining how to delete your Road app account.
    Required by Google Play Store data safety policy.
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Delete Your Account - Road App</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 600px;
                margin: 40px auto;
                padding: 20px;
                color: #333;
                line-height: 1.6;
            }
            h1 { color: #1a1a2e; }
            .steps { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .steps li { margin: 10px 0; }
            .warning { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 8px; margin: 20px 0; }
            .contact { background: #e8f4fd; padding: 15px; border-radius: 8px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>🚗 Road App - Delete Your Account</h1>
        <p>You can delete your Road app account and all associated data at any time.</p>

        <div class="steps">
            <h2>How to delete your account:</h2>
            <ol>
                <li>Open the <strong>Road</strong> app on your device</li>
                <li>Go to <strong>Settings</strong> (gear icon)</li>
                <li>Tap <strong>Account Settings</strong></li>
                <li>Tap <strong>Delete Account</strong></li>
                <li>Confirm by entering your password</li>
            </ol>
        </div>

        <div class="warning">
            <strong>⚠️ Warning:</strong> Account deletion is permanent and cannot be undone.
        </div>

        <h2>What data is deleted:</h2>
        <ul>
            <li>Your account credentials (invoice number, email, password)</li>
            <li>Your profile information (name, phone number)</li>
            <li>Your device associations</li>
            <li>Push notification tokens</li>
        </ul>

        <h2>Data retention:</h2>
        <p>All user data is deleted immediately upon account deletion. No data is retained after deletion.</p>

        <div class="contact">
            <strong>Need help?</strong><br>
            Contact us at <a href="mailto:fahad@dashcamrd.com">fahad@dashcamrd.com</a>
        </div>
    </body>
    </html>
    """

@router.post("/register")
def register(user: UserCreate):
    """
    Register a new user with invoice number, device ID, name, email, and password.
    Returns a JWT access token if registration is successful.
    """
    return auth_service.register_user(user)

@router.post("/login")
def login(user: UserLogin):
    """
    Login with invoice number & password.
    Returns a JWT access token if credentials are valid.
    """
    return auth_service.login_user(user)

@router.post("/change-password")
def change_password(
    password_data: ChangePassword, 
    current_user: dict = Depends(auth_service.get_current_user)
):
    """
    Change the current user's password.
    Requires valid JWT token and current password verification.
    """
    return auth_service.change_password(
        current_user["invoice_no"], 
        password_data.current_password,
        password_data.new_password
    )

@router.post("/reset-password")
def reset_password(reset_request: PasswordResetRequest):
    """
    Request password reset via email.
    Sends a reset link/token to the user's email.
    """
    return auth_service.request_password_reset(reset_request.email)

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: dict = Depends(auth_service.get_current_user)):
    """
    Get current user information from JWT token.
    """
    from database import SessionLocal
    from models.user_db import UserDB
    
    db = SessionLocal()
    try:
        db_user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        return db_user
    finally:
        db.close()

@router.get("/profile", response_model=ProfileResponse)
def get_user_profile(current_user: dict = Depends(auth_service.get_current_user)):
    """
    Get current user's profile (invoice_no, name, email, phone).
    """
    from database import SessionLocal
    from models.user_db import UserDB
    
    db = SessionLocal()
    try:
        db_user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return ProfileResponse(
            invoice_no=db_user.invoice_no,
            name=db_user.name,
            email=db_user.email,
            phone=db_user.phone
        )
    finally:
        db.close()

@router.put("/profile", response_model=ProfileResponse)
def update_user_profile(
    profile_data: ProfileUpdateRequest,
    current_user: dict = Depends(auth_service.get_current_user)
):
    """
    Update current user's profile (name, email, phone).
    """
    from database import SessionLocal
    from models.user_db import UserDB
    
    db = SessionLocal()
    try:
        db_user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields if provided
        if profile_data.name is not None:
            db_user.name = profile_data.name
        if profile_data.email is not None:
            db_user.email = profile_data.email
        if profile_data.phone is not None:
            db_user.phone = profile_data.phone
        
        db.commit()
        db.refresh(db_user)
        
        return ProfileResponse(
            invoice_no=db_user.invoice_no,
            name=db_user.name,
            email=db_user.email,
            phone=db_user.phone
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")
    finally:
        db.close()

@router.delete("/account")
def delete_account(current_user: dict = Depends(auth_service.get_current_user)):
    """
    Delete the current user's account permanently.
    This action cannot be undone. All user data will be deleted.
    """
    return auth_service.delete_user_account(current_user["user_id"])
