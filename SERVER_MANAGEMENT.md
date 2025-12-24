# 🚀 Server Management Guide

## Quick Commands

### ✅ Check Server Status
```bash
./server_status.sh
```

### 🚀 Start Server (Background)
```bash
./server_start.sh
```

### 🛑 Stop Server
```bash
./server_stop.sh
```

### 🔄 Start with Auto-Restart (Recommended for Development)
```bash
./keep_server_running.sh
```
Press `Ctrl+C` to stop the monitoring script.

---

## 📋 Solution Comparison

| Solution | Use Case | Pros | Cons |
|----------|----------|------|------|
| **server_start.sh** | Quick manual start | Simple, fast | No auto-restart |
| **keep_server_running.sh** | Active development | Auto-restarts on crash | Requires terminal to stay open |
| **launchd** | Always running | Starts on login, runs in background | More complex setup |
| **Render** | Production | Managed, scalable, always-on | Not for local dev |

---

## 🔧 Detailed Setup Instructions

### Option 1: Manual Start/Stop (Simplest)

**Start:**
```bash
cd /Users/fahadalmanee/pythonProject
./server_start.sh
```

**Stop:**
```bash
./server_stop.sh
```

**Check:**
```bash
./server_status.sh
```

---

### Option 2: Auto-Restart Script (Recommended for Development)

This keeps the server running and automatically restarts it if it crashes.

**Start:**
```bash
cd /Users/fahadalmanee/pythonProject
./keep_server_running.sh
```

**Stop:**
Press `Ctrl+C` in the terminal where the script is running.

**Run in Background:**
```bash
nohup ./keep_server_running.sh > /tmp/server_monitor.log 2>&1 &
```

---

### Option 3: macOS LaunchAgent (Starts on Login)

This makes the server start automatically when you log in to your Mac.

**Install:**
```bash
# Copy the plist file
cp /Users/fahadalmanee/pythonProject/com.dashcam.server.plist ~/Library/LaunchAgents/

# Load it
launchctl load ~/Library/LaunchAgents/com.dashcam.server.plist
```

**Start:**
```bash
launchctl start com.dashcam.server
```

**Stop:**
```bash
launchctl stop com.dashcam.server
```

**Uninstall:**
```bash
launchctl unload ~/Library/LaunchAgents/com.dashcam.server.plist
rm ~/Library/LaunchAgents/com.dashcam.server.plist
```

**View Logs:**
```bash
tail -f /tmp/dashcam_server.log
tail -f /tmp/dashcam_server_error.log
```

---

### Option 4: Production (Render)

For production, Render automatically:
- ✅ Keeps your server running 24/7
- ✅ Restarts on crashes
- ✅ Scales based on traffic
- ✅ Provides SSL certificates
- ✅ Monitors uptime

**Deploy to Render:**
```bash
git add .
git commit -m "Update server"
git push origin main
```

Render will automatically detect changes and redeploy.

---

## 🔍 Troubleshooting

### Server Won't Start

1. **Check if port 8000 is in use:**
```bash
lsof -i :8000
```

2. **Kill existing processes:**
```bash
killall -9 Python
```

3. **Check logs:**
```bash
tail -50 /tmp/dashcam_server.log
```

### Database Connection Issues

1. **Check .env file:**
```bash
cat /Users/fahadalmanee/pythonProject/.env | grep DATABASE
```

2. **Test database connection:**
```bash
cd /Users/fahadalmanee/pythonProject
python3 -c "from database import engine; print('✅ Database connected' if engine.connect() else '❌ Connection failed')"
```

### Permission Denied

```bash
chmod +x *.sh
```

---

## 📊 Monitoring

### View Real-Time Logs
```bash
tail -f /tmp/dashcam_server.log
```

### Check Server Health
```bash
curl http://localhost:8000/
```

### API Documentation
Open in browser: http://localhost:8000/docs

---

## 🎯 Best Practices

### For Local Development:
- Use **keep_server_running.sh** during active development
- Use **server_start.sh** for quick testing
- Check logs regularly: `tail -f /tmp/dashcam_server.log`

### For Production:
- Use **Render** for deployment
- Monitor via Render dashboard
- Set up alerts for downtime

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Start server | `./server_start.sh` |
| Stop server | `./server_stop.sh` |
| Check status | `./server_status.sh` |
| Auto-restart | `./keep_server_running.sh` |
| View logs | `tail -f /tmp/dashcam_server.log` |
| Test API | `curl http://localhost:8000/` |
| API docs | http://localhost:8000/docs |

---

## 🆘 Emergency Commands

**Force kill everything:**
```bash
killall -9 Python
```

**Clear all logs:**
```bash
rm /tmp/dashcam_*.log
```

**Fresh start:**
```bash
./server_stop.sh
sleep 2
./server_start.sh
```

