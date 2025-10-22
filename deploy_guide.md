# Deploy API to Railway

## Step 1: Prepare for Deployment

### Create Railway Project
1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"

### Add Your Code to GitHub
1. Create new repository on GitHub
2. Push your code:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/dashcam-api.git
git push -u origin main
```

## Step 2: Deploy to Railway

### Connect Repository
1. In Railway, select your GitHub repository
2. Railway will auto-detect Python
3. Add environment variables

### Environment Variables in Railway
Add these in Railway dashboard:
```
DATABASE_URL=mysql+pymysql://root:DHwoWoogDNQzVkoCJvJPPAmpAQdwdIwy@shortline.proxy.rlwy.net:58339/railway
SECRET_KEY=supersecretkey123!@#$%^&*()dashcam-platform-jwt-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
MANUFACTURER_API_BASE_URL=http://127.0.0.1:9337
MANUFACTURER_API_USERNAME=your_integrator_username
MANUFACTURER_API_PASSWORD=your_integrator_password
MANUFACTURER_TOKEN_EXPIRE_HOURS=24
```

### Railway Configuration
Railway will automatically:
- Install dependencies from requirements.txt
- Run your FastAPI app
- Provide public URL

## Step 3: Test Deployed API

After deployment, you'll get a URL like:
`https://your-app-name.railway.app`

Test endpoints:
```bash
# Health check
curl https://your-app-name.railway.app/health

# Login
curl -X POST https://your-app-name.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"invoice_no":"INV2024001","password":"customer123"}'
```

## Step 4: Update Frontend Configuration

Once deployed, update your frontend to use:
```javascript
const API_BASE_URL = 'https://your-app-name.railway.app'
```

## Benefits of Cloud Deployment
- ✅ Publicly accessible API
- ✅ Automatic HTTPS
- ✅ Auto-scaling
- ✅ Easy frontend integration
- ✅ Professional URL
- ✅ No local server needed


