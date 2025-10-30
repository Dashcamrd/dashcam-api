from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LatestGpsDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed_kmh: Optional[float] = Field(default=None, description="Speed in km/h")
    direction_deg: Optional[float] = Field(default=None, description="Direction in degrees")
    altitude_m: Optional[float] = Field(default=None, description="Altitude in meters")
    timestamp_ms: Optional[int] = Field(default=None, description="Unix epoch in milliseconds")
    address: Optional[str] = None


class TrackPointDto(BaseModel):
    latitude: float
    longitude: float
    timestamp_ms: int
    speed_kmh: Optional[float] = None
    direction_deg: Optional[float] = None


class TrackPlaybackDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    start_time_ms: int
    end_time_ms: int
    points: List[TrackPointDto] = []


class AccStateDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    acc_on: Optional[bool] = None
    last_online_time_ms: Optional[int] = None


class DeviceDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    name: Optional[str] = None
    plate_no: Optional[str] = None
    online: Optional[bool] = None
    acc_on: Optional[bool] = None


# Media DTOs
class VideoStreamDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    channel: int
    play_url: str = Field(..., alias="playUrl")
    stream_type: Optional[int] = Field(default=None, alias="streamType")
    data_type: Optional[int] = Field(default=None, alias="dataType")


class MediaPreviewDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    videos: List[VideoStreamDto] = []


# Task DTOs
class TaskDto(BaseModel):
    task_id: str = Field(..., alias="taskId")
    device_id: str = Field(..., alias="deviceId")
    content: Optional[str] = None
    status: Optional[str] = None  # pending, in_progress, completed, failed
    priority: Optional[str] = None
    created_at: Optional[int] = Field(default=None, alias="createdAt")
    send_time: Optional[int] = Field(default=None, alias="sendTime")
    completed_at: Optional[int] = Field(default=None, alias="completedAt")
    result: Optional[Dict[str, Any]] = None


class TaskResultDto(BaseModel):
    task_id: str = Field(..., alias="taskId")
    device_id: str = Field(..., alias="deviceId")
    status: Optional[str] = None
    delivered_at: Optional[int] = Field(default=None, alias="deliveredAt")
    acknowledged_at: Optional[int] = Field(default=None, alias="acknowledgedAt")
    delivery_attempts: Optional[int] = Field(default=None, alias="deliveryAttempts")
    error_details: Optional[Dict[str, Any]] = Field(default=None, alias="errorDetails")
    device_response: Optional[Dict[str, Any]] = Field(default=None, alias="deviceResponse")


# Alarm DTOs
class AlarmDto(BaseModel):
    alarm_id: str = Field(..., alias="alarmId")
    device_id: str = Field(..., alias="deviceId")
    type_id: Optional[int] = Field(default=None, alias="typeId")
    level: Optional[str] = None  # critical, warning, info
    message: Optional[str] = None
    timestamp_ms: Optional[int] = Field(default=None, alias="timestampMs")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    speed: Optional[float] = None
    altitude: Optional[float] = None
    has_attachment: Optional[bool] = Field(default=False, alias="hasAttachment")
    status: Optional[str] = None  # active, acknowledged, resolved


class AlarmSummaryDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    total_alarms: int
    critical_count: int
    warning_count: int
    info_count: int
    alarms: List[AlarmDto] = []


# Statistics DTOs
class VehicleStatisticsDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    date_range: str
    total_distance_km: Optional[float] = Field(default=None, alias="totalDistanceKm")
    total_duration_s: Optional[int] = Field(default=None, alias="totalDurationS")
    average_speed_kmh: Optional[float] = Field(default=None, alias="averageSpeedKmh")
    max_speed_kmh: Optional[float] = Field(default=None, alias="maxSpeedKmh")
    total_stops: Optional[int] = Field(default=None, alias="totalStops")
    fuel_consumption: Optional[float] = None
    idle_time_s: Optional[int] = Field(default=None, alias="idleTimeS")
    total_alarms: Optional[int] = Field(default=None, alias="totalAlarms")


class VehicleDetailDto(BaseModel):
    device_id: str = Field(..., alias="deviceId")
    date: str
    trips: List[Dict[str, Any]] = []
    stops: List[Dict[str, Any]] = []
    alarms: List[AlarmDto] = []
    total_distance_km: Optional[float] = Field(default=None, alias="totalDistanceKm")
    total_duration_s: Optional[int] = Field(default=None, alias="totalDurationS")

