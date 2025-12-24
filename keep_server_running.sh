#!/bin/bash

# Script to keep the server running and auto-restart on crash
# Usage: ./keep_server_running.sh

LOG_FILE="/tmp/dashcam_server.log"
PID_FILE="/tmp/dashcam_server.pid"

echo "🔄 Starting Dashcam Server Monitor..."
echo "📝 Logs: $LOG_FILE"
echo "🛑 To stop: kill \$(cat $PID_FILE)"
echo ""

# Function to check if server is running
is_server_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start server
start_server() {
    echo "🚀 Starting server at $(date)..."
    cd /Users/fahadalmanee/pythonProject
    python3 start.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 5
    
    if is_server_running; then
        echo "✅ Server started successfully (PID: $(cat $PID_FILE))"
        echo "🌐 Access at: http://localhost:8000"
    else
        echo "❌ Server failed to start. Check logs: tail -f $LOG_FILE"
    fi
}

# Function to stop server
stop_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "🛑 Stopping server (PID: $PID)..."
        kill "$PID" 2>/dev/null
        rm -f "$PID_FILE"
    fi
}

# Cleanup on exit
trap stop_server EXIT INT TERM

# Main loop
while true; do
    if ! is_server_running; then
        echo "⚠️  Server not running, restarting..."
        start_server
    fi
    sleep 10  # Check every 10 seconds
done

