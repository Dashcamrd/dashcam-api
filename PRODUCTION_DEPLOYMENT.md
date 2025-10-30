# Production Deployment Guide

## 🚀 Pre-Deployment Checklist

### ✅ Code Quality
- [x] All adapters implemented and tested
- [x] Enhanced response validation in place
- [x] Rate limiting and retry logic configured
- [x] Correlation IDs for request tracing
- [x] Error handling with proper logging
- [x] Configuration externalized to YAML

### ✅ Dependencies
- [x] `requirements.txt` includes all dependencies
- [x] PyYAML added for config parsing
- [x] All Python packages compatible

### ✅ Configuration
- [x] Config file: `config/manufacturer_api.yaml` (49 endpoints)
- [x] Environment variables documented
- [x] Default values configured

### ⚠️ Required Environment Variables

**Critical - Must be set in production:**

```bash
# Database
DATABASE_URL=mysql+pymysql://user:pass@host:port/database

# Security
SECRET_KEY=your-strong-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Manufacturer API
MANUFACTURER_API_BASE_URL=http://180.167.106.70:9337
MANUFACTURER_API_USERNAME=your_username
MANUFACTURER_API_PASSWORD=your_password

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=false
```

**Optional (have defaults):**

```bash
MANUFACTURER_API_PROFILE=default
MANUFACTURER_API_CONFIG=config/manufacturer_api.yaml
MANUFACTURER_TOKEN_EXPIRE_HOURS=24
```

## 📦 Deployment to Render

### Step 1: Prepare Repository

Ensure all files are committed:

```bash
git add .
git commit -m "Production ready: Adapters, rate limiting, config-driven API"
git push origin main
```

### Step 2: Configure Render Service

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Create/Update Web Service**:
   - Connect GitHub repository
   - Service name: `dashcam-api`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python start.py`

### Step 3: Set Environment Variables

**In Render Dashboard → Environment Variables:**

```bash
# Database (use your Railway/cloud DB)
DATABASE_URL=mysql+pymysql://root:password@host:port/database

# Security (CHANGE THESE IN PRODUCTION!)
SECRET_KEY=<generate-strong-random-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Manufacturer API
MANUFACTURER_API_BASE_URL=http://180.167.106.70:9337
MANUFACTURER_API_USERNAME=<your-username>
MANUFACTURER_API_PASSWORD=<your-password>

# Server
HOST=0.0.0.0
PORT=$PORT  # Render sets this automatically
RELOAD=false
```

### Step 4: Deploy

1. Click "Save Changes"
2. Render will automatically deploy
3. Monitor build logs for errors
4. Wait for deployment to complete (~2-3 minutes)

### Step 5: Verify Deployment

```bash
# Health check
curl https://your-app.onrender.com/health

# Expected: {"status":"ok"}

# API docs
curl https://your-app.onrender.com/docs

# Test authentication
curl -X POST https://your-app.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"invoice_no":"INV2024001","password":"customer123"}'
```

## 🔒 Security Checklist

### Before Going Live

- [ ] **SECRET_KEY**: Changed from default to strong random key
- [ ] **Database credentials**: Using secure cloud database
- [ ] **API credentials**: Using production manufacturer API credentials
- [ ] **HTTPS**: Enabled (Render provides automatically)
- [ ] **CORS**: Configure if needed for frontend
- [ ] **Rate limiting**: Configured (60/min default)
- [ ] **Logging**: Review what's logged (ensure no secrets)

### Secrets Management

**DO NOT commit these to Git:**
- `SECRET_KEY`
- `DATABASE_URL` (if contains password)
- `MANUFACTURER_API_PASSWORD`
- Any API tokens

**Use Render Environment Variables** instead of hardcoding.

## 📊 Monitoring & Observability

### Logs

Render provides built-in logs. Check for:
- Correlation IDs: `[xxxx]` pattern
- API requests: `📡` emoji prefix
- Errors: `❌` emoji prefix
- Rate limiting: `⏳` emoji prefix

### Health Endpoints

- `/health` - Basic health check
- `/docs` - API documentation
- All endpoints return correlation IDs in logs

### Metrics to Monitor

1. **API Response Times**: Check logs for timeouts
2. **Rate Limiting Events**: Look for `Rate limit reached` messages
3. **Retry Attempts**: Look for `Retrying` messages
4. **Authentication Failures**: Look for `Failed to get valid token`
5. **Error Rates**: Monitor for `❌` errors

## 🔄 Post-Deployment

### 1. Database Setup

Ensure database migrations run on first deploy:
- Tables created automatically
- `device_id` column added to users table if needed

### 2. Initial Data

Create admin user if needed:
```bash
# Use setup_initial_data.py or admin endpoint
curl -X POST https://your-app.onrender.com/admin/users \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"invoice_no":"ADMIN001","password":"admin123","name":"Admin","email":"admin@example.com"}'
```

### 3. Device Assignment

Sync devices from manufacturer API:
- Use `/admin/devices/sync` endpoint
- Assign devices to users via admin panel

### 4. Frontend Configuration

Update Flutter app to use production URL:
```dart
// In Flutter app
const baseUrl = 'https://your-app.onrender.com';
```

## 🐛 Troubleshooting

### Build Fails

**Issue**: `ModuleNotFoundError: No module named 'yaml'`

**Fix**: Ensure `PyYAML` is in `requirements.txt`

### API Not Responding

**Check**:
1. Environment variables set correctly
2. Database connection working
3. Manufacturer API credentials valid
4. Logs for error messages

### Rate Limiting Too Aggressive

**Adjust in `config/manufacturer_api.yaml`:**
```yaml
rate_limit_per_minute: 120  # Increase limit
```

### Timeouts Too Short

**Adjust per endpoint:**
```yaml
gps_search_v1:
  timeout: 90  # Increase timeout
```

## 📝 Configuration Files

### Required Files for Deployment

- ✅ `requirements.txt` - Python dependencies
- ✅ `Procfile` - Process configuration (Render uses `start.py`)
- ✅ `start.py` - Startup script
- ✅ `config/manufacturer_api.yaml` - API configuration
- ✅ `main.py` - FastAPI application
- ✅ All adapter files in `adapters/`
- ✅ All router files in `routers/`
- ✅ All service files in `services/`
- ✅ All model files in `models/`

### Optional Files (Not Required)

- Test files: `test_*.py`
- Documentation: `*.md` files
- `.env` (use Render env vars instead)

## 🎯 Production Features Enabled

- ✅ **Config-driven API**: 49 endpoints configured
- ✅ **Adapter pattern**: Vendor API decoupled
- ✅ **Rate limiting**: 60 requests/minute (configurable)
- ✅ **Retry logic**: Exponential backoff on failures
- ✅ **Request tracing**: Correlation IDs
- ✅ **Error handling**: Graceful degradation
- ✅ **Type safety**: Pydantic DTOs
- ✅ **Logging**: Structured logs with correlation IDs

## 📞 Support

If deployment fails:
1. Check Render build logs
2. Verify environment variables
3. Test database connection
4. Verify manufacturer API credentials
5. Check logs for correlation IDs to trace issues

## ✅ Deployment Status

Once deployed, verify:
- [ ] Health endpoint responds
- [ ] API docs accessible
- [ ] Authentication works
- [ ] GPS endpoints functional
- [ ] Device endpoints functional
- [ ] Logs show correlation IDs
- [ ] No errors in logs

---

**Ready for production!** 🚀

