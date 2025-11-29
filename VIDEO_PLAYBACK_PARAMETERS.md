# Video Playback API Call - Parameters & Values

## 📋 Complete Parameter Flow

### **Example Request:**
- **Device ID:** `18270761136`
- **Date:** `2025-01-15`
- **Start Time:** `10:30:00`
- **End Time:** `11:00:00`
- **Channel:** `1` (Front)

---

## 🔄 Step 1: Flutter App → Backend API

**Flutter Code:**
```dart
ApiService.startPlayback(
  deviceId: "18270761136",
  channel: 1,
  startTime: "2025-01-15 10:30:00",
  endTime: "2025-01-15 11:00:00",
)
```

**HTTP Request:**
```http
POST https://dashcam-api.onrender.com/media/playback
Headers:
  Content-Type: application/json
  Authorization: Bearer <JWT_TOKEN>

Body:
{
  "device_id": "18270761136",
  "channel": 1,
  "start_time": "2025-01-15 10:30:00",
  "end_time": "2025-01-15 11:00:00"
}
```

---

## 🔄 Step 2: Backend API → Media Adapter

**Backend Router (`routers/media.py`):**
```python
playback_data = MediaAdapter.build_playback_request(
    device_id="18270761136",
    start_time="2025-01-15 10:30:00",  # String format
    end_time="2025-01-15 11:00:00",    # String format
    channel=1,
    data_type=1,      # Playback
    stream_type=0     # 0=main stream
)
```

**Media Adapter Processing:**
```python
# Converts time strings to Unix timestamps:
start_dt = datetime.strptime("2025-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
start_timestamp = int(start_dt.timestamp())  # → 1736932200

end_dt = datetime.strptime("2025-01-15 11:00:00", "%Y-%m-%d %H:%M:%S")
end_timestamp = int(end_dt.timestamp())  # → 1736934000
```

---

## 🔄 Step 3: Backend → Manufacturer API

**Final Request to Manufacturer API:**
```http
POST http://180.167.106.70:9337/api/v1/media/playback
Headers:
  Content-Type: application/json
  X-Token: <MANUFACTURER_JWT_TOKEN>

Body:
{
  "deviceId": "18270761136",        // ✅ String
  "channels": [1],                  // ✅ Array of int
  "startTime": 1736932200,          // ✅ Unix timestamp (int seconds)
  "endTime": 1736934000,            // ✅ Unix timestamp (int seconds)
  "dataType": 1,                    // ✅ int (1=Playback)
  "streamType": 0,                  // ✅ int (0=main stream, 1=sub stream)
  "method": 0,                      // ✅ int (0=normal playback)
  "multiple": 1                     // ✅ int (1=1x speed)
}
```

---

## 📊 Parameter Details

| Parameter | Type | Value | Description |
|-----------|------|-------|-------------|
| **deviceId** | `string` | `"18270761136"` | Device identifier |
| **channels** | `array<int>` | `[1]` | Channel array (1=Front, 2=Rear, 3=Interior) |
| **startTime** | `int` | `1736932200` | Unix timestamp (seconds) for start time |
| **endTime** | `int` | `1736934000` | Unix timestamp (seconds) for end time |
| **dataType** | `int` | `1` | 1=Playback, 0=Preview |
| **streamType** | `int` | `0` | 0=main stream, 1=sub stream |
| **method** | `int` | `0` | 0=normal, 1=FF, 2=keyframe rewind, 3=keyframe, 4=single frame |
| **multiple** | `int` | `1` | 0=invalid, 1=1x, 2=2x, 3=4x, 4=8x, 5=16x |

---

## 🔢 Time Conversion Examples

| Date/Time String | Unix Timestamp | Calculation |
|-----------------|----------------|-------------|
| `"2025-01-15 10:30:00"` | `1736932200` | `datetime(2025, 1, 15, 10, 30, 0).timestamp()` |
| `"2025-01-15 11:00:00"` | `1736934000` | `datetime(2025, 1, 15, 11, 0, 0).timestamp()` |
| `"2025-01-15 12:00:00"` | `1736937600` | `datetime(2025, 1, 15, 12, 0, 0).timestamp()` |

**Formula:**
```python
from datetime import datetime
timestamp = int(datetime.strptime("2025-01-15 10:30:00", "%Y-%m-%d %H:%M:%S").timestamp())
```

---

## ✅ Response Format

**Manufacturer API Response:**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "videos": [
      {
        "deviceId": "18270761136",
        "channel": 1,
        "playUrl": "rtsp://...",
        "errCode": 0,
        "errDesc": ""
      }
    ]
  }
}
```

**Backend Response to Flutter:**
```json
{
  "success": true,
  "message": "Playback started successfully",
  "device_id": "18270761136",
  "time_range": "2025-01-15 10:30:00 to 2025-01-15 11:00:00",
  "videos": [
    {
      "device_id": "18270761136",
      "channel": 1,
      "play_url": "rtsp://...",
      "err_code": 0,
      "err_desc": ""
    }
  ]
}
```

---

## 🎯 Summary

1. **Flutter** sends: `"2025-01-15 10:30:00"` (string)
2. **Backend** converts to: `1736932200` (Unix timestamp int)
3. **Manufacturer API** receives: All required parameters with correct types
4. **Response** contains: `play_url` for video streaming

**All parameters are now correctly formatted and sent! ✅**

