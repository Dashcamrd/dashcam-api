# 🧪 Testing Flutter App with Production API

## Pre-Test Checklist

Before running the Flutter app:

- [x] API deployed to Render
- [x] Flutter app configured with production URL: `https://dashcam-api.onrender.com`
- [ ] API health check passes
- [ ] Authentication endpoint working

## Quick API Verification

**Check if API is accessible:**
```bash
curl https://dashcam-api.onrender.com/health
```
Expected: `{"status":"ok"}`

**Test authentication:**
```bash
curl -X POST https://dashcam-api.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"invoice_no":"INV2024001","password":"customer123"}'
```

## Running the Flutter App

### Option 1: VS Code / Cursor

1. **Open Flutter project:**
   ```bash
   cd /Users/fahadalmanee/flutterProject/dashcamapp
   ```

2. **Run the app:**
   - Press `F5` or click "Run" button
   - Or use terminal: `flutter run`

### Option 2: Terminal

```bash
cd /Users/fahadalmanee/flutterProject/dashcamapp
flutter run
```

## What to Test

### 1. ✅ Login
- Use test credentials: `INV2024001` / `customer123`
- Should successfully authenticate
- Token should be saved

### 2. ✅ Device List
- Should load devices assigned to user
- Should show device status

### 3. ✅ GPS Data
- Navigate to GPS/map screens
- Should fetch latest GPS data
- Should display location on map

### 4. ✅ Live Video
- Test video preview if available
- Should connect to production API

### 5. ✅ Track Playback
- Test historical GPS track
- Should load track data

## Common Issues & Fixes

### Issue: "Connection refused" or timeout

**Possible causes:**
- API not deployed yet
- API sleeping (Render free tier)
- Wrong URL

**Fix:**
1. Check Render dashboard - service should be "Live"
2. Wake up service: `curl https://dashcam-api.onrender.com/health` (first request may be slow)
3. Verify URL in `api_service.dart` is correct

### Issue: "401 Unauthorized"

**Possible causes:**
- Invalid credentials
- Token expired
- User doesn't exist in database

**Fix:**
1. Create test user via `/admin/users` endpoint
2. Or use existing credentials
3. Check database for user

### Issue: "No GPS data found"

**Possible causes:**
- Device not assigned to user
- Device has no GPS data
- Manufacturer API credentials incorrect

**Fix:**
1. Assign device to user via admin panel
2. Check if device has GPS data in manufacturer system
3. Verify manufacturer API credentials in Render env vars

### Issue: Slow API responses

**Possible causes:**
- Render free tier cold start (~30s)
- First request after idle period
- Network latency

**Fix:**
- First request may be slow (cold start)
- Subsequent requests should be faster
- Consider upgrading Render plan if needed

## Expected Behavior

### First Launch (Cold Start)
- May take 30+ seconds for first API call
- This is normal for Render free tier
- Subsequent calls should be fast

### After Login
- Token saved locally
- Can make authenticated requests
- Device list should load

### GPS Features
- Should fetch latest GPS location
- Map should display location
- Should show relative time ("X minutes ago")

## Verification Steps

1. **API Health:**
   ```bash
   curl https://dashcam-api.onrender.com/health
   ```

2. **API Docs:**
   - Visit: `https://dashcam-api.onrender.com/docs`
   - Should show Swagger UI

3. **Flutter App:**
   - Run app
   - Test login
   - Verify API calls succeed
   - Check console/logs for errors

## Debug Tips

### Check Flutter Console
- Look for HTTP errors
- Check response codes
- Verify API base URL is correct

### Check API Logs
- Go to Render Dashboard → Logs
- Look for correlation IDs: `[xxxx]`
- Check for errors: `❌`

### Network Inspector
- Use Flutter DevTools network tab
- See all API requests
- Check request/response data

## Success Indicators

You'll know everything works when:
- ✅ App starts without errors
- ✅ Login succeeds
- ✅ Device list loads
- ✅ GPS data displays
- ✅ No network errors in console
- ✅ API logs show successful requests with correlation IDs

---

**Ready to test!** Open your Flutter project and run the app.

