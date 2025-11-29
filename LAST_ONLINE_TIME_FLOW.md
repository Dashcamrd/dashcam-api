# Last Online Time: Complete Data Flow Explanation

This document explains in detail how the app collects, processes, and displays the "last online time" information that appears under the ACC status on the main screen.

## Overview

The app has **two independent data sources** for last online time:

1. **GPS Latest Endpoint** (`/gps/latest/{device_id}`) - Primary source when fetching GPS coordinates
2. **Device States Endpoint** (`/gps/states/{device_id}`) - Primary source when fetching ACC status

Both sources can provide last online time, and the Flutter app uses whichever is available.

---

## Data Flow Architecture

```
┌─────────────────┐
│  Vendor API     │  (Third-party manufacturer API)
│  - GPS V2       │
│  - Device States│
└────────┬────────┘
         │
         │ Raw JSON Response
         ▼
┌─────────────────┐
│  Adapter Layer  │  (adapters/gps_adapter.py, adapters/device_adapter.py)
│  - Parse vendor │
│  - Normalize    │
│  - Convert      │
└────────┬────────┘
         │
         │ DTO (Data Transfer Object)
         ▼
┌─────────────────┐
│  Router Layer   │  (routers/gps.py)
│  - HTTP endpoint│
│  - Field aliases│
│  - Error handling│
└────────┬────────┘
         │
         │ JSON Response (HTTP)
         ▼
┌─────────────────┐
│  Flutter API    │  (services/api_service.dart)
│  - HTTP request │
│  - JSON decode  │
└────────┬────────┘
         │
         │ Map<String, dynamic>
         ▼
┌─────────────────┐
│  UI Screen      │  (screens/main_screen.dart)
│  - Parse        │
│  - State update │
│  - Format       │
│  - Display      │
└─────────────────┘
```

---

## Source 1: GPS Latest Endpoint

### Step 1: Flutter Initiation
**File**: `lib/screens/main_screen.dart` (line 60, 182-269)

When the main screen loads:
```dart
@override
void initState() {
  _initializeWithGPS();  // Fetches GPS coordinates
  _fetchAccStatus();     // Fetches ACC status
}
```

The `_initializeWithGPS()` method calls:
```dart
final response = await ApiService.getLatestGps(widget.deviceId);
```

### Step 2: HTTP Request
**File**: `lib/services/api_service.dart`

```dart
static Future<Map<String, dynamic>> getLatestGps(String deviceId) async {
  final response = await http.get(
    Uri.parse("${ApiService.baseUrl}/gps/latest/$deviceId"),
    headers: {"Authorization": "Bearer $token"},
  );
  return jsonDecode(response.body);
}
```

**URL**: `GET https://dashcam-api.onrender.com/gps/latest/{device_id}`

### Step 3: Backend Router
**File**: `routers/gps.py` (line 101-163)

The router endpoint:
1. **Tries V2 API first** (dedicated endpoint, doesn't need time range):
   ```python
   result = manufacturer_api.get_latest_gps_v2({"deviceId": device_id})
   ```

2. **Falls back to V1** if V2 fails:
   ```python
   result = manufacturer_api.get_latest_gps({"deviceId": device_id})
   ```

3. **Parses response** using GPS adapter:
   ```python
   dto = GPSAdapter.parse_latest_gps_response(result, device_id, correlation_id)
   ```

4. **Adds field aliases** for Flutter compatibility:
   ```python
   response_data = dto.model_dump(by_alias=False)
   if dto.timestamp_ms is not None:
       response_data["lastOnlineTime"] = dto.timestamp_ms
       response_data["last_online_time_ms"] = dto.timestamp_ms
       response_data["last_online_time"] = dto.timestamp_ms
   ```

### Step 4: Vendor API Call
**File**: `services/manufacturer_api_service.py`

For V2:
- **Endpoint**: `POST /api/v2/gps/getLatestGPS`
- **Request**: `{"deviceIds": ["18270761136"]}`
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "list": [{
        "deviceId": "18270761136",
        "gps": {
          "latitude": 22.649954,
          "longitude": 114.148194,
          "speed": 359,
          "direction": 240,
          "time": 1726934400,        // ← GPS timestamp (Unix seconds)
          "altitude": 73
        },
        "lastOnlineTime": 1726934500  // ← Device last online time (Unix seconds)
      }]
    }
  }
  ```

### Step 5: Adapter Parsing
**File**: `adapters/gps_adapter.py` (line 85-125)

The adapter:
1. **Finds device in list**:
   ```python
   for device_item in device_list:
       if device_item.get("deviceId") == device_id:
   ```

2. **Extracts timestamp** (tries multiple sources):
   ```python
   # Try gps.time first, fallback to device_item.lastOnlineTime
   timestamp = gps_data.get("time") or device_item.get("lastOnlineTime")
   timestamp_ms = GPSAdapter.convert_timestamp_to_ms(timestamp)
   ```

3. **Converts timestamp** to milliseconds:
   ```python
   # BaseAdapter.convert_timestamp_to_ms()
   # If timestamp < 1e12, assumes seconds → multiply by 1000
   # If timestamp >= 1e12, assumes milliseconds → use as-is
   ```

4. **Returns DTO**:
   ```python
   return LatestGpsDto(
       deviceId=device_id,
       latitude=latitude,
       longitude=longitude,
       timestamp_ms=timestamp_ms  # ← In milliseconds
   )
   ```

### Step 6: Flutter Processing
**File**: `lib/screens/main_screen.dart` (line 182-237)

```dart
// Extract timestamp from multiple possible field names
final candidate = response['lastOnlineTime'] ??
    response['last_online_time_ms'] ??
    response['last_online_time'] ??
    response['timestamp'] ??
    response['time'];

