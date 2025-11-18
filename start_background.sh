#!/bin/bash
# Quick Start Script for VPS Background Execution

echo "🚀 Starting HyperBot in background..."

# Check if already running
if pgrep -f "python -m app.bot" > /dev/null; then
    echo "⚠️  Bot is already running!"
    echo "PID: $(pgrep -f 'python -m app.bot')"
    exit 1
fi

# Activate venv and start
cd "$(dirname "$0")"
source venv/bin/activate

# Start bot in background with nohup
nohup python -m app.bot >> logs/bot_$(date +%Y%m%d).log 2>&1 &

PID=$!
echo "✅ Bot started successfully!"
echo "PID: $PID"
echo "Log: logs/bot_$(date +%Y%m%d).log"
echo ""
echo "Commands:"
echo "  View logs:  tail -f logs/bot_$(date +%Y%m%d).log"
echo "  Stop bot:   kill $PID  (or ./stop.sh)"
echo "  Check status: ps aux | grep 'app.bot'"
