#!/bin/bash

# Stop the server
echo "🛑 Stopping Dashcam Server..."

if [ -f /tmp/dashcam_server.pid ]; then
    PID=$(cat /tmp/dashcam_server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "✅ Server stopped (PID: $PID)"
        rm /tmp/dashcam_server.pid
    else
        echo "⚠️  Server not running (PID file found but process not running)"
        rm /tmp/dashcam_server.pid
    fi
else
    # Try killing all Python processes running start.py
    killall -9 Python 2>/dev/null && echo "✅ Killed all Python processes" || echo "⚠️  No server processes found"
fi

