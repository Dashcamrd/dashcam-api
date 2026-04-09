"""
Monitoring Service - Collects comprehensive system, application, and fleet metrics.
"""
import os
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)

class MonitoringService:
    """Collects and tracks all system metrics"""

    def __init__(self):
        self._start_time = time.time()
        self._request_times: deque = deque(maxlen=10000)
        self._endpoint_stats: Dict[str, Dict] = {}
        self._error_count = 0
        self._total_requests = 0
        self._forwarding_count = 0
        self._forwarding_gps_count = 0
        self._forwarding_alarm_count = 0
        self._lock = Lock()
        self._last_forwarding_time: Optional[float] = None
        self._vms_response_times: deque = deque(maxlen=100)
        self._db_response_times: deque = deque(maxlen=100)

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    @property
    def uptime_human(self) -> str:
        seconds = int(self.uptime_seconds)
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)

    def record_request(self, endpoint: str, duration_ms: float, status_code: int):
        with self._lock:
            self._total_requests += 1
            self._request_times.append(duration_ms)
            if status_code >= 400:
                self._error_count += 1
            if endpoint not in self._endpoint_stats:
                self._endpoint_stats[endpoint] = {
                    "count": 0, "errors": 0, "total_ms": 0.0,
                    "max_ms": 0.0, "times": deque(maxlen=100)
                }
            stats = self._endpoint_stats[endpoint]
            stats["count"] += 1
            stats["total_ms"] += duration_ms
            stats["max_ms"] = max(stats["max_ms"], duration_ms)
            stats["times"].append(duration_ms)
            if status_code >= 400:
                stats["errors"] += 1

    def record_forwarding(self, gps_count: int = 0, alarm_count: int = 0):
        with self._lock:
            self._forwarding_count += 1
            self._forwarding_gps_count += gps_count
            self._forwarding_alarm_count += alarm_count
            self._last_forwarding_time = time.time()

    def record_vms_response(self, duration_ms: float):
        with self._lock:
            self._vms_response_times.append(duration_ms)

    def record_db_response(self, duration_ms: float):
        with self._lock:
            self._db_response_times.append(duration_ms)

    def _percentile(self, data, p):
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (p / 100)
        f = int(k)
        c = f + 1
        if c >= len(sorted_data):
            return sorted_data[f]
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

    def get_system_metrics(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)

        return {
            "cpu": {
                "percent": round(cpu_percent, 1),
                "count": cpu_count,
                "load_avg_1m": round(load_avg[0], 2),
                "load_avg_5m": round(load_avg[1], 2),
                "load_avg_15m": round(load_avg[2], 2),
            },
            "memory": {
                "total_mb": round(mem.total / 1024 / 1024),
                "used_mb": round(mem.used / 1024 / 1024),
                "available_mb": round(mem.available / 1024 / 1024),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 1),
                "percent": round(disk.percent, 1),
            },
            "network": {
                "bytes_sent_mb": round(net.bytes_sent / 1024 / 1024, 1),
                "bytes_recv_mb": round(net.bytes_recv / 1024 / 1024, 1),
            },
        }

    def get_api_metrics(self) -> Dict[str, Any]:
        with self._lock:
            times = list(self._request_times)
            total = self._total_requests
            errors = self._error_count

        avg = sum(times) / len(times) if times else 0
        p50 = self._percentile(times, 50)
        p95 = self._percentile(times, 95)
        p99 = self._percentile(times, 99)
        max_time = max(times) if times else 0
        error_rate = (errors / total * 100) if total > 0 else 0

        top_endpoints = []
        with self._lock:
            for ep, stats in sorted(self._endpoint_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:15]:
                ep_times = list(stats["times"])
                top_endpoints.append({
                    "endpoint": ep,
                    "requests": stats["count"],
                    "errors": stats["errors"],
                    "avg_ms": round(stats["total_ms"] / stats["count"], 1) if stats["count"] > 0 else 0,
                    "max_ms": round(stats["max_ms"], 1),
                    "p95_ms": round(self._percentile(ep_times, 95), 1),
                })

        return {
            "total_requests": total,
            "total_errors": errors,
            "error_rate_percent": round(error_rate, 2),
            "response_times": {
                "avg_ms": round(avg, 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
                "max_ms": round(max_time, 1),
            },
            "top_endpoints": top_endpoints,
        }

    def get_forwarding_metrics(self) -> Dict[str, Any]:
        with self._lock:
            last_time = self._last_forwarding_time
            seconds_since = round(time.time() - last_time, 1) if last_time else None
            return {
                "total_webhooks": self._forwarding_count,
                "total_gps_records": self._forwarding_gps_count,
                "total_alarms": self._forwarding_alarm_count,
                "last_received_seconds_ago": seconds_since,
                "forwarding_active": seconds_since is not None and seconds_since < 120,
            }

    def get_vms_metrics(self) -> Dict[str, Any]:
        with self._lock:
            times = list(self._vms_response_times)
        if not times:
            return {"avg_ms": 0, "p95_ms": 0, "max_ms": 0, "samples": 0}
        return {
            "avg_ms": round(sum(times) / len(times), 1),
            "p95_ms": round(self._percentile(times, 95), 1),
            "max_ms": round(max(times), 1),
            "samples": len(times),
        }

    def get_db_metrics(self) -> Dict[str, Any]:
        with self._lock:
            times = list(self._db_response_times)
        if not times:
            return {"avg_ms": 0, "p95_ms": 0, "max_ms": 0, "samples": 0}
        return {
            "avg_ms": round(sum(times) / len(times), 1),
            "p95_ms": round(self._percentile(times, 95), 1),
            "max_ms": round(max(times), 1),
            "samples": len(times),
        }


monitoring = MonitoringService()
