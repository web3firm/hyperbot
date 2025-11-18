#!/bin/bash
# HyperBot Monitor Script
# Usage: ./monitor.sh [option]
# Options: logs, status, stats, telegram, kill, restart

BOT_PID_FILE="bot.pid"
LOG_FILE="logs/bot_output.log"
TODAY_LOG="logs/bot_$(date +%Y%m%d).log"

show_status() {
    echo "========================================"
    echo "🤖 HYPERBOT STATUS"
    echo "========================================"
    
    if [ -f "$BOT_PID_FILE" ]; then
        PID=$(cat $BOT_PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo "✅ Bot is RUNNING (PID: $PID)"
            echo "⏱️  Uptime: $(ps -p $PID -o etime= | xargs)"
            echo "💾 Memory: $(ps -p $PID -o rss= | awk '{printf "%.2f MB", $1/1024}')"
            echo "🔥 CPU: $(ps -p $PID -o %cpu= | xargs)%"
        else
            echo "❌ Bot is NOT running (stale PID file)"
        fi
    else
        echo "❌ Bot is NOT running (no PID file)"
    fi
    
    echo ""
    echo "📊 Account Status:"
    tail -1 $LOG_FILE | grep "Account updated" || echo "No recent account data"
    
    echo ""
    echo "📝 Recent Activity (last 5 lines):"
    tail -5 $LOG_FILE
}

show_logs() {
    echo "========================================"
    echo "📋 LIVE BOT LOGS (Ctrl+C to exit)"
    echo "========================================"
    tail -f $LOG_FILE
}

show_stats() {
    echo "========================================"
    echo "📊 BOT STATISTICS"
    echo "========================================"
    
    if [ -f "$TODAY_LOG" ]; then
        echo "📅 Today's Log: $TODAY_LOG"
        echo ""
        echo "🎯 Signals Generated:"
        grep -c "Signal generated" $TODAY_LOG 2>/dev/null || echo "0"
        
        echo ""
        echo "💰 Trades Executed:"
        grep -c "Trade executed" $TODAY_LOG 2>/dev/null || echo "0"
        
        echo ""
        echo "⚠️  Errors:"
        grep -c "ERROR" $TODAY_LOG 2>/dev/null || echo "0"
        
        echo ""
        echo "🛑 Stop Losses Hit:"
        grep -c "SL triggered" $TODAY_LOG 2>/dev/null || echo "0"
        
        echo ""
        echo "✅ Take Profits Hit:"
        grep -c "TP triggered" $TODAY_LOG 2>/dev/null || echo "0"
    else
        echo "No log file for today yet"
    fi
}

check_telegram() {
    echo "========================================"
    echo "📱 TELEGRAM BOT STATUS"
    echo "========================================"
    
    if grep -q "Telegram bot started successfully" $LOG_FILE; then
        echo "✅ Telegram bot is connected"
        echo ""
        echo "Recent Telegram activity:"
        grep "Telegram" $LOG_FILE | tail -5
    else
        echo "❌ Telegram bot not initialized or failed"
    fi
}

kill_bot() {
    echo "========================================"
    echo "🛑 STOPPING BOT"
    echo "========================================"
    
    if [ -f "$BOT_PID_FILE" ]; then
        PID=$(cat $BOT_PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo "Killing bot process (PID: $PID)..."
            kill $PID
            sleep 2
            
            if ps -p $PID > /dev/null 2>&1; then
                echo "Force killing..."
                kill -9 $PID
            fi
            
            rm -f $BOT_PID_FILE
            echo "✅ Bot stopped"
        else
            echo "Bot was not running"
            rm -f $BOT_PID_FILE
        fi
    else
        echo "No PID file found"
    fi
}

restart_bot() {
    echo "========================================"
    echo "🔄 RESTARTING BOT"
    echo "========================================"
    
    kill_bot
    sleep 2
    
    echo "Starting bot..."
    nohup python3 -u app/bot.py > logs/bot_output.log 2>&1 & 
    echo $! > bot.pid
    
    sleep 3
    echo ""
    show_status
}

show_help() {
    echo "========================================"
    echo "🤖 HYPERBOT MONITOR SCRIPT"
    echo "========================================"
    echo ""
    echo "Usage: ./monitor.sh [option]"
    echo ""
    echo "Options:"
    echo "  status    - Show bot status and recent activity"
    echo "  logs      - Tail live logs (Ctrl+C to exit)"
    echo "  stats     - Show trading statistics"
    echo "  telegram  - Check Telegram bot status"
    echo "  kill      - Stop the bot"
    echo "  restart   - Restart the bot"
    echo "  help      - Show this help"
    echo ""
    echo "Examples:"
    echo "  ./monitor.sh status"
    echo "  ./monitor.sh logs"
    echo ""
}

# Main script
case "$1" in
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    stats)
        show_stats
        ;;
    telegram)
        check_telegram
        ;;
    kill)
        kill_bot
        ;;
    restart)
        restart_bot
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
