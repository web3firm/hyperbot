#!/bin/bash
# Stop HyperBot

echo "🛑 Stopping HyperBot..."

PID=$(pgrep -f "python -m app.bot")

if [ -z "$PID" ]; then
    echo "❌ Bot is not running"
    exit 1
fi

echo "Found process: $PID"
kill $PID

# Wait for graceful shutdown
sleep 2

# Force kill if still running
if ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  Forcing shutdown..."
    kill -9 $PID
fi

echo "✅ Bot stopped successfully"
