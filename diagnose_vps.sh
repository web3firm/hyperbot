#!/bin/bash
# VPS Diagnostic Script for HyperBot
# Run this on your VPS to diagnose issues

echo "╔════════════════════════════════════════════════════════════╗"
echo "║            HYPERBOT VPS DIAGNOSTIC                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running
echo "🔍 1. CHECKING BOT STATUS..."
if command -v pm2 &> /dev/null; then
    pm2 list | grep hyperbot
    echo ""
else
    echo "⚠️  PM2 not found, checking processes..."
    ps aux | grep -i "bot.py\|python.*app" | grep -v grep
    echo ""
fi

# Check logs
echo "🔍 2. CHECKING RECENT LOGS (Last 50 lines)..."
echo "════════════════════════════════════════════════════════════"
if [ -d "logs" ]; then
    latest_log=$(ls -t logs/bot_*.log 2>/dev/null | head -1)
    if [ -n "$latest_log" ]; then
        echo "📄 Log file: $latest_log"
        echo ""
        tail -50 "$latest_log"
    else
        echo "❌ No log files found in logs/ directory"
    fi
else
    echo "❌ logs/ directory not found"
fi
echo ""
echo "════════════════════════════════════════════════════════════"

# Check for errors
echo ""
echo "🔍 3. CHECKING FOR ERRORS (Last 20)..."
echo "════════════════════════════════════════════════════════════"
if [ -d "logs" ]; then
    latest_log=$(ls -t logs/bot_*.log 2>/dev/null | head -1)
    if [ -n "$latest_log" ]; then
        grep -i "error\|exception\|failed\|traceback" "$latest_log" | tail -20
    fi
fi
echo ""
echo "════════════════════════════════════════════════════════════"

# Check database connection
echo ""
echo "🔍 4. TESTING DATABASE CONNECTION..."
python3 -c "
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

async def test():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('❌ DATABASE_URL not found in .env')
        return
    
    try:
        import asyncpg
        conn = await asyncpg.connect(db_url, timeout=5)
        print('✅ Database connection: SUCCESS')
        await conn.close()
    except Exception as e:
        print(f'❌ Database connection: FAILED - {e}')

asyncio.run(test())
" 2>&1
echo ""

# Check API connectivity
echo "🔍 5. CHECKING HYPERLIQUID API..."
python3 -c "
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, '.')

try:
    from app.hl.hl_client import HyperLiquidClient
    import asyncio
    
    async def test():
        client = HyperLiquidClient()
        try:
            state = await client.get_account_state()
            print(f'✅ API connection: SUCCESS')
            print(f'   Account: \${state.get(\"marginSummary\", {}).get(\"accountValue\", 0):.2f}')
        except Exception as e:
            print(f'❌ API connection: FAILED - {e}')
    
    asyncio.run(test())
except Exception as e:
    print(f'❌ Error loading client: {e}')
" 2>&1
echo ""

# Check market data
echo "🔍 6. CHECKING MARKET DATA FEED..."
python3 -c "
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, '.')

symbol = os.getenv('SYMBOL', 'SOL')
print(f'   Symbol: {symbol}')

try:
    from app.hl.hl_client import HyperLiquidClient
    import asyncio
    
    async def test():
        client = HyperLiquidClient()
        try:
            market = await client.get_market_data(symbol)
            print(f'✅ Market data: SUCCESS')
            print(f'   Price: \${market.get(\"mark_price\", 0):.3f}')
            print(f'   24h Volume: \${market.get(\"volume_24h\", 0):,.0f}')
        except Exception as e:
            print(f'❌ Market data: FAILED - {e}')
    
    asyncio.run(test())
except Exception as e:
    print(f'❌ Error: {e}')
" 2>&1
echo ""

# Check .env configuration
echo "🔍 7. CHECKING .ENV CONFIGURATION..."
echo "════════════════════════════════════════════════════════════"
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    echo ""
    echo "Key configurations:"
    grep -E "^SYMBOL=|^BOT_MODE=|^MAX_LEVERAGE=|^POSITION_SIZE_PCT=|^DATABASE_URL=|^TELEGRAM_BOT_TOKEN=" .env | sed 's/=.*/=***/' | while read line; do
        key=$(echo "$line" | cut -d'=' -f1)
        if [ -n "$(grep "^${key}=" .env | cut -d'=' -f2-)" ]; then
            echo "   ✅ $key: SET"
        else
            echo "   ❌ $key: EMPTY"
        fi
    done
else
    echo "❌ .env file not found!"
fi
echo ""
echo "════════════════════════════════════════════════════════════"

# Check Python packages
echo ""
echo "🔍 8. CHECKING PYTHON PACKAGES..."
python3 -c "
packages = ['asyncpg', 'hyperliquid', 'telegram', 'pandas']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'   ✅ {pkg}')
    except ImportError:
        print(f'   ❌ {pkg} - MISSING')
"
echo ""

# Summary
echo "════════════════════════════════════════════════════════════"
echo "🎯 DIAGNOSTIC COMPLETE"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📋 Next steps based on findings:"
echo "   1. If database failing: Update DATABASE_URL in .env"
echo "   2. If API failing: Check API_SECRET and ACCOUNT_ADDRESS"
echo "   3. If no logs: Bot might not be running"
echo "   4. If no signals: Check SYMBOL (HYPE) has activity"
echo ""
echo "🔄 To restart bot:"
echo "   pm2 restart hyperbot"
echo "   # or"
echo "   pkill -f bot.py && python3 app/bot.py &"
echo ""
