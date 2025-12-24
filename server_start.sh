#!/bin/bash

# Start the server in the background
cd /Users/fahadalmanee/pythonProject

# Kill any existing server
killall -9 Python 2>/dev/null || true
sleep 2

# Start new server
nohup python3 start.py > /tmp/dashcam_server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > /tmp/dashcam_server.pid

echo "🚀 Server starting..."
sleep 5

# Check if running
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "✅ Server started successfully (PID: $SERVER_PID)"
    echo "📝 Logs: tail -f /tmp/dashcam_server.log"
    echo "🌐 Access: http://localhost:8000"
else
    echo "❌ Server failed to start. Check logs:"
    tail -20 /tmp/dashcam_server.log
fi

