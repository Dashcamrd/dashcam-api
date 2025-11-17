# 🐛 Debugging Guide - How to Share Logs with AI Assistant

## Quick Ways to View Logs

### 1. **Render Dashboard (Production)**
If your API is deployed on Render:
1. Go to https://dashboard.render.com
2. Click on your service (e.g., "dashcam-api")
3. Click the **"Logs"** tab
4. Copy relevant log lines and paste them in chat

### 2. **Local Server (Development)**
If running locally:
```bash
# Option A: Check terminal where you run 'python start.py'
# All logs appear there in real-time

# Option B: Use the helper script
./view_recent_logs.sh

# Option C: View log files directly
tail -50 server.log
# or
tail -50 server-8001.log

# Option D: Follow logs in real-time (like tail -f)
tail -f server.log
```

### 3. **Flutter App Logs**
- **VS Code**: View → Output → Select "Debug Console"
- **Android Studio**: View → Tool Windows → Logcat (for Android)
- **Terminal**: If running `flutter run`, logs appear in terminal

## What to Look For

When debugging, look for:

1. **Correlation IDs**: `[a1b2c3d4]` - Unique IDs for each request
2. **Error messages**: Lines starting with `❌`
3. **API requests**: Lines starting with `📡`
4. **Responses**: Lines showing vendor API responses

## How to Share Logs

### Method 1: Copy Specific Lines
1. Find relevant log lines (look for correlation ID or error)
2. Copy them (Cmd+C / Ctrl+C)
3. Paste here in chat

### Method 2: Share Correlation ID
If you see an error, look for the correlation ID:
```
[5zg7x] ❌ API request failed: 404
```
Then share that ID and I can help you find related logs.

### Method 3: Share Last N Lines
```bash
# Get last 100 lines
tail -100 server.log > recent_logs.txt
# Then share the file or paste contents
```

## Quick Debug Commands

```bash
# View recent errors
grep -i "error\|❌\|failed" server.log | tail -20

# Search for specific correlation ID
grep "[5zg7x]" server.log

# Find all GPS-related requests
grep "gps\|GPS" server.log | tail -30

# Find 404 errors
grep "404" server.log | tail -20
```

## Common Issues & What to Share

### "404 page not found"
Share:
- The correlation ID
- The log line showing the URL being called
- The response body

### "No GPS data found"
Share:
- Device ID
- The date/time range being requested
- Vendor API response

### "Authentication failed"
Share:
- Login attempt logs
- Token refresh logs
- Any 401/403 errors

## Tips

1. **Timestamps matter**: Include timestamps when sharing logs
2. **Correlation IDs**: Always include the correlation ID for specific requests
3. **Full context**: Share a few lines before and after the error
4. **Sensitive data**: Mask passwords/tokens before sharing

---

**Need help?** Just run `./view_recent_logs.sh` and share the output!

