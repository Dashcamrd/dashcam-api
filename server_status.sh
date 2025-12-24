#!/bin/bash

# Check server status
echo "🔍 Checking Dashcam Server Status..."
echo ""

# Check if running
if lsof -i :8000 -P -n | grep -q LISTEN; then
    echo "✅ Server IS RUNNING on port 8000"
    echo ""
    echo "Process details:"
    lsof -i :8000 -P -n | grep LISTEN
    echo ""
    
    # Test API
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ API is responding"
        RESPONSE=$(curl -s http://localhost:8000/)
        echo "   Response: $RESPONSE"
    else
        echo "⚠️  Port is open but API not responding"
    fi
    
    echo ""
    echo "🌐 URLs:"
    echo "   - API: http://localhost:8000"
    echo "   - Docs: http://localhost:8000/docs"
    echo ""
    echo "📝 View logs: tail -f /tmp/dashcam_server.log"
else
    echo "❌ Server is NOT running"
    echo ""
    echo "To start the server:"
    echo "  ./server_start.sh"
    echo ""
    echo "Or with auto-restart:"
    echo "  ./keep_server_running.sh"
fi

