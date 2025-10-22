from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, devices, media, gps, alarms, tasks, reports, admin, database_info
from database import Base, engine
from models.device_db import DeviceDB
from models.user_db import UserDB

# Create all tables
Base.metadata.create_all(bind=engine)

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

@app.get("/")
def root():
    return {"message": "Backend MVP with is running and frontend can connect"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