// Parse timestamp (handles both seconds and milliseconds)
DateTime? lastOnlineTime = _parseApiTimestamp(candidate);

// Update state
setState(() {
  _lastGpsUpdateTime = lastOnlineTime;
  _lastUpdateTime = '$locationName • ${_formatLastOnline(lastOnlineTime)}';
});
```

**Timestamp parsing logic**:
```dart
DateTime? _parseApiTimestamp(dynamic value) {
  if (value is int) {
    if (value > 1000000000000)  // Already milliseconds
      return DateTime.fromMillisecondsSinceEpoch(value);
    return DateTime.fromMillisecondsSinceEpoch(value * 1000);  // Seconds → ms
  }
  // ... string parsing ...
}
```

---

## Source 2: Device States Endpoint (ACC Status)

### Step 1: Flutter Initiation
**File**: `lib/screens/main_screen.dart` (line 63, 114-170)

Called separately from GPS fetch:
```dart
Future<void> _fetchAccStatus() async {
  final response = await ApiService.getDeviceStates(widget.deviceId);
  // ...
}
```

### Step 2: HTTP Request
**File**: `lib/services/api_service.dart` (line 359-372)

```dart
static Future<Map<String, dynamic>> getDeviceStates(String deviceId) async {
  final response = await http.get(
    Uri.parse("${ApiService.baseUrl}/gps/states/$deviceId"),
    headers: {"Authorization": "Bearer $token"},
  );
  return jsonDecode(response.body);
}
```

**URL**: `GET https://dashcam-api.onrender.com/gps/states/{device_id}`

### Step 3: Backend Router
**File**: `routers/gps.py` (line 408-451)

```python
@router.get("/states/{device_id}")
def get_device_states(device_id: str, ...):
    # Call vendor API
    result = manufacturer_api.get_device_states({"deviceId": device_id})
    
    # Parse using adapter
    dto = DeviceAdapter.parse_device_states_response(result, device_id, correlation_id)
    
    # Return with multiple field name formats
    response_data = {
        "success": True,
        "device_id": dto.device_id,
        "acc_on": dto.acc_on,
        "acc_status": dto.acc_on,
    }
    
    # Add last online time in multiple formats
    if dto.last_online_time_ms is not None:
        response_data["last_online_time_ms"] = dto.last_online_time_ms
        response_data["lastOnlineTime"] = dto.last_online_time_ms
        response_data["last_online_time"] = dto.last_online_time_ms
        response_data["last_online"] = dto.last_online_time_ms
```

### Step 4: Vendor API Call
**File**: `services/manufacturer_api_service.py` (line 419-428)

- **Endpoint**: `POST /api/v1/device/states`
- **Request**: `{"deviceIds": ["18270761136"]}`
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "list": [{
        "deviceId": "18270761136",
        "state": 1,              // 0=offline, 1=online, 2=low power
        "accState": 1,            // 0=off, 1=on
        "lastOnlineTime": 1726934500  // ← Unix seconds
      }]
    }
  }
  ```

### Step 5: Adapter Parsing
**File**: `adapters/device_adapter.py` (line 97-122)

```python
# Try multiple field names
last_online = (
    device_state.get("lastOnlineTime") or
    device_state.get("last_online_time") or
    device_state.get("lastOnline") or
    device_state.get("last_online")
)

# Convert to milliseconds
last_online_time_ms = DeviceAdapter.convert_timestamp_to_ms(last_online)

# Return DTO
return AccStateDto(
    deviceId=device_id,
    acc_on=acc_on,
    last_online_time_ms=last_online_time_ms  # ← In milliseconds
)
```

### Step 6: Flutter Processing
**File**: `lib/screens/main_screen.dart` (line 114-162)

```dart
// Extract last online time from ACC status response
final lastOnlineCandidate = response['lastOnlineTime'] ??
    response['last_online_time_ms'] ??
    response['last_online_time'] ??
    response['last_online'] ??
    response['timestamp_ms'];

// Parse timestamp
final lastOnlineTime = _parseApiTimestamp(lastOnlineCandidate);

