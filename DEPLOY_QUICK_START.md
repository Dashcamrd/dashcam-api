# 🚀 Quick Deployment Guide

## One-Command Deployment to Render

### Prerequisites
1. GitHub repository connected to Render
2. Render account with service created

### Step 1: Set Environment Variables in Render

Go to Render Dashboard → Your Service → Environment and add:

```bash
DATABASE_URL=mysql+pymysql://user:pass@host:port/db
SECRET_KEY=3e7Spb_0dvt8v6Bn_xxHohf7IEQlIbMPPmU_hN3-GWo
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
MANUFACTURER_API_BASE_URL=http://180.167.106.70:9337
MANUFACTURER_API_USERNAME=<your-username>
MANUFACTURER_API_PASSWORD=<your-password>
HOST=0.0.0.0
PORT=$PORT
RELOAD=false
```

### Step 2: Commit & Push

```bash
git add .
git commit -m "Production ready: Adapters, rate limiting, config-driven API"
git push origin main
```

### Step 3: Deploy

Render will automatically deploy when you push. Or click "Manual Deploy" in Render dashboard.

### Step 4: Verify

```bash
# Replace with your Render URL
curl https://your-app.onrender.com/health
```

Expected: `{"status":"ok"}`

## 🎯 What's Deployed

✅ **49 API endpoints** - All config-driven via YAML  
✅ **Adapter architecture** - Vendor API decoupled  
✅ **Rate limiting** - 60 requests/minute  
✅ **Retry logic** - Exponential backoff  
✅ **Request tracing** - Correlation IDs  
✅ **Error handling** - Graceful degradation  

## 📝 Files Required for Deployment

- ✅ `requirements.txt` (includes PyYAML)
- ✅ `Procfile` (web: python start.py)
- ✅ `start.py` (handles migrations)
- ✅ `config/manufacturer_api.yaml` (49 endpoints)
- ✅ `adapters/` (all adapter files)
- ✅ All router, service, and model files

## 🔍 Troubleshooting

**Build fails with "No module named 'yaml'"?**
→ Ensure `PyYAML` is in `requirements.txt` ✅ (already added)

**Config file not found?**
→ Ensure `config/manufacturer_api.yaml` is committed ✅

**Database connection fails?**
→ Verify `DATABASE_URL` environment variable

**API not responding?**
→ Check logs in Render dashboard for correlation IDs

## 📚 Full Documentation

- **Detailed Guide**: `PRODUCTION_DEPLOYMENT.md`
- **Checklist**: `DEPLOYMENT_CHECKLIST.md`
- **Rate Limiting**: `RATE_LIMITING.md`

---

**Status**: ✅ Ready to Deploy!

