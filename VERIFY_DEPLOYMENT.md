# Deployment Verification Guide

## ✅ Post-Deployment Checklist

Since you've manually deployed to Render, verify the following:

### 1. Service Status
- [ ] Service shows "Live" status in Render dashboard
- [ ] No build errors in Render logs
- [ ] Service URL is accessible

### 2. Health Check
```bash
curl https://your-app.onrender.com/health
```
Expected: `{"status":"ok"}`

### 3. API Documentation
Visit: `https://your-app.onrender.com/docs`
- [ ] Swagger UI loads correctly
- [ ] All endpoints are listed
- [ ] Can expand and view endpoint details

### 4. Authentication Test
```bash
curl -X POST https://your-app.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"invoice_no":"INV2024001","password":"customer123"}'
```
Expected: Returns `access_token` and user info

### 5. Check Logs for Correlation IDs
In Render dashboard → Logs:
- [ ] Look for `📡 [xxxx]` pattern (correlation IDs)
- [ ] Look for `🔧 Manufacturer API Config` message
- [ ] No `❌` error messages
- [ ] Check if token refresh is working

### 6. Manufacturer API Connection
Logs should show:
```
🔧 Manufacturer API Config (Profile: default):
   Base URL: http://180.167.106.70:9337
   Username: your_username
   Password: ***
   Token: Will be fetched automatically on first use
   Endpoints loaded: 49
```

### 7. Test GPS Endpoint (if device available)
```bash
# First, get auth token
TOKEN=$(curl -X POST https://your-app.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"invoice_no":"INV2024001","password":"customer123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Then test GPS endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://your-app.onrender.com/gps/latest/cam001
```

### 8. Verify Adapters Are Working
Check logs for:
- `[correlation_id]` in adapter parse messages
- Successful DTO creation
- No adapter errors

### 9. Rate Limiting Status
Logs should not show excessive:
- `⏳ Rate limit reached` messages
- If you see them, rate limiting is working!

### 10. Error Handling
Test with invalid device:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://your-app.onrender.com/gps/latest/invalid_device
```
Should return graceful error, not crash

## 🔍 Common Issues

### Build Succeeded but Service Won't Start
**Check:**
1. Environment variables are all set
2. Database connection works
3. Manufacturer API credentials are correct
4. Check Render logs for Python errors

### "No module named 'yaml'"
**Fix:** Ensure `PyYAML` is in `requirements.txt` ✅ (already added)

### "Config file not found"
**Fix:** Ensure `config/manufacturer_api.yaml` is committed ✅ (already committed)

### Authentication Works But API Calls Fail
**Check:**
1. Manufacturer API credentials in environment variables
2. Base URL is correct: `http://180.167.106.70:9337`
3. Check logs for token refresh errors
4. Verify API is accessible from Render's network

### Rate Limiting Too Strict
**Adjust in config:**
```yaml
# In config/manufacturer_api.yaml
rate_limit_per_minute: 120  # Increase if needed
```

## 📊 What Should Be Working

✅ **49 Endpoints** configured via YAML  
✅ **Adapter Pattern** - All vendor API calls go through adapters  
✅ **Rate Limiting** - 60 requests/minute (configurable)  
✅ **Retry Logic** - Automatic retries with exponential backoff  
✅ **Correlation IDs** - All requests traceable  
✅ **Error Handling** - Graceful degradation  
✅ **Config-Driven** - Easy to update endpoints  

## 📝 Deployment Summary

**Status:** ✅ Deployed to Render  
**Commit:** `74dd04a` - Production ready  
**Key Changes:**
- Adapter architecture implemented
- 49 endpoints configured
- Rate limiting & retries
- Request tracing

**Next Steps:**
1. Verify all endpoints work
2. Test with real device data
3. Monitor logs for issues
4. Update Flutter app to use production URL

