# Data Forwarding Setup Guide

This document explains how to set up real-time data forwarding from the vendor to your backend.

## Overview

Instead of polling the vendor API repeatedly, the vendor pushes data to your backend when:
- Device sends GPS updates
- Device triggers an alarm
- Device status changes (ACC ON/OFF, Online/Offline)

This provides:
- **Real-time updates** (< 1 second latency)
- **Zero vendor API calls** from your app
- **Better battery life** (no constant polling)
- **No rate limit risk**

## Architecture

```
Devices → Vendor Server → Your Backend (/api/forwarding/receive)
                                ↓
                          Database (device_cache, alarms)
                                ↓
                          Mobile App (fetches from cache)
```

## Setup Steps

### Step 1: Run Database Migration

```bash
cd dashcam-api
python migrate_cache_tables.py
```

This creates:
- `device_cache` table - Stores latest GPS, ACC status, online status
- `alarms` table - Stores all alarm events

### Step 2: Deploy Backend

The new `/api/forwarding/receive` endpoint is automatically available after deployment.

```bash
git add .
git commit -m "feat: Add data forwarding support"
git push
```

### Step 3: Configure Vendor Data Forwarding

#### 3.1 Create Forwarding Platform

Call vendor API to register your backend URL:

```bash
POST https://vendor-api.com/api/v1/forwarding/platform/create
```

```json
{
    "name": "Dashcam App Backend",
    "protocol": 1,
    "httpConfig": {
        "url": "https://dashcam-api.onrender.com/api/forwarding/receive",
        "timeout": 30
    }
}
```

Save the returned `platformId`.

#### 3.2 Create Forwarding Policy

Configure which data to forward:

```bash
POST https://vendor-api.com/api/v1/forwarding/policy/create
```

```json
{
    "name": "All Data Forwarding",
    "platformId": YOUR_PLATFORM_ID,
    "configType": 1,
    "forwardCompanyId": YOUR_COMPANY_ID,
    "companyId": YOUR_COMPANY_ID,
    "configs": {
        "msgIds": [1, 2, 3],
        "gps": {
            "coordinateType": 1,
            "parseAdditionalInfo": true
        },
        "alarm": {
            "alarmTypes": [1, 2, 3, 4, 5, 6, 7, 8],
            "forwardingType": 2
        }
    }
}
```

Message Types (msgIds):
- `1` = GPS Location
- `2` = Alarms
- `3` = Device Status (ACC, Online/Offline)

### Step 4: Verify Data Forwarding

Check if data is being received:

```bash
curl https://dashcam-api.onrender.com/api/forwarding/stats
```

Expected response:
```json
{
    "devices": {
        "total": 5,
        "online": 3,
        "acc_on": 2
    },
    "alarms": {
        "total": 42,
        "unread": 5
    },
    "latest_update": "2024-01-03T15:30:00"
}
```

## API Endpoints

### Receive Forwarded Data (Vendor calls this)
```
POST /api/forwarding/receive
```

### Get Cached Device Status (App calls this)
```
GET /api/forwarding/device/{device_id}/status
```

### Get All Device Statuses (App calls this)
```
GET /api/forwarding/devices/status
```

### Get Device Alarms
```
GET /api/forwarding/device/{device_id}/alarms?limit=50&unread_only=false
```

### Acknowledge Alarm
```
POST /api/forwarding/device/{device_id}/alarms/{alarm_id}/acknowledge
```

### Get Forwarding Statistics
```
GET /api/forwarding/stats
```

## Flutter App Usage

The app now has new API methods:

```dart
// Get cached status for a single device (FAST!)
final status = await ApiService.getCachedDeviceStatus(deviceId);

// Get ALL device statuses in ONE call (most efficient)
final allStatuses = await ApiService.getAllCachedDeviceStatuses();

// Get device alarms
final alarms = await ApiService.getDeviceAlarms(deviceId, limit: 50);

// Acknowledge an alarm
await ApiService.acknowledgeAlarm(deviceId, alarmId);
```

## Gradual Migration Strategy

You can migrate gradually:

1. **Phase 1**: Enable data forwarding for GPS + Status
2. **Phase 2**: Enable alarm forwarding
3. **Phase 3**: Update app to use cached endpoints
4. **Phase 4**: Remove old polling logic

The app can fallback to vendor API if cache is empty:

```dart
try {
  return await ApiService.getCachedDeviceStatus(deviceId);
} catch (e) {
  if (e.toString().contains('DEVICE_NOT_CACHED')) {
    // Fallback to vendor API
    return await ApiService.getDeviceStates(deviceId);
  }
  rethrow;
}
```

## Monitoring

Check the forwarding stats regularly to ensure data is flowing:

```bash
# Check stats
curl https://dashcam-api.onrender.com/api/forwarding/stats

# Check specific device
curl https://dashcam-api.onrender.com/api/forwarding/device/YOUR_DEVICE_ID/status
```

## Troubleshooting

### No data in cache?
1. Check vendor forwarding platform is **enabled**
2. Check forwarding policy includes correct `msgIds`
3. Check backend logs for incoming requests
4. Verify backend URL is accessible from vendor

### Old data in cache?
1. Check vendor forwarding policy is active
2. Check devices are actually sending data
3. Look at `updated_at` timestamp in response

### Missing alarms?
1. Verify `alarmTypes` in forwarding policy
2. Check alarm level filtering
3. Query with `unread_only=false` to see all

