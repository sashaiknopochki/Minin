#!/bin/bash
# Helper script to watch the application logs in real-time
#
# Usage: ./watch_logs.sh
#
# This will show the last 50 lines and continuously update as new logs are written

echo "📋 Watching logs/minin.log (Ctrl+C to stop)..."
echo "=========================================="
echo ""

# Show last 50 lines and follow new entries
tail -n 50 -f logs/minin.log
