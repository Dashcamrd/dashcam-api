# Timezone Handling in Video Playback

## ⚠️ **Critical Issue Found & Fixed**

### **Problem:**
The original code used **server's local timezone** (UTC+3) when converting timestamps, causing incorrect time calculations.

### **Example of the Problem:**

**Before Fix:**
```python
# Server timezone: UTC+3
start_dt = datetime.strptime("2025-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
# Python assumes this is 10:30:00 in UTC+3 (server's local timezone)
timestamp = int(start_dt.timestamp())
# Result: 1736926200 (which is 07:30:00 UTC - 3 hours off!)
```

**After Fix:**
```python
# Explicitly use UTC
start_dt = datetime.strptime("2025-01-15 10:30:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
# Now explicitly 10:30:00 UTC
timestamp = int(start_dt.timestamp())
# Result: 1736937000 (which is 10:30:00 UTC - correct!)
```

---

## ✅ **Current Implementation**

### **Backend (Python):**
```python
from datetime import datetime, timezone

# Parse time string and explicitly set to UTC
start_dt = datetime.strptime("2025-01-15 10:30:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
start_timestamp = int(start_dt.timestamp())
```

**Timezone Used:** **UTC (Coordinated Universal Time)**

### **Flutter (Dart):**
```dart
String _formatDateTime(DateTime date, TimeOfDay time) {
  return "${date.year}-${date.month}-${date.day} ${time.hour}:${time.minute}:00";
}
```

**Current Behavior:** Flutter sends time as-is (user's local time selection)

---

## 🔄 **Time Flow:**

1. **User selects:** `10:30 AM` in their local timezone (e.g., UTC+3)
2. **Flutter sends:** `"2025-01-15 10:30:00"` (string, no timezone info)
3. **Backend interprets:** `"2025-01-15 10:30:00"` as **UTC time**
4. **Backend converts:** To Unix timestamp: `1736937000`
5. **Manufacturer API receives:** Unix timestamp (always UTC)

---

## ⚠️ **Important Note:**

**Current behavior:** The time string from Flutter is interpreted as **UTC time**.

**Example:**
- User in UTC+3 selects: `10:30 AM` (local time)
- Flutter sends: `"2025-01-15 10:30:00"`
- Backend interprets as: `10:30:00 UTC` (not `10:30:00 UTC+3`)
- **Result:** User's local `10:30 AM` becomes `10:30 AM UTC` (which is `1:30 PM` in UTC+3)

---

## 🎯 **Options for Better Timezone Handling:**

### **Option 1: Flutter Converts to UTC (Recommended)**
Convert user's local time to UTC before sending:

```dart
String _formatDateTime(DateTime date, TimeOfDay time) {
  // Combine date and time in local timezone
  final localDateTime = DateTime(
    date.year, date.month, date.day,
    time.hour, time.minute, 0
  );
  
  // Convert to UTC
  final utcDateTime = localDateTime.toUtc();
  
  // Format as string
  return "${utcDateTime.year.toString().padLeft(4, '0')}-"
       "${utcDateTime.month.toString().padLeft(2, '0')}-"
       "${utcDateTime.day.toString().padLeft(2, '0')} "
       "${utcDateTime.hour.toString().padLeft(2, '0')}:"
       "${utcDateTime.minute.toString().padLeft(2, '0')}:00";
}
```

**Example:**
- User selects: `10:30 AM` (UTC+3 local time)
- Flutter converts: `10:30 AM UTC+3` → `07:30 AM UTC`
- Flutter sends: `"2025-01-15 07:30:00"`
- Backend interprets: `07:30:00 UTC` ✅

### **Option 2: Send Timezone Info**
Include timezone offset in the request:

```dart
// Flutter sends timezone offset
{
  "start_time": "2025-01-15 10:30:00",
  "timezone_offset": 3  // UTC+3
}
```

```python
# Backend adjusts based on timezone
from datetime import datetime, timezone, timedelta

dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
tz_offset = timedelta(hours=timezone_offset)
dt_utc = dt - tz_offset  # Convert to UTC
timestamp = int(dt_utc.timestamp())
```

### **Option 3: Document Current Behavior**
Keep current implementation but document that times are expected in UTC.

---

## 📊 **Comparison:**

| User Local Time | Current (UTC) | Option 1 (Convert) | Option 2 (TZ Info) |
|----------------|---------------|-------------------|-------------------|
| User selects: `10:30 AM` (UTC+3) | Sends: `"10:30:00"`<br>Backend: `10:30 UTC`<br>Actual: `1:30 PM` local ❌ | Sends: `"07:30:00"`<br>Backend: `07:30 UTC`<br>Actual: `10:30 AM` local ✅ | Sends: `"10:30:00"` + `offset: 3`<br>Backend: `07:30 UTC`<br>Actual: `10:30 AM` local ✅ |

---

## ✅ **Recommendation:**

**Implement Option 1** - Convert to UTC in Flutter before sending. This ensures:
- User's local time selection is correctly interpreted
- No timezone confusion
- Consistent behavior across all users

---

## 🔧 **Current Status:**

- ✅ **Backend:** Fixed to use UTC explicitly
- ⚠️ **Flutter:** Still sends local time (needs conversion)
- 📝 **Documentation:** This document explains the issue

---

## 📝 **Summary:**

**Question:** "Which GMT/timezone is used when converting to Unix timestamp?"

**Answer:** 
- **Before fix:** Server's local timezone (UTC+3) - **WRONG** ❌
- **After fix:** **UTC (Coordinated Universal Time)** - **CORRECT** ✅

**Note:** Flutter should convert user's local time to UTC before sending to ensure accurate playback time selection.

