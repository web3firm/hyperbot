#!/bin/bash
# Quick check script - verify bot is running properly

echo "🤖 HyperBot Health Check"
echo "========================="

# Check if bot process is running
if pgrep -f "python -m app.bot" > /dev/null; then
    echo "✅ Bot process: RUNNING"
    PID=$(pgrep -f "python -m app.bot")
    echo "   PID: $PID"
else
    echo "❌ Bot process: NOT RUNNING"
fi

# Check system resources
echo ""
echo "📊 System Resources:"
echo "   $(free -h | grep Mem | awk '{print "Memory: "$3"/"$2}')"
echo "   $(df -h / | tail -1 | awk '{print "Disk: "$3"/"$2" ("$5" used)"}')"
echo "   CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')% used"

# Check last log entry
echo ""
echo "📝 Last Log Entry:"
LOG_FILE=$(ls -t logs/bot_*.log 2>/dev/null | head -1)
if [ -f "$LOG_FILE" ]; then
    tail -1 "$LOG_FILE"
else
    echo "   No log files found"
fi

# Check account balance
echo ""
echo "💰 Account Status:"
grep -E "Account updated|value=" "$LOG_FILE" 2>/dev/null | tail -1 | grep -oP 'value=\$\K[0-9.]+' | head -1 | awk '{print "   Balance: $"$1}'

# Check for errors
echo ""
ERROR_COUNT=$(grep -c ERROR "$LOG_FILE" 2>/dev/null || echo 0)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Errors in log: $ERROR_COUNT"
    echo "   Last error:"
    grep ERROR "$LOG_FILE" | tail -1
else
    echo "✅ No errors in current log"
fi

# Check systemd status (if using systemd)
if command -v systemctl &> /dev/null; then
    echo ""
    echo "🔧 Service Status:"
    if systemctl is-active --quiet hyperbot 2>/dev/null; then
        echo "   ✅ Systemd service: ACTIVE"
    else
        echo "   ⚠️  Systemd service: INACTIVE"
    fi
fi

echo ""
echo "========================="
