# Track Playback Data Flow - Dynamic vs Static

## 📊 Data Sources: All Dynamic (User-Driven)

All parameters (`deviceId`, `startTime`, `endTime`) are **100% dynamic** and based on:
1. **User's selected device** (from device list)
2. **User's selected date** (from calendar picker)
3. **User's timezone/current day**

## 🔄 Complete Data Flow

### Step 1: User Selects Device
**Location:** Device list screen or map screen
```dart
// User taps on a device, then navigates to track playback
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => TrackPlaybackScreen(deviceId: "cam001"), // ← Dynamic device ID
  ),
);
```

**Device ID Source:**
- ✅ From user's device list (authenticated user)
- ✅ User can only see devices assigned to them
- ✅ Not hardcoded - comes from `/gps/devices` endpoint

### Step 2: User Selects Date
**Location:** `track_playback_screen.dart` → Calendar picker
```dart
DateTime _selectedDate = DateTime.now();  // ← Defaults to today, but user can change

// User taps calendar button
CalendarDatePicker(
  initialDate: _selectedDate,
  firstDate: DateTime.now().subtract(const Duration(days: 365)), // Last year
  lastDate: DateTime.now(),  // Up to today
  onDateChanged: (date) {
    setState(() {
      _selectedDate = date;  // ← User-selected date
      _showCalendar = false;
    });
    _loadTrackData();  // Reload data for new date
  },
)
```

**Date Source:**
- ✅ User selects from calendar picker
- ✅ Defaults to current date (`DateTime.now()`)
- ✅ Can select any date in the past year
- ✅ Format: `YYYY-MM-DD` (e.g., "2024-01-15")

### Step 3: Flutter App → Backend API
**Location:** `lib/services/api_service.dart` → `getTrackHistory()`
```dart
final dateStr = DateFormat('yyyy-MM-dd').format(_selectedDate);  // ← User's selected date

final response = await ApiService.getTrackHistory(
  deviceId: widget.deviceId,  // ← Device from navigation
  date: dateStr,              // ← Date from calendar
  // startTime/endTime are null = full day
);
```

**Request to Backend:**
```json
POST /gps/history
{
  "device_id": "cam001",      // ← From user's device selection
  "date": "2024-01-15",       // ← From user's calendar selection
  "start_time": null,         // Optional time range
  "end_time": null            // Optional time range
}
```

### Step 4: Backend Converts Date → Timestamps
**Location:** `routers/gps.py` → `get_detailed_track_history()`
```python
# User's selected date: "2024-01-15"
date_obj = datetime.strptime(request.date, "%Y-%m-%d")

# Convert to Unix timestamps
start_datetime = datetime.combine(date_obj.date(), time.min)  # 00:00:00
start_time = int(start_datetime.timestamp())                  # ← Dynamic start of day

end_datetime = datetime.combine(date_obj.date(), time.max)    # 23:59:59
end_time = int(end_datetime.timestamp())                      # ← Dynamic end of day

# If user provided start_time/end_time (e.g., "10:00:00"), combine with date
if request.start_time:
    time_obj = datetime.strptime(request.start_time, "%H:%M:%S").time()
    start_datetime = datetime.combine(date_obj.date(), time_obj)
    start_time = int(start_datetime.timestamp())  # ← Dynamic based on user time selection
```

**Result:**
```python
track_data = {
    "deviceId": "cam001",        # ← From user's device
    "startTime": 1704067200,     # ← Start of user's selected day (00:00:00)
    "endTime": 1704153599        # ← End of user's selected day (23:59:59)
}
```

### Step 5: Backend → Vendor API
**Location:** `services/manufacturer_api_service.py` → `query_detailed_track()`
```python
POST http://180.167.106.70:9337/api/v1/gps/search
Headers:
  X-Token: <manufacturer_token>
Body:
{
  "deviceId": "cam001",        # ← User's selected device
  "startTime": 1704067200,     # ← Start of user's selected day
  "endTime": 1704153599        # ← End of user's selected day
}
```

## 🎯 Summary: All Dynamic

| Parameter | Source | Dynamic? |
|-----------|--------|----------|
| **deviceId** | User selects device from their device list | ✅ **100% Dynamic** |
| **date** | User selects from calendar picker | ✅ **100% Dynamic** |
| **startTime** | Calculated from selected date (00:00:00) | ✅ **100% Dynamic** |
| **endTime** | Calculated from selected date (23:59:59) | ✅ **100% Dynamic** |

## 📱 User Flow Example

1. **User opens app** → Logs in → Sees device list
2. **User taps device** → "cam001" (their assigned device)
3. **Navigates to Track Playback** → `deviceId = "cam001"` passed
4. **Sees today's date** → Can change via calendar
5. **Selects date** → "2024-01-15" (from calendar)
6. **App loads data** → Requests GPS data for that device + date
7. **Backend calculates** → Start: `2024-01-15 00:00:00`, End: `2024-01-15 23:59:59`
8. **Vendor API called** → With deviceId + timestamps
9. **Data displayed** → Track points for that specific device + day

## 🔒 Security & Access Control

**Device Access:**
- User can only access devices assigned to them
- Backend verifies: `verify_device_access(device_id, current_user)`
- Prevents unauthorized device access

**Date Range:**
- User can select any date (up to 1 year ago)
- Limited to dates with available GPS data
- No future dates allowed

## 💡 No Hardcoded/Dummy Data

**Everything is dynamic:**
- ❌ No hardcoded device IDs
- ❌ No hardcoded dates
- ❌ No dummy/mock data (unless device has no GPS data)
- ✅ All based on user selection and authentication

## 🧪 Example Scenarios

### Scenario 1: User Selects Today
```
deviceId: "cam001" (user's device)
date: "2024-01-31" (today)
→ startTime: 1704067200 (today 00:00:00)
→ endTime: 1704153599 (today 23:59:59)
```

### Scenario 2: User Selects Yesterday
```
deviceId: "cam002" (different device)
date: "2024-01-30" (yesterday)
→ startTime: 1703980800 (yesterday 00:00:00)
→ endTime: 1704067199 (yesterday 23:59:59)
```

### Scenario 3: User Selects Last Week
```
deviceId: "cam001"
date: "2024-01-24" (last week)
→ startTime: 1703376000 (that day 00:00:00)
→ endTime: 1703462399 (that day 23:59:59)
```

All parameters change based on user's selections!

---

**Answer:** ✅ **All data is dynamic** - based on user's device selection and date picker choice.

