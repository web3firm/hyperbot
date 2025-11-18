#!/bin/bash
# Bot Monitoring Script

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  🤖 HYPERAI TRADER STATUS                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if bot is running
if pgrep -f "python app/bot.py" > /dev/null; then
    echo "✅ Bot Status: RUNNING"
    PID=$(pgrep -f "python app/bot.py")
    echo "   PID: $PID"
    echo "   Runtime: $(ps -p $PID -o etime= | xargs)"
else
    echo "❌ Bot Status: STOPPED"
    echo ""
    echo "To start: python app/bot.py"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Recent Activity (last 10 lines):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -10 logs/bot_live.log
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Watch live:    tail -f logs/bot_live.log"
echo "  Stop bot:      kill $PID"
echo "  View trades:   cat data/trades/*.jsonl"
echo "  Check status:  ./monitor.sh"
echo ""
