"""
Monitoring Router - Comprehensive system health and performance metrics.
Provides real-time visibility into API, database, VMS, fleet, and infrastructure health.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timedelta
import time
import logging
import os

from database import SessionLocal, engine
from services.monitoring_service import monitoring
from services.manufacturer_api_service import manufacturer_api
from services.auth_service import get_current_user

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
async def comprehensive_health(current_user: dict = Depends(get_current_user)):
    """Full system health check — tests every dependency"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": monitoring.uptime_human,
        "uptime_seconds": round(monitoring.uptime_seconds),
        "components": {},
    }
    unhealthy = []

    # 1. Database
    try:
        start = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ms = round((time.time() - start) * 1000, 1)
        monitoring.record_db_response(db_ms)
        health["components"]["database"] = {
            "status": "ok",
            "response_time_ms": db_ms,
        }
    except Exception as e:
        unhealthy.append("database")
        health["components"]["database"] = {"status": "error", "error": str(e)[:200]}

    # 2. VMS API
    try:
        start = time.time()
        has_token = manufacturer_api._ensure_valid_token()
        vms_ms = round((time.time() - start) * 1000, 1)
        monitoring.record_vms_response(vms_ms)
        health["components"]["vms_api"] = {
            "status": "ok" if has_token else "error",
            "response_time_ms": vms_ms,
            "has_token": has_token,
            "base_url": manufacturer_api.base_url,
        }
        if not has_token:
            unhealthy.append("vms_api")
    except Exception as e:
        unhealthy.append("vms_api")
        health["components"]["vms_api"] = {"status": "error", "error": str(e)[:200]}

    # 3. Data Forwarding
    fwd = monitoring.get_forwarding_metrics()
    health["components"]["forwarding"] = {
        "status": "ok" if fwd["forwarding_active"] else "warning",
        "last_received_seconds_ago": fwd["last_received_seconds_ago"],
        "total_gps_records": fwd["total_gps_records"],
        "total_alarms": fwd["total_alarms"],
    }
    if not fwd["forwarding_active"]:
        unhealthy.append("forwarding")

    # 4. DB Connection Pool
    try:
        pool = engine.pool
        health["components"]["db_pool"] = {
            "status": "ok",
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": pool._max_overflow,
        }
    except Exception:
        health["components"]["db_pool"] = {"status": "unknown"}

    if unhealthy:
        health["status"] = "degraded"
        health["unhealthy_components"] = unhealthy

    return health


@router.get("/metrics")
async def full_metrics(current_user: dict = Depends(get_current_user)):
    """Complete performance metrics — API, DB, VMS, system resources"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": monitoring.uptime_human,
        "api": monitoring.get_api_metrics(),
        "system": monitoring.get_system_metrics(),
        "vms": monitoring.get_vms_metrics(),
        "database": monitoring.get_db_metrics(),
        "forwarding": monitoring.get_forwarding_metrics(),
    }


@router.get("/fleet")
async def fleet_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fleet overview — device counts, online/offline, GPS data freshness"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    fleet = {
        "timestamp": datetime.utcnow().isoformat(),
        "devices": {},
        "users": {},
        "data_freshness": {},
    }

    # Device counts from local DB
    try:
        total_devices = db.execute(text("SELECT COUNT(*) FROM devices")).scalar() or 0
        assigned_devices = db.execute(text(
            "SELECT COUNT(*) FROM devices WHERE assigned_user_id IS NOT NULL"
        )).scalar() or 0
        fleet["devices"]["total"] = total_devices
        fleet["devices"]["active"] = assigned_devices
        fleet["devices"]["inactive"] = total_devices - assigned_devices
    except Exception as e:
        fleet["devices"]["error"] = str(e)[:200]

    # User counts
    try:
        total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
        admin_users = db.execute(text(
            "SELECT COUNT(*) FROM users WHERE is_admin = true"
        )).scalar() or 0
        fleet["users"]["total"] = total_users
        fleet["users"]["admins"] = admin_users
        fleet["users"]["regular"] = total_users - admin_users
    except Exception as e:
        fleet["users"]["error"] = str(e)[:200]

    # GPS data freshness from cache
    try:
        now = datetime.utcnow()
        fresh_5min = db.execute(text(
            "SELECT COUNT(*) FROM device_cache WHERE updated_at > :cutoff"
        ), {"cutoff": now - timedelta(minutes=5)}).scalar() or 0
        fresh_30min = db.execute(text(
            "SELECT COUNT(*) FROM device_cache WHERE updated_at > :cutoff"
        ), {"cutoff": now - timedelta(minutes=30)}).scalar() or 0
        stale_1h = db.execute(text(
            "SELECT COUNT(*) FROM device_cache WHERE updated_at < :cutoff"
        ), {"cutoff": now - timedelta(hours=1)}).scalar() or 0
        total_cached = db.execute(text("SELECT COUNT(*) FROM device_cache")).scalar() or 0

        fleet["data_freshness"] = {
            "fresh_under_5min": fresh_5min,
            "fresh_under_30min": fresh_30min,
            "stale_over_1h": stale_1h,
            "total_cached": total_cached,
        }
    except Exception as e:
        fleet["data_freshness"]["error"] = str(e)[:200]

    # Live device states from VMS
    try:
        start = time.time()
        result = manufacturer_api.make_request("device_list", {"page": 1, "pageSize": 1})
        vms_ms = round((time.time() - start) * 1000, 1)
        monitoring.record_vms_response(vms_ms)
        if result and result.get("code") == 200:
            fleet["devices"]["vms_total"] = result.get("data", {}).get("total", 0)
            fleet["devices"]["vms_response_ms"] = vms_ms
    except Exception as e:
        fleet["devices"]["vms_error"] = str(e)[:100]

    # Recent alarms
    try:
        today = datetime.utcnow().date()
        alarms_today = db.execute(text(
            "SELECT COUNT(*) FROM alarms WHERE created_at >= :today"
        ), {"today": today}).scalar() or 0
        alarms_week = db.execute(text(
            "SELECT COUNT(*) FROM alarms WHERE created_at >= :week"
        ), {"week": now - timedelta(days=7)}).scalar() or 0
        fleet["alarms"] = {
            "today": alarms_today,
            "this_week": alarms_week,
        }
    except Exception as e:
        fleet["alarms"] = {"error": str(e)[:200]}

    # Notification settings
    try:
        notif_count = db.execute(text(
            "SELECT COUNT(*) FROM user_notification_settings"
        )).scalar() or 0
        fleet["notification_settings_configured"] = notif_count
    except Exception:
        pass

    return fleet


@router.get("/system")
async def system_resources(current_user: dict = Depends(get_current_user)):
    """Detailed system resource usage — CPU, memory, disk, network, processes"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    metrics = monitoring.get_system_metrics()

    # Add process-level info
    import psutil
    current_process = psutil.Process()
    metrics["process"] = {
        "pid": current_process.pid,
        "memory_mb": round(current_process.memory_info().rss / 1024 / 1024, 1),
        "cpu_percent": round(current_process.cpu_percent(interval=0.1), 1),
        "threads": current_process.num_threads(),
        "open_files": len(current_process.open_files()),
        "connections": len(current_process.connections()),
    }

    # Docker-aware: check if running in container
    metrics["environment"] = {
        "in_docker": os.path.exists("/.dockerenv"),
        "python_version": os.sys.version.split()[0],
        "hostname": os.uname().nodename,
    }

    return metrics


