# Deploy to Render (Free Tier)

## Step 1: Go to Render
1. Visit: https://render.com
2. Sign up with your GitHub account
3. Authorize Render to access your repositories

## Step 2: Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository: `Dashcamrd/dashcam-api`
3. Configure the service:

### Basic Settings:
- **Name:** `dashcam-api`
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python start.py`

### Environment Variables:
Add these in the "Environment" section:
```
DATABASE_URL=mysql+pymysql://root:DHwoWoogDNQzVkoCJvJPPAmpAQdwdIwy@shortline.proxy.rlwy.net:58339/railway
SECRET_KEY=supersecretkey123!@#$%^&*()dashcam-platform-jwt-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
MANUFACTURER_API_BASE_URL=http://127.0.0.1:9337
MANUFACTURER_API_USERNAME=your_integrator_username
MANUFACTURER_API_PASSWORD=your_integrator_password
MANUFACTURER_TOKEN_EXPIRE_HOURS=24
HOST=0.0.0.0
PORT=8000
RELOAD=false
```

## Step 3: Deploy
1. Click "Create Web Service"
2. Render will build and deploy your app
3. Wait for deployment (2-3 minutes)

## Step 4: Get Your URL
After deployment, you'll get a URL like:
`https://dashcam-api.onrender.com`

## Benefits of Render Free Tier:
- ✅ Free hosting
- ✅ Automatic HTTPS
- ✅ Custom domain support
- ✅ GitHub integration
- ✅ Environment variables
- ✅ Build logs
- ✅ Health checks

## Limitations:
- ⚠️ Sleeps after 15 minutes of inactivity
- ⚠️ 750 hours/month free
- ⚠️ Cold start takes ~30 seconds

## Test Your Deployed API:
```bash
# Health check
curl https://your-app-name.onrender.com/health

# Login
curl -X POST https://your-app-name.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"invoice_no":"INV2024001","password":"customer123"}'
```
