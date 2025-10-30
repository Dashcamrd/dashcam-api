# 🚀 Production Deployment Checklist

## Pre-Deployment (Complete Before Deploying)

### Code & Dependencies
- [x] All adapters implemented (GPS, Device, Media, Task, Statistics)
- [x] Config-driven API (49 endpoints in YAML)
- [x] Rate limiting and retry logic
- [x] Correlation IDs for tracing
- [x] `requirements.txt` updated with PyYAML
- [x] All imports working (`python -m py_compile` on all .py files)

### Configuration Files
- [x] `config/manufacturer_api.yaml` exists and is complete
- [x] `render.yaml` updated with correct base URL
- [x] `Procfile` configured
- [x] `start.py` handles migrations

### Security
- [ ] **SECRET_KEY** - Generate strong random key for production
- [ ] **Database password** - Use secure cloud database
- [ ] **API credentials** - Use production manufacturer API credentials
- [ ] **No secrets in code** - Verify no hardcoded passwords/tokens

### Testing
- [x] Adapter unit tests pass
- [x] Config integration tests pass
- [x] Syntax validation passes
- [ ] End-to-end tests (requires valid credentials)
- [ ] Load testing (optional)

## Deployment Steps

### Step 1: Commit All Changes

```bash
# Verify what needs to be committed
git status

# Add all production files
git add .
git commit -m "Production deployment: Adapters, rate limiting, config-driven API"

# Push to repository
git push origin main
```

### Step 2: Render Dashboard Setup

1. **Go to**: https://dashboard.render.com
2. **Select/Create Service**: `dashcam-api`
3. **Connect Repository**: Link your GitHub repo
4. **Build Settings**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python start.py`

### Step 3: Environment Variables

**Copy these into Render Environment Variables:**

```bash
# Database (REQUIRED - Use your cloud database)
DATABASE_URL=mysql+pymysql://user:password@host:port/database

# Security (REQUIRED - CHANGE SECRET_KEY!)
SECRET_KEY=<GENERATE_STRONG_RANDOM_KEY>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Manufacturer API (REQUIRED - Use production credentials)
MANUFACTURER_API_BASE_URL=http://180.167.106.70:9337
MANUFACTURER_API_USERNAME=<your-production-username>
MANUFACTURER_API_PASSWORD=<your-production-password>

# Server (REQUIRED)
HOST=0.0.0.0
PORT=$PORT
RELOAD=false
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 4: Deploy

1. Click **"Save Changes"** in Render
2. Monitor **Build Logs** for errors
3. Wait for deployment (2-3 minutes)
4. Note the **Service URL** (e.g., `https://dashcam-api.onrender.com`)

### Step 5: Verify Deployment

```bash
# Test health endpoint
curl https://your-app.onrender.com/health
# Expected: {"status":"ok"}

# Test API docs
open https://your-app.onrender.com/docs

# Test authentication
curl -X POST https://your-app.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"invoice_no":"INV2024001","password":"customer123"}'
```

## Post-Deployment Verification

### Immediate Checks
- [ ] Health endpoint returns 200
- [ ] API documentation accessible
- [ ] No errors in Render logs
- [ ] Service shows "Live" status

### Functional Tests
- [ ] Can authenticate successfully
- [ ] GPS endpoints work
- [ ] Device endpoints work
- [ ] Logs show correlation IDs
- [ ] Rate limiting is active

### Database
- [ ] Tables created successfully
- [ ] Can create users
- [ ] Can assign devices

### Monitoring
- [ ] Check logs for errors
- [ ] Verify correlation IDs in logs
- [ ] Check rate limiting behavior
- [ ] Monitor response times

## Rollback Plan

If deployment fails:

1. **Check Build Logs**:
   - Look for import errors
   - Check for missing dependencies
   - Verify environment variables

2. **Common Issues**:
   - Missing PyYAML → Add to requirements.txt
   - Config file not found → Ensure `config/` directory included
   - Database connection → Verify DATABASE_URL
   - API credentials → Verify manufacturer API vars

3. **Rollback Steps**:
   - Revert to previous commit if needed
   - Fix issues locally
   - Re-deploy

## Configuration Summary

### Current Production Settings

**Rate Limiting:**
- Default: 60 requests/minute
- Configurable per profile

**Timeouts:**
- Default: 30 seconds
- GPS searches: 60 seconds

**Retries:**
- Default: 3 attempts
- Exponential backoff: 1s, 2s, 4s

**API Endpoints:**
- 49 endpoints configured
- All use adapter pattern
- All have correlation IDs

## Quick Reference

**Service URL Format:**
```
https://dashcam-api.onrender.com
```

**Health Check:**
```
GET /health
```

**API Documentation:**
```
https://your-app.onrender.com/docs
```

**Logs Location:**
- Render Dashboard → Your Service → Logs

**Environment Variables:**
- Render Dashboard → Your Service → Environment

---

**Status**: ✅ Ready for Production Deployment

