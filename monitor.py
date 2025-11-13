#!/usr/bin/env python3
"""
Hyperliquid Trading Bot Monitor
Simple monitoring and status script
"""

import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

def check_bot_status():
    """Check if bot is running"""
    try:
        # Check for recent log entries
        log_file = Path("logs/trading_bot.log")
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1]
                    # Extract timestamp from last log line
                    if "2025-" in last_line:
                        return True, "Bot appears to be running (recent log activity)"
        return False, "No recent activity detected"
    except Exception as e:
        return False, f"Error checking status: {e}"

def get_portfolio_summary():
    """Get portfolio summary from logs"""
    try:
        log_file = Path("logs/trading_bot.log")
        if not log_file.exists():
            return "No log file found"
        
        positions = []
        recent_trades = []
        
        with open(log_file, 'r') as f:
            lines = f.readlines()[-100:]  # Last 100 lines
            
            for line in lines:
                if "Opened" in line and "position" in line:
                    recent_trades.append(line.strip())
                elif "Active positions:" in line:
                    positions.append(line.strip())
        
        summary = []
        summary.append("📊 PORTFOLIO SUMMARY")
        summary.append("=" * 40)
        
        if positions:
            summary.append(f"Last status: {positions[-1]}")
        else:
            summary.append("No position information found")
        
        if recent_trades:
            summary.append("\n🎯 RECENT TRADES:")
            for trade in recent_trades[-5:]:  # Last 5 trades
                summary.append(f"  {trade}")
        else:
            summary.append("\n🎯 RECENT TRADES: None")
        
        return "\n".join(summary)
        
    except Exception as e:
        return f"Error getting portfolio summary: {e}"

def show_risk_status():
    """Show risk management status"""
    try:
        log_file = Path("logs/trading_bot.log")
        if not log_file.exists():
            return "No log file found"
        
        risk_info = []
        
        with open(log_file, 'r') as f:
            lines = f.readlines()[-50:]  # Last 50 lines
            
            for line in lines:
                if any(keyword in line.lower() for keyword in ['risk', 'stop loss', 'drawdown', 'violation']):
                    risk_info.append(line.strip())
        
        summary = []
        summary.append("🛡️ RISK STATUS")
        summary.append("=" * 40)
        
        if risk_info:
            for info in risk_info[-5:]:  # Last 5 risk events
                summary.append(f"  {info}")
        else:
            summary.append("  ✅ No recent risk alerts")
        
        return "\n".join(summary)
        
    except Exception as e:
        return f"Error getting risk status: {e}"

def show_performance():
    """Show basic performance metrics"""
    try:
        log_file = Path("logs/trading_bot.log")
        if not log_file.exists():
            return "No log file found"
        
        pnl_info = []
        
        with open(log_file, 'r') as f:
            lines = f.readlines()[-100:]  # Last 100 lines
            
            for line in lines:
                if "PnL" in line:
                    pnl_info.append(line.strip())
        
        summary = []
        summary.append("📈 PERFORMANCE")
        summary.append("=" * 40)
        
        if pnl_info:
            summary.append("Recent PnL updates:")
            for info in pnl_info[-10:]:  # Last 10 PnL updates
                summary.append(f"  {info}")
        else:
            summary.append("  No PnL information found")
        
        return "\n".join(summary)
        
    except Exception as e:
        return f"Error getting performance data: {e}"

def main():
    """Main monitoring function"""
    print("🤖 Hyperliquid Trading Bot Monitor")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check bot status
    is_running, status_msg = check_bot_status()
    status_emoji = "🟢" if is_running else "🔴"
    print(f"{status_emoji} Bot Status: {status_msg}")
    print()
    
    # Show portfolio summary
    print(get_portfolio_summary())
    print()
    
    # Show risk status
    print(show_risk_status())
    print()
    
    # Show performance
    print(show_performance())
    print()
    
    # Show quick commands
    print("💡 QUICK COMMANDS")
    print("=" * 40)
    print("  View live logs:     tail -f logs/trading_bot.log")
    print("  Start bot:          python main.py")
    print("  Run tests:          python demo_test.py")
    print("  Setup menu:         python setup.py")
    print("  Monitor (refresh):  python monitor.py")
    print()
    
    if not is_running:
        print("⚠️  Bot is not running. To start:")
        print("   1. Ensure .env is configured with your credentials")
        print("   2. Run: python main.py")
        print("   3. Monitor logs for any errors")

if __name__ == "__main__":
    main()