@router.get("/dashboard")
async def dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Single endpoint combining all key metrics for the admin dashboard"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": monitoring.uptime_human,
        "status": "healthy",
    }

    # System resources
    result["system"] = monitoring.get_system_metrics()

    # API performance
    api = monitoring.get_api_metrics()
    result["api"] = {
        "total_requests": api["total_requests"],
        "error_rate": api["error_rate_percent"],
        "avg_response_ms": api["response_times"]["avg_ms"],
        "p95_response_ms": api["response_times"]["p95_ms"],
    }

    # Database health
    try:
        start = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ms = round((time.time() - start) * 1000, 1)
        monitoring.record_db_response(db_ms)
        pool = engine.pool
        result["database"] = {
            "status": "ok",
            "response_ms": db_ms,
            "pool_used": pool.checkedout(),
            "pool_size": pool.size(),
        }
    except Exception as e:
        result["database"] = {"status": "error", "error": str(e)[:100]}
        result["status"] = "degraded"

    # VMS health
    vms_metrics = monitoring.get_vms_metrics()
    try:
        start = time.time()
        has_token = manufacturer_api._ensure_valid_token()
        vms_ms = round((time.time() - start) * 1000, 1)
        monitoring.record_vms_response(vms_ms)
        result["vms"] = {
            "status": "ok" if has_token else "error",
            "response_ms": vms_ms,
            "avg_response_ms": vms_metrics["avg_ms"],
        }
        if not has_token:
            result["status"] = "degraded"
    except Exception as e:
        result["vms"] = {"status": "error", "error": str(e)[:100]}
        result["status"] = "degraded"

    # Forwarding health
    fwd = monitoring.get_forwarding_metrics()
    result["forwarding"] = {
        "active": fwd["forwarding_active"],
        "gps_records": fwd["total_gps_records"],
        "alarms": fwd["total_alarms"],
        "last_received_ago": fwd["last_received_seconds_ago"],
    }
    if not fwd["forwarding_active"]:
        result["status"] = "degraded"

    # Fleet summary
    try:
        total_devices = db.execute(text("SELECT COUNT(*) FROM devices")).scalar() or 0
        total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
        now = datetime.utcnow()
        fresh = db.execute(text(
            "SELECT COUNT(*) FROM device_cache WHERE updated_at > :cutoff"
        ), {"cutoff": now - timedelta(minutes=5)}).scalar() or 0
        result["fleet"] = {
            "total_devices": total_devices,
            "total_users": total_users,
            "devices_with_fresh_data": fresh,
        }
    except Exception as e:
        result["fleet"] = {"error": str(e)[:100]}

    return result
