"""
VMS Background Sync Service

Periodically polls the manufacturer VMS API in bulk to keep device_cache
fresh with ACC status, online state, and GPS coordinates. This is a
workaround for broken VMS data-forwarding and can be disabled by setting
SYNC_INTERVAL_SECONDS = 0 or calling vms_sync.stop().

Budget: ~9 API calls per 60 s cycle (1 device_states + 8 GPS batches of 50),
well within the 60 req/min rate limit.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from database import SessionLocal
from models.device_db import DeviceDB
from models.device_cache_db import DeviceCacheDB, AlarmDB
from services.manufacturer_api_service import manufacturer_api
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

_sync_thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="vms-sync")


class VMSSyncService:

    SYNC_INTERVAL_SECONDS = 60
    GPS_BATCH_SIZE = 50

    def __init__(self):
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._last_sync_at: Optional[datetime] = None
        self._last_sync_duration: Optional[float] = None
        self._last_error: Optional[str] = None
        self._devices_synced = 0
        self._gps_updated = 0
        self._status_updated = 0
        logger.info("🔄 VMS Sync Service initialized")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._task is not None and not self._task.done():
            logger.warning("⚠️ VMS Sync Service is already running")
            return
        self.running = True
        self._task = asyncio.create_task(self._run_worker())
        logger.info("✅ VMS Sync Service started")

    def stop(self):
        self.running = False
        if self._task is not None:
            self._task.cancel()
            logger.info("🛑 VMS Sync Service stopped")

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "last_sync_at": self._last_sync_at.isoformat() if self._last_sync_at else None,
            "last_sync_duration_s": round(self._last_sync_duration, 2) if self._last_sync_duration else None,
            "devices_synced": self._devices_synced,
            "gps_updated": self._gps_updated,
            "status_updated": self._status_updated,
            "last_error": self._last_error,
        }

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    SYNC_CYCLE_TIMEOUT = 45

    async def _run_worker(self):
        logger.info(
            f"🔄 VMS sync worker started, polling every {self.SYNC_INTERVAL_SECONDS}s"
        )
        while self.running:
            try:
                await asyncio.wait_for(
                    self._sync_cycle(), timeout=self.SYNC_CYCLE_TIMEOUT
                )
            except asyncio.TimeoutError:
                self._last_error = "Sync cycle timed out"
                logger.error(
                    f"❌ VMS sync cycle exceeded {self.SYNC_CYCLE_TIMEOUT}s timeout, skipping"
                )
            except Exception as e:
                self._last_error = str(e)
                logger.error(f"❌ VMS sync cycle error: {e}", exc_info=True)
            await asyncio.sleep(self.SYNC_INTERVAL_SECONDS)

    # ------------------------------------------------------------------
    # Single sync cycle
    # ------------------------------------------------------------------

    async def _sync_cycle(self):
        start = asyncio.get_event_loop().time()

        # Single auth check — avoids hammering VMS with N login attempts
        # when the token is invalid (each API call would retry independently).
        loop = asyncio.get_running_loop()
        auth_ok = await loop.run_in_executor(
            _sync_thread_pool, manufacturer_api._ensure_valid_token
        )
        if not auth_ok:
            logger.warning("⚠️ VMS sync: auth failed, skipping cycle")
            self._last_error = "VMS authentication failed"
            return

        db: Session = SessionLocal()
        try:
            device_ids = self._get_assigned_device_ids(db)
            if not device_ids:
                logger.debug("VMS sync: no assigned devices, skipping")
                return

            self._devices_synced = len(device_ids)

            status_count = await self._sync_device_states(db, device_ids)
            db.flush()  # make new rows visible before GPS phase
            gps_count = await self._sync_gps(db, device_ids)

            db.commit()

            self._status_updated = status_count
            self._gps_updated = gps_count
            self._last_sync_at = datetime.now(timezone.utc)
            self._last_error = None

            elapsed = asyncio.get_event_loop().time() - start
            self._last_sync_duration = elapsed
            logger.info(
                f"✅ VMS sync done: {len(device_ids)} devices, "
                f"{status_count} statuses, {gps_count} GPS updates "
                f"in {elapsed:.1f}s"
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_assigned_device_ids(db: Session) -> List[str]:
        rows = (
            db.query(DeviceDB.device_id)
            .filter(DeviceDB.assigned_user_id.isnot(None))
            .all()
        )
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Device states (ACC + online)
    # ------------------------------------------------------------------

    async def _sync_device_states(
        self, db: Session, device_ids: List[str]
    ) -> int:
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                _sync_thread_pool,
                manufacturer_api.get_device_states, {"deviceIds": device_ids}
            )
        except Exception as e:
            logger.warning(f"⚠️ VMS device_states call failed: {e}")
            return 0

        code = result.get("code")
        if code not in (200, 0):
            logger.warning(
                f"⚠️ VMS device_states non-success code={code}: "
                f"{result.get('message', '')}"
            )
            return 0

        device_list = (result.get("data") or {}).get("list") or []
        updated = 0
        acc_changes: List[Dict[str, Any]] = []

        for item in device_list:
            did = item.get("deviceId")
            if not did:
                continue

            acc_raw = item.get("accState", 0)
            acc_on = acc_raw == 1 or acc_raw is True

            state_raw = item.get("state", 0)
            is_online = state_raw == 1

            cache = db.query(DeviceCacheDB).filter(
                DeviceCacheDB.device_id == did
            ).first()

            now = datetime.utcnow()
            previous_acc = None
            if cache is None:
                cache = DeviceCacheDB(device_id=did)
                db.add(cache)
            else:
                previous_acc = cache.acc_status

            dev_row = db.query(DeviceDB).filter(DeviceDB.device_id == did).first()
            parking_enabled = dev_row.parking_mode if dev_row else False

            cache.acc_status = acc_on
            if not acc_on and parking_enabled:
                cache.is_online = True
            else:
                cache.is_online = is_online
            cache.parking_mode = parking_enabled
            if cache.is_online:
                cache.last_online_time = now
            cache.updated_at = now
            updated += 1

            if previous_acc is not None and previous_acc != acc_on:
                acc_changes.append({
                    "device_id": did,
                    "acc_on": acc_on,
                    "previous": previous_acc,
                    "lat": cache.latitude,
                    "lng": cache.longitude,
                    "speed": (cache.speed / 10.0) if cache.speed else None,
                })

        if acc_changes:
            self._process_acc_notifications(db, acc_changes)

        return updated

    def _process_acc_notifications(
        self, db: Session, changes: List[Dict[str, Any]]
    ) -> None:
        """Create alarm records and send push notifications for ACC changes."""
        import json as _json

        for ch in changes:
            did = ch["device_id"]
            acc_on = ch["acc_on"]
            try:
                device = db.query(DeviceDB).filter(DeviceDB.device_id == did).first()
                device_name = device.name if device else did

                alarm_type_id = 999002 if acc_on else 999003
                alarm_name = "ACC ON - Engine Started" if acc_on else "ACC OFF - Engine Stopped"
                new_alarm = AlarmDB(
                    device_id=did,
                    alarm_type=alarm_type_id,
                    alarm_type_name=alarm_name,
                    alarm_level=1,
                    latitude=ch.get("lat"),
                    longitude=ch.get("lng"),
                    speed=ch.get("speed"),
                    alarm_time=datetime.utcnow(),
                    alarm_data=_json.dumps({
                        "type": "acc_change",
                        "acc_status": "on" if acc_on else "off",
                        "device_name": device_name,
                        "source": "vms_sync",
                    }),
                )
                db.add(new_alarm)

                sent = NotificationService.send_acc_notification(
                    db=db,
                    device_id=did,
                    acc_on=acc_on,
                    previous_acc_status=ch["previous"],
                )
                logger.info(
                    f"📱 [sync] ACC {'ON' if acc_on else 'OFF'} for {did} — "
                    f"sent {sent} notifications"
                )
            except Exception as e:
                logger.error(f"❌ [sync] notification error for {did}: {e}")

    # ------------------------------------------------------------------
    # GPS (batched)
    # ------------------------------------------------------------------

    async def _sync_gps(self, db: Session, device_ids: List[str]) -> int:
        updated = 0
        for i in range(0, len(device_ids), self.GPS_BATCH_SIZE):
            batch = device_ids[i : i + self.GPS_BATCH_SIZE]
            count = await self._sync_gps_batch(db, batch)
            updated += count
        return updated

    async def _sync_gps_batch(
        self, db: Session, batch: List[str]
    ) -> int:
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                _sync_thread_pool,
                manufacturer_api.get_latest_gps_v2, {"deviceId": batch}
            )
        except Exception as e:
            logger.warning(f"⚠️ VMS GPS batch call failed: {e}")
            return 0

        code = result.get("code")
        if code not in (200, 0):
            logger.warning(
                f"⚠️ VMS GPS batch non-success code={code}: "
                f"{result.get('message', '')}"
            )
            return 0

        device_list = (result.get("data") or {}).get("list") or []
        updated = 0

        for item in device_list:
            did = item.get("deviceId")
            if not did:
                continue

            gps = item.get("gps") or {}
            lat = gps.get("latitude")
            lng = gps.get("longitude")
            if lat is None or lng is None:
                continue

            speed_raw = gps.get("speed")
            speed = speed_raw / 10.0 if speed_raw is not None else None

            direction = gps.get("direction")
            altitude = gps.get("altitude")
            gps_time_unix = gps.get("time")
            last_online_unix = item.get("lastOnlineTime")

            cache = db.query(DeviceCacheDB).filter(
                DeviceCacheDB.device_id == did
            ).first()

            now = datetime.utcnow()
            if cache is None:
                cache = DeviceCacheDB(device_id=did)
                db.add(cache)

            cache.latitude = lat
            cache.longitude = lng
            cache.speed = speed
            cache.direction = direction
            cache.altitude = altitude

            if gps_time_unix:
                cache.gps_time = datetime.utcfromtimestamp(gps_time_unix)
            if last_online_unix:
                cache.last_online_time = datetime.utcfromtimestamp(last_online_unix)

            cache.updated_at = now
            updated += 1

        return updated


vms_sync = VMSSyncService()
