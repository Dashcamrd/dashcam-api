from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging to show INFO level messages in Render logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from routers import auth, devices, media, gps, alarms, tasks, reports, admin, database_info, forwarding
from database import Base, engine
from models.device_db import DeviceDB
from models.user_db import UserDB
from models.device_cache_db import DeviceCacheDB, AlarmDB  # New cache models

# Create all tables (with error handling for connection issues)
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized successfully")
except Exception as e:
    print(f"⚠️  Warning: Could not initialize database tables: {e}")
    print("   Tables will be created on first database access")

app = FastAPI(
    title="Dashcam Management Platform API",
    description="Multi-tenant dashcam management platform with manufacturer API integration",
    version="1.0.0"
)

# ✅ Allow frontend apps to talk to the backend
origins = [
    "http://localhost:3000",   # React dev server
    "http://127.0.0.1:3000",   # alternative localhost
    "http://localhost:5173",   # Vite dev server
    "http://127.0.0.1:5173",
    "http://localhost:8080",   # Vue dev server
    "*"                        # (optional) allow all origins for testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] in development
    allow_credentials=True,
    allow_methods=["*"],    # allow all HTTP methods
    allow_headers=["*"],    # allow all headers
)

# Include all routers
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(media.router)
app.include_router(gps.router)
app.include_router(alarms.router)
app.include_router(tasks.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(database_info.router)
app.include_router(forwarding.router)  # Data forwarding from vendor (webhooks)

@app.get("/")
def root():
    return {"message": "Backend MVP with is running and frontend can connect"}

@app.get("/health")
def health_check():
    """Health check endpoint for Railway deployment"""
    try:
        # Quick database connectivity check (non-blocking)
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        # Return ok even if database check fails (app is still running)
        return {"status": "ok", "database": "disconnected", "message": str(e)}

