#!/bin/bash
# End-to-End Test Runner
# This script starts the server (if not running) and runs E2E tests

cd "$(dirname "$0")"

echo "🚀 End-to-End Test Runner"
echo "=========================="
echo ""

# Check if server is already running
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Server is already running"
    echo ""
    source .venv/bin/activate
    python test_e2e.py
else
    echo "⚠️  Server is not running"
    echo ""
    echo "Starting server in background..."
    source .venv/bin/activate
    
    # Start server in background
    python start.py > server_test.log 2>&1 &
    SERVER_PID=$!
    
    echo "Server started with PID: $SERVER_PID"
    echo "Waiting for server to be ready..."
    
    # Wait up to 30 seconds for server to be ready
    for i in {1..30}; do
        if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
            echo "✅ Server is ready!"
            echo ""
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    # Run tests
    echo ""
    python test_e2e.py
    TEST_EXIT_CODE=$?
    
    # Cleanup: stop the server
    echo ""
    echo "Stopping server (PID: $SERVER_PID)..."
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    
    exit $TEST_EXIT_CODE
fi

