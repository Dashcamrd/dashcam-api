# Video Playback API Call Flow & Parameters

## 📋 Complete Call Flow

```
Flutter App → Backend API → Manufacturer API → Response
```

## 🔄 Step-by-Step Flow

### 1. **Flutter App** (`video_playback_screen.dart`)

**User Input:**
- `deviceId`: From widget parameter (e.g., "18270761136")
- `_selectedDate`: DateTime (e.g., `DateTime(2025, 1, 15)`)
- `_startTime`: TimeOfDay (e.g., `TimeOfDay(hour: 10, minute: 30)`)
- `_endTime`: TimeOfDay (e.g., `TimeOfDay(hour: 11, minute: 0)`)
- `_selectedChannel`: int (1, 2, or 3)

**Formatting:**
```dart
String _formatDateTime(DateTime date, TimeOfDay time) {
  return "YYYY-MM-DD HH:MM:SS"
  // Example: "2025-01-15 10:30:00"
}
```

**API Call:**
```dart
ApiService.startPlayback(
  deviceId: "18270761136",
  channel: 1,
  startTime: "2025-01-15 10:30:00",  // String format
  endTime: "2025-01-15 11:00:00",     // String format
)
```

---

### 2. **Flutter API Service** (`api_service.dart`)

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
  "start_time": "2025-01-15 10:30:00",  // String
  "end_time": "2025-01-15 11:00:00"     // String
}
```

---

### 3. **Backend API** (`routers/media.py`)

**Endpoint:** `POST /media/playback`

**Request Model:**
```python
class PlaybackRequest(BaseModel):
    device_id: str          # "18270761136"
    channel: Optional[int] = 1
    start_time: str         # "2025-01-15 10:30:00"
    end_time: str           # "2025-01-15 11:00:00"
```

**Adapter Call:**
```python
playback_data = MediaAdapter.build_playback_request(
    device_id="18270761136",
    start_time="2025-01-15 10:30:00",  # Still string!
    end_time="2025-01-15 11:00:00",    # Still string!
    channel=1,
    data_type=1  # Playback
)
```

---

### 4. **Media Adapter** (`adapters/media_adapter.py`)

**Current Implementation (❌ PROBLEM):**
```python
def build_playback_request(...):
    request = {
        "deviceId": device_id,           # ✅ Correct
        "channels": [channel],            # ✅ Correct
        "startTime": start_time,         # ❌ WRONG: String, should be Unix timestamp (int)
        "endTime": end_time,             # ❌ WRONG: String, should be Unix timestamp (int)
        "dataType": data_type            # ✅ Correct (1)
    }
    # ❌ MISSING: method, multiple, streamType
    return request
```

**What Gets Sent to Manufacturer API:**
```json
{
  "deviceId": "18270761136",
  "channels": [1],
  "startTime": "2025-01-15 10:30:00",  // ❌ String (wrong format)
  "endTime": "2025-01-15 11:00:00",    // ❌ String (wrong format)
  "dataType": 1
  // ❌ Missing: method, multiple, streamType
}
```

---

### 5. **Manufacturer API** (`/api/v1/media/playback`)

**Expected Format (from docs):**
```json
{
  "deviceId": "18270761136",        // ✅ String
  "channels": [1],                  // ✅ Array of int
  "dataType": 0,                   // ✅ int (0 or 1)
  "streamType": 0,                  // ❌ MISSING (0=main, 1=sub)
  "method": 0,                     // ❌ MISSING (0=normal, 1=FF, 2=keyframe rewind, 3=keyframe, 4=single frame)
  "multiple": 0,                   // ❌ MISSING (0=invalid, 1=1x, 2=2x, 3=4x, 4=8x, 5=16x)
  "startTime": 1715568599,         // ❌ Should be Unix timestamp (int seconds)
  "endTime": 1715568757            // ❌ Should be Unix timestamp (int seconds)
}
```

**Example Unix Timestamps:**
- `"2025-01-15 10:30:00"` → `1736932200` (Unix seconds)
- `"2025-01-15 11:00:00"` → `1736934000` (Unix seconds)

---

## ❌ **Current Issues:**

1. **Time Format Mismatch:**
   - Backend sends: `"2025-01-15 10:30:00"` (string)
   - Manufacturer expects: `1736932200` (int)`

2. **Missing Required Parameters:**
   - `method`: Required (0=normal playback)
   - `multiple`: Required (0=invalid, 1=1x speed)
   - `streamType`: Required (0=main stream, 1=sub stream)

3. **dataType Value:**
   - Currently sending: `data_type=1`
   - Docs say: `0 or 1 per docs` (need to verify which is correct)

---

## ✅ **What Needs to be Fixed:**

### Fix 1: Convert String Time to Unix Timestamp

In `adapters/media_adapter.py`:
```python
from datetime import datetime

def build_playback_request(...):
    # Convert "2025-01-15 10:30:00" to Unix timestamp
    start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    
    start_timestamp = int(start_dt.timestamp())
    end_timestamp = int(end_dt.timestamp())
    
    request = {
        "deviceId": device_id,
        "channels": [channel],
        "startTime": start_timestamp,  # ✅ Now int
        "endTime": end_timestamp,       # ✅ Now int
        "dataType": data_type,
        "streamType": stream_type or 0,  # ✅ Add default
        "method": 0,                      # ✅ Add default (normal playback)
        "multiple": 1                     # ✅ Add default (1x speed)
    }
    return request
```

### Fix 2: Update Router to Pass streamType

In `routers/media.py`:
```python
playback_data = MediaAdapter.build_playback_request(
    device_id=request.device_id,
    start_time=request.start_time,
    end_time=request.end_time,
    channel=request.channel,
    data_type=1,
    stream_type=0  # Add: 0=main stream, 1=sub stream
)
```

---

## 📊 **Summary of Parameters:**

| Parameter | Flutter → Backend | Backend → Manufacturer | Status |
|-----------|------------------|----------------------|--------|
| `device_id` / `deviceId` | ✅ String | ✅ String | ✅ String | ✅ |
| `channel` / `channels` | ✅ int | ✅ int | ✅ Array[int] | ✅ |
| `start_time` / `startTime` | ✅ String "YYYY-MM-DD HH:MM:SS" | ❌ String | ❌ Should be int (Unix) | ❌ |
| `end_time` / `endTime` | ✅ String "YYYY-MM-DD HH:MM:SS" | ❌ String | ❌ Should be int (Unix) | ❌ |
| `dataType` | N/A | ✅ int (1) | ✅ int | ✅ |
| `streamType` | N/A | ❌ Missing | ❌ Required (0 or 1) | ❌ |
| `method` | N/A | ❌ Missing | ❌ Required (0-4) | ❌ |
| `multiple` | N/A | ❌ Missing | ❌ Required (0-5) | ❌ |

---

## 🔧 **Next Steps:**

1. Fix `MediaAdapter.build_playback_request()` to convert time strings to Unix timestamps
2. Add missing parameters: `method`, `multiple`, `streamType`
3. Test with actual device to verify playback works