if (lastOnlineTime != null) {
  setState(() {
    _isAccOn = accStatus;
    _lastGpsUpdateTime = lastOnlineTime;  // ← Updates the same state variable!
  });
}
```

**Important**: Notice that both GPS and ACC endpoints update the **same state variable** `_lastGpsUpdateTime`. This means:
- If GPS fetch completes first, it sets the timestamp
- If ACC fetch completes later, it **overwrites** the GPS timestamp
- The last one to complete wins

---

## Display Logic

### Formatting
**File**: `lib/screens/main_screen.dart` (line 85-111)

The `_getLastUpdatedText()` method:
```dart
String _getLastUpdatedText() {
  if (_lastGpsUpdateTime == null) return 'Unknown';  // ← Shows "-Unknown-" if null
  
  final difference = DateTime.now().difference(_lastGpsUpdateTime!);
  
  if (difference.inMinutes < 1) return 'Just now';
  else if (difference.inMinutes < 60) return '${difference.inMinutes} minutes ago';
  else if (difference.inHours < 24) return '${difference.inHours} hours ago';
  else if (difference.inDays < 7) return '${difference.inDays} days ago';
  else return '${(difference.inDays / 7).floor()} weeks ago';
}
```

### UI Rendering
**File**: `lib/screens/main_screen.dart` (line 592-599)

```dart
Text(
  _getLastUpdatedText(),  // ← Calls formatting method
  style: const TextStyle(
    fontSize: 14,
    color: Color(0xFF6B7280),
  ),
),
```

This text appears **under the ACC status** in the device info section.

---

## Key Conversions

### Timestamp Format Conversion

| Format | Vendor API | Adapter Input | Adapter Output | Flutter Receives | Flutter Stores |
|--------|-----------|--------------|----------------|------------------|----------------|
| Unix Seconds | `1726934500` | `1726934500` | `1726934500000` | `1726934500000` | `DateTime` object |
| Unix Milliseconds | `1726934500000` | `1726934500000` | `1726934500000` | `1726934500000` | `DateTime` object |

**Conversion Logic**:
```python
# BaseAdapter.convert_timestamp_to_ms()
if timestamp < 1_000_000_000_000:  # Less than year 2286 in ms
    return timestamp * 1000  # Assume seconds, convert to ms
else:
    return timestamp  # Already milliseconds
```

### Field Name Mapping

The backend returns **multiple field names** to ensure Flutter finds it:

**Backend Response**:
```json
{
  "success": true,
  "last_online_time_ms": 1726934500000,
  "lastOnlineTime": 1726934500000,
  "last_online_time": 1726934500000,
  "last_online": 1726934500000
}
```

**Flutter tries all of them**:
```dart
final candidate = response['lastOnlineTime'] ??
    response['last_online_time_ms'] ??
    response['last_online_time'] ??
    response['last_online'];
```

---

## Race Condition Handling

Both GPS and ACC endpoints can provide last online time. The current implementation:

1. **Both endpoints update** `_lastGpsUpdateTime`
2. **Last one to complete wins** (overwrites previous value)
3. **ACC endpoint typically completes faster** (simpler request), so it usually sets the final value

### Potential Issue

If GPS fetch takes longer than ACC fetch:
- ACC sets `_lastGpsUpdateTime` first
- GPS fetch completes later and overwrites it
- User sees GPS timestamp, not ACC timestamp

**However**, in practice:
- GPS endpoint has `lastOnlineTime` in V2 response
- ACC endpoint has `lastOnlineTime` in device states response
- Both should be similar (device last online time)

---

## Error Handling

### Backend Level

1. **Vendor API errors**: Returns graceful error response
2. **Missing data**: Returns `success: false` with message
3. **Parsing errors**: Returns DTO with `last_online_time_ms: None`

### Flutter Level

1. **Null check**: `if (_lastGpsUpdateTime == null) return 'Unknown';`
2. **Parse failures**: Falls back to showing "Unknown"
3. **Missing fields**: Logs all available keys for debugging

---

## Debugging Flow

When debugging "Unknown" display:

1. **Check Flutter console** for:
   - `🔍 Last online candidate from ACC response: ...`
   - `🔍 Full ACC response keys: ...`
   - `⚠️ No last online time found in ACC response`

2. **Check backend logs** for:
   - `[correlation_id] Extracted lastOnlineTime: ...`
   - `[correlation_id] Converted last_online_time_ms: ...`
   - `[correlation_id] Returning last online time: ...`

3. **Check vendor API response**:
   - Does `data.list[].lastOnlineTime` exist?
   - Is timestamp in seconds or milliseconds?
   - Is timestamp valid (not null, not 0)?

---

## Summary

1. **Two sources**: GPS endpoint and Device States endpoint
2. **Backend normalizes**: Converts seconds→milliseconds, adds field aliases
3. **Flutter extracts**: Tries multiple field names, parses timestamp
4. **State management**: Both endpoints update same `_lastGpsUpdateTime` variable
5. **Display**: Formats as relative time ("2 hours ago") or "Unknown" if null
6. **Error handling**: Graceful fallbacks at every layer

The key to fixing the "Unknown" issue is ensuring:
- Vendor API returns `lastOnlineTime` field
- Adapter correctly extracts and converts it
- Backend includes it in response with multiple field names
- Flutter successfully parses it and updates state

