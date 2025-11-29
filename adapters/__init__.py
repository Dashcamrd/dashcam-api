"""
Adapters for mapping vendor API responses to stable DTOs.
Separates vendor-specific field names and formats from internal data structures.
"""
from .gps_adapter import GPSAdapter
from .device_adapter import DeviceAdapter
from .media_adapter import MediaAdapter
from .task_adapter import TaskAdapter
from .statistics_adapter import StatisticsAdapter

__all__ = [
    "GPSAdapter",
    "DeviceAdapter",
    "MediaAdapter",
    "TaskAdapter",
    "StatisticsAdapter"
]

