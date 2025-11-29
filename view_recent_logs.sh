#!/bin/bash
# Quick script to view recent logs and filter for relevant entries

echo "🔍 Recent Logs Viewer"
echo "===================="
echo ""

# Check which log file exists
if [ -f "server.log" ]; then
    LOGFILE="server.log"
elif [ -f "server-8001.log" ]; then
    LOGFILE="server-8001.log"
else
    echo "❌ No log files found. Logs are in the terminal where server is running."
    exit 1
fi

echo "📄 Reading from: $LOGFILE"
echo ""
echo "=== Recent API Requests (last 30 lines) ==="
tail -30 "$LOGFILE" | grep -E "📡|❌|✅|⚠️" || tail -30 "$LOGFILE"
echo ""
echo ""
echo "=== Recent Errors (last 20 lines) ==="
tail -100 "$LOGFILE" | grep -i "error\|❌\|failed\|404\|exception" | tail -20 || echo "No errors found"
echo ""
echo ""
echo "=== Correlation IDs (for debugging specific requests) ==="
tail -50 "$LOGFILE" | grep -o "\[[a-zA-Z0-9]\{8\}\]" | sort -u | tail -10 || echo "No correlation IDs found"

