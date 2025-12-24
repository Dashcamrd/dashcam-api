#!/bin/bash

echo "🔍 Checking if server is running..."
echo ""

# Check if port 8000 is in use
if lsof -i :8000 -P -n | grep -q LISTEN; then
    echo "✅ Server IS RUNNING on port 8000"
    echo ""
    echo "Process details:"
    lsof -i :8000 -P -n | grep LISTEN
    echo ""
    echo "🌐 Try accessing: http://localhost:8000"
else
    echo "❌ Server is NOT running"
    echo ""
    echo "To start the server, run:"
    echo "  cd /Users/fahadalmanee/pythonProject"
    echo "  python3 start.py"
fi

