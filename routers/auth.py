from fastapi import APIRouter, Depends, HTTPException
from models.user import UserCreate, UserLogin, ChangePassword, UserResponse
import services.auth_service as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])

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
    Requires valid JWT token.
    """
    return auth_service.change_password(current_user["invoice_no"], password_data.new_password)

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
