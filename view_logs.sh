#!/bin/bash
# Quick log viewer script

echo "🔍 Log Viewer"
echo "============"
echo ""
echo "Choose option:"
echo "1. View server.log (last 50 lines)"
echo "2. View server-8001.log (last 50 lines)"
echo "3. Follow server.log (live updates)"
echo "4. Search logs for correlation ID"
echo "5. Search logs for errors"
read -p "Enter choice (1-5): " choice

case $choice in
  1)
    tail -50 server.log 2>/dev/null || echo "server.log not found"
    ;;
  2)
    tail -50 server-8001.log 2>/dev/null || echo "server-8001.log not found"
    ;;
  3)
    tail -f server.log 2>/dev/null || echo "server.log not found"
    ;;
  4)
    read -p "Enter correlation ID: " cid
    grep "$cid" *.log 2>/dev/null || echo "No matches found"
    ;;
  5)
    grep -i "error\|❌\|failed" *.log 2>/dev/null | tail -20 || echo "No errors found"
    ;;
  *)
    echo "Invalid choice"
    ;;
esac
