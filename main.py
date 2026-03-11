from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
import asyncio

# Configure logging to show INFO level messages in Render logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from routers import auth, devices, media, gps, alarms, tasks, reports, admin, database_info, forwarding, notifications
from routers import orders, inventory, worker_auth, uploads, income  # OMS
from database import Base, engine
from models.device_db import DeviceDB
from models.user_db import UserDB
from models.device_cache_db import DeviceCacheDB, AlarmDB  # New cache models
from models.fcm_token_db import FCMTokenDB, UserNotificationSettingsDB  # Push notification models
from models.order_db import OrderDB, OrderPhotoDB, OrderActivityDB  # OMS models
from models.inventory_db import ProductDB, WorkerInventoryDB, InventoryTransactionDB, WorkerPaymentDB, ManualCarsDB  # Inventory models
from services.device_auto_config_service import device_auto_config  # Auto-configuration service

# Create all tables (with error handling for connection issues)
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized successfully")
except Exception as e:
    print(f"⚠️  Warning: Could not initialize database tables: {e}")
    print("   Tables will be created on first database access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Starts the device auto-configuration background worker.
    """
    # Startup
    print("🚀 Starting background services...")
    device_auto_config.start()
    print("✅ Device Auto-Configuration Service started")
    
    yield  # App is running
    
    # Shutdown
    print("🛑 Stopping background services...")
    device_auto_config.stop()
    print("✅ Background services stopped")

app = FastAPI(
    title="Dashcam Management Platform API",
    description="Multi-tenant dashcam management platform with manufacturer API integration",
    version="1.0.0",
    lifespan=lifespan  # Add lifespan for background services
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
app.include_router(notifications.router)  # Push notifications management
app.include_router(orders.router)       # Order Management System
app.include_router(inventory.router)    # Inventory management
app.include_router(worker_auth.router)  # Worker authentication
app.include_router(uploads.router)      # Photo uploads (Cloudinary)
app.include_router(income.router)      # Worker income tracking

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


@app.get("/account-deletion", response_class=HTMLResponse)
def account_deletion_page():
    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>حذف الحساب - Road by DashcamRD</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.card{max-width:600px;width:100%;background:#1a1a1a;border-radius:16px;padding:40px;border:1px solid #2a2a2a}
h1{font-size:24px;margin-bottom:8px;color:#fff}
.brand{color:#888;font-size:14px;margin-bottom:32px}
h2{font-size:18px;color:#fff;margin:24px 0 12px}
p,li{font-size:15px;line-height:1.7;color:#bbb}
ol{padding-right:20px;margin-bottom:24px}
li{margin-bottom:8px}
.highlight{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px 20px;margin:20px 0}
.highlight p{color:#94a3b8}
a{color:#60a5fa;text-decoration:none}
a:hover{text-decoration:underline}
.warn{color:#f87171;font-weight:600}
.divider{border:none;border-top:1px solid #2a2a2a;margin:28px 0}
.footer{text-align:center;color:#555;font-size:13px;margin-top:24px}
</style>
</head>
<body>
<div class="card">
<h1>طلب حذف الحساب</h1>
<p class="brand">Road by DashcamRD</p>

<h2>كيفية حذف حسابك</h2>
<ol>
<li>افتح تطبيق <strong>Road</strong> على هاتفك</li>
<li>اذهب إلى <strong>الحساب</strong> ← <strong>إعدادات الحساب</strong></li>
<li>اضغط على <strong>حذف الحساب</strong></li>
<li>أكّد عملية الحذف</li>
</ol>

<div class="highlight">
<p class="warn">⚠️ تنبيه: حذف الحساب نهائي ولا يمكن التراجع عنه.</p>
<p>سيتم حذف جميع بياناتك بما في ذلك: معلومات الحساب، الأجهزة المسجلة، وسجل التنبيهات.</p>
</div>

<hr class="divider">

<h2>طريقة بديلة</h2>
<p>إذا لم تتمكن من الوصول إلى التطبيق، يمكنك إرسال طلب حذف الحساب عبر البريد الإلكتروني:</p>
<p style="margin-top:8px"><a href="mailto:support@dashcamrd.com">support@dashcamrd.com</a></p>
<p style="margin-top:4px;color:#888">يرجى إرسال الطلب من نفس البريد الإلكتروني المسجل في حسابك. سيتم معالجة طلبك خلال 48 ساعة.</p>

<hr class="divider">

<h2>Account Deletion Request</h2>
<p>To delete your account, open the <strong>Road</strong> app → <strong>Account</strong> → <strong>Account Settings</strong> → <strong>Delete Account</strong>.</p>
<p style="margin-top:8px">Alternatively, email <a href="mailto:support@dashcamrd.com">support@dashcamrd.com</a> from your registered email. Your request will be processed within 48 hours.</p>
<p style="margin-top:8px">All your data including account info, registered devices, and alarm history will be permanently deleted.</p>

<div class="footer">© 2026 DashcamRD. All rights reserved.</div>
</div>
</body>
</html>"""

