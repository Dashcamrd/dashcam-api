# Track Playback Data Flow & Endpoints

## 🔄 Complete Data Flow

```
Flutter App → Backend API → Manufacturer API → GPS Adapter → Flutter App
```

## 📍 Endpoints Used

### 1. Flutter App → Backend API

**Endpoint:** `POST /gps/history`

**Location:** `lib/services/api_service.dart` → `getTrackHistory()`

**Request:**
```dart
POST https://dashcam-api.onrender.com/gps/history
Headers:
  Authorization: Bearer <token>
  Content-Type: application/json

Body:
{
  "device_id": "cam001",
  "date": "2024-01-15",  // YYYY-MM-DD format
  "start_time": null,    // Optional, for time range
  "end_time": null       // Optional, for time range
}
```

### 2. Backend API → Manufacturer API

**Router:** `routers/gps.py` → `get_detailed_track_history()`

**Endpoint Name:** `gps_query_detailed_track_v1`

**Location:** `services/manufacturer_api_service.py` → `query_detailed_track()`

**Manufacturer API Request:**
```
POST http://180.167.106.70:9337/api/v1/gps/search
Headers:
  X-Token: <manufacturer_token>
  Content-Type: application/json

Body:
{
  "deviceId": "cam001",
  "startTime": 1704067200,  // Unix timestamp in seconds (start of day)
  "endTime": 1704153600     // Unix timestamp in seconds (end of day)
}
```

### 3. Manufacturer API Response → GPS Adapter

**Adapter:** `adapters/gps_adapter.py` → `parse_track_history_response()`

**Response Path:** `data.points` (from YAML config)

**Processing:**
- Extracts GPS points array
- Converts raw coordinates (1e6 format) → decimal degrees
- Converts timestamps (seconds/ms) → milliseconds
- Converts speed to km/h
- Maps to `TrackPlaybackDto`

### 4. GPS Adapter → Backend Response

**DTO:** `models/dto.py` → `TrackPlaybackDto`

**Response to Flutter:**
```json
{
  "success": true,
  "device_id": "cam001",
  "start_time_ms": 1736966400000,
  "end_time_ms": 1737052799000,
  "points": [
    {
      "latitude": 5.290439,
      "longitude": 100.291992,
      "timestamp_ms": 1736967000000,
      "speed_kmh": 65.5,
      "direction_deg": 180.0
    },
    // ... more points
  ]
}
```

### 5. Flutter App Processing

**Location:** `lib/screens/track_playback_screen.dart` → `_loadTrackData()`

**Parsing:**
- Extracts `points` array from response
- Creates `TrackPoint` objects
- Displays on map and in list
- Enables playback controls

## 📊 Configuration

### YAML Config
**File:** `config/manufacturer_api.yaml`

```yaml
gps_query_detailed_track_v1:
  path: /api/v1/gps/queryDetailedTrack
  method: POST
  timeout: 60  # GPS searches can take longer
  retries: 2   # Fewer retries for time-consuming operations
  request:
    required: [deviceId, startTime, endTime]
  response:
    data_path: data.points
```

### Adapter Mapping

**Raw Vendor Response:**
```json
{
  "code": 200,
  "data": {
    "gpsInfo": [
      {
        "latitude": 5290439,      // Raw: multiplied by 1e6, divide to get decimal
        "longitude": 100291992,   // Raw: multiplied by 1e6, divide to get decimal
        "time": 1736967,          // Unix seconds
        "speed": 655,              // May be in 0.1 km/h units or raw
        "direction": 180
      }
    ]
  }
}
```

**After Adapter (DTO):**
```json
{
  "latitude": 5.290439,           // Converted to decimal
  "longitude": 100.291992,        // Converted to decimal
  "timestamp_ms": 1736967000000,  // Converted to milliseconds
  "speed_kmh": 65.5,              // Normalized to km/h
  "direction_deg": 180.0
}
```

## 🔑 Key Components

### Backend Router
- **File:** `routers/gps.py`
- **Function:** `get_detailed_track_history()`
- **Line:** ~164-198
- **Features:**
  - User authentication check
  - Device access verification
  - Correlation ID generation
  - Adapter integration

### GPS Adapter
- **File:** `adapters/gps_adapter.py`
- **Function:** `parse_track_history_response()`
- **Line:** ~126-227
- **Features:**
  - Config-driven response parsing
  - Coordinate conversion (raw → decimal)
  - Timestamp normalization (seconds → ms)
  - Speed normalization
  - Error handling with correlation IDs

### Manufacturer API Service
- **File:** `services/manufacturer_api_service.py`
- **Method:** `query_detailed_track()`
- **Endpoint:** `gps_query_detailed_track_v1`
- **Features:**
  - Token management
  - Rate limiting
  - Retry logic
  - Request building from config

## 🎯 Summary

**Endpoint Chain:**
1. **Flutter:** `POST /gps/history` (backend)
2. **Backend Router:** `routers/gps.py` → `get_detailed_track_history()`
3. **Service:** `manufacturer_api.query_detailed_track()`
4. **Vendor API:** `POST /api/v1/gps/queryDetailedTrack`
5. **Adapter:** `GPSAdapter.parse_track_history_response()`
6. **Response:** `TrackPlaybackDto` → JSON → Flutter

**Data Transformations:**
- ✅ Raw coordinates (1e6) → Decimal degrees
- ✅ Timestamps → Milliseconds
- ✅ Speed → km/h
- ✅ Vendor field names → Stable DTO fields

## 📝 Notes

- **Date Format:** Backend expects `YYYY-MM-DD` (e.g., "2024-01-15")
- **Time Range:** Optional `start_time` and `end_time` for filtering
- **Full Day:** If no time range provided, returns all points for the day
- **Correlation IDs:** All requests traceable via `[correlation_id]` in logs
- **Error Handling:** Graceful fallbacks if data missing or invalid

