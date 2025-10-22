"""
Database information and query endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user_db import UserDB
from typing import List

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/database-info")
def get_database_info():
    """Get database connection information"""
    from database import DATABASE_URL
    return {
        "database_type": "MySQL" if "mysql" in DATABASE_URL else "PostgreSQL",
        "database_url": DATABASE_URL.split("@")[0] + "@***" if "@" in DATABASE_URL else "Local database",
        "message": "Database connection active"
    }

@router.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    """Get all users from the database"""
    users = db.query(UserDB).all()
    return {
        "total_users": len(users),
        "users": [
            {
                "id": user.id,
                "invoice_no": user.invoice_no,
                "name": user.name,
                "email": user.email,
                "device_id": user.device_id,
                "created_at": user.created_at
            }
            for user in users
        ]
    }

@router.get("/users/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """Get a specific user by ID"""
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        return {"error": f"User with ID {user_id} not found"}
    
    return {
        "id": user.id,
        "invoice_no": user.invoice_no,
        "name": user.name,
        "email": user.email,
        "device_id": user.device_id,
        "created_at": user.created_at
    }
