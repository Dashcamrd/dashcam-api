# Time Conversion Flow: User Selection → Unix Timestamp

## 📋 Complete Conversion Process

### **Step 1: User Selects Date & Time (Flutter)**

**User Input:**
- **Date:** Selected via `showDatePicker()` → `DateTime` object
  - Example: `DateTime(2025, 1, 15)` → January 15, 2025
- **Start Time:** Selected via `showTimePicker()` → `TimeOfDay` object
  - Example: `TimeOfDay(hour: 10, minute: 30)` → 10:30 AM
- **End Time:** Selected via `showTimePicker()` → `TimeOfDay` object
  - Example: `TimeOfDay(hour: 11, minute: 0)` → 11:00 AM

**State Variables:**
```dart
DateTime _selectedDate = DateTime.now();        // e.g., 2025-01-15
TimeOfDay _startTime = TimeOfDay(hour: 10, minute: 30);  // 10:30
TimeOfDay _endTime = TimeOfDay(hour: 11, minute: 0);    // 11:00
```

---

### **Step 2: Flutter Formats to String**

**Function:** `_formatDateTime(DateTime date, TimeOfDay time)`

**Code:**
```dart
String _formatDateTime(DateTime date, TimeOfDay time) {
  return "${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}:00";
}
```

**Conversion:**
```dart
// Input:
_selectedDate = DateTime(2025, 1, 15)  // 2025-01-15
_startTime = TimeOfDay(hour: 10, minute: 30)  // 10:30

// Output:
startTimeStr = "2025-01-15 10:30:00"  // String format
```

**Example Conversions:**
| DateTime | TimeOfDay | Formatted String |
|----------|-----------|------------------|
| `DateTime(2025, 1, 15)` | `TimeOfDay(10, 30)` | `"2025-01-15 10:30:00"` |
| `DateTime(2025, 1, 15)` | `TimeOfDay(11, 0)` | `"2025-01-15 11:00:00"` |
| `DateTime(2025, 2, 28)` | `TimeOfDay(14, 45)` | `"2025-02-28 14:45:00"` |

---

### **Step 3: Flutter Sends String to Backend**

**API Call:**
```dart
final response = await ApiService.startPlayback(
  deviceId: "18270761136",
  channel: 1,
  startTime: "2025-01-15 10:30:00",  // String
  endTime: "2025-01-15 11:00:00",    // String
);
```

**HTTP Request:**
```json
{
  "device_id": "18270761136",
  "channel": 1,
  "start_time": "2025-01-15 10:30:00",  // String
  "end_time": "2025-01-15 11:00:00"      // String
}
```

---

### **Step 4: Backend Receives String**

**Backend Router (`routers/media.py`):**
```python
class PlaybackRequest(BaseModel):
    device_id: str
    channel: Optional[int] = 1
    start_time: str  # "2025-01-15 10:30:00"
    end_time: str    # "2025-01-15 11:00:00"
```

**Adapter Call:**
```python
playback_data = MediaAdapter.build_playback_request(
    device_id="18270761136",
    start_time="2025-01-15 10:30:00",  # String
    end_time="2025-01-15 11:00:00",    # String
    channel=1,
    data_type=1,
    stream_type=0
)
```

---

### **Step 5: Backend Converts String to Unix Timestamp**

**Function:** `MediaAdapter.build_playback_request()`

**Conversion Code:**
```python
from datetime import datetime

# Parse string to datetime object
start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
# start_dt = datetime(2025, 1, 15, 10, 30, 0)

# Convert datetime to Unix timestamp (seconds since epoch)
start_timestamp = int(start_dt.timestamp())
# start_timestamp = 1736932200
```

**Complete Conversion:**
```python
# Input strings
start_time = "2025-01-15 10:30:00"
end_time = "2025-01-15 11:00:00"

# Step 1: Parse string to datetime
start_dt = datetime.strptime("2025-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
# → datetime(2025, 1, 15, 10, 30, 0)

end_dt = datetime.strptime("2025-01-15 11:00:00", "%Y-%m-%d %H:%M:%S")
# → datetime(2025, 1, 15, 11, 0, 0)

# Step 2: Convert to Unix timestamp (seconds)
start_timestamp = int(start_dt.timestamp())
# → 1736932200

end_timestamp = int(end_dt.timestamp())
# → 1736934000
```

---

### **Step 6: Backend Sends Unix Timestamp to Manufacturer API**

**Final Request:**
```json
{
  "deviceId": "18270761136",
  "channels": [1],
  "startTime": 1736932200,  // Unix timestamp (int)
  "endTime": 1736934000,    // Unix timestamp (int)
  "dataType": 1,
  "streamType": 0,
  "method": 0,
  "multiple": 1
}
```

---

## 🔢 Conversion Examples

### **Example 1:**
| Step | Value | Type |
|------|-------|------|
| User selects | Date: Jan 15, 2025<br>Time: 10:30 AM | `DateTime` + `TimeOfDay` |
| Flutter formats | `"2025-01-15 10:30:00"` | `String` |
| Backend parses | `datetime(2025, 1, 15, 10, 30, 0)` | `datetime` |
| Backend converts | `1736932200` | `int` (Unix seconds) |

### **Example 2:**
| Step | Value | Type |
|------|-------|------|
| User selects | Date: Feb 28, 2025<br>Time: 2:45 PM | `DateTime` + `TimeOfDay` |
| Flutter formats | `"2025-02-28 14:45:00"` | `String` |
| Backend parses | `datetime(2025, 2, 28, 14, 45, 0)` | `datetime` |
| Backend converts | `1738157100` | `int` (Unix seconds) |

---

## 📊 Conversion Formula

**Python Conversion:**
```python
from datetime import datetime

# String → datetime → Unix timestamp
time_string = "2025-01-15 10:30:00"
dt = datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S")
unix_timestamp = int(dt.timestamp())
```

**What `.timestamp()` does:**
- Returns seconds since Unix epoch (January 1, 1970, 00:00:00 UTC)
- `int()` converts float to integer (removes milliseconds)

**Verification:**
```python
from datetime import datetime

# Convert back to verify
timestamp = 1736932200
dt = datetime.fromtimestamp(timestamp)
print(dt.strftime("%Y-%m-%d %H:%M:%S"))
# Output: "2025-01-15 10:30:00" ✅
```

---

## 🎯 Summary

1. **User selects:** `DateTime` + `TimeOfDay` objects
2. **Flutter formats:** `"YYYY-MM-DD HH:MM:SS"` string
3. **Backend receives:** String format
4. **Backend parses:** `datetime.strptime()` → `datetime` object
5. **Backend converts:** `.timestamp()` → Unix timestamp (int seconds)
6. **Manufacturer API receives:** Unix timestamp (int)

**Key Functions:**
- **Flutter:** `_formatDateTime()` - Combines date and time into string
- **Backend:** `datetime.strptime()` - Parses string to datetime
- **Backend:** `.timestamp()` - Converts datetime to Unix timestamp

