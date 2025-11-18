#!/bin/bash
# HyperAI Trader - Quick Launcher
# One-command start script

echo "🤖 HyperAI Trader - Starting..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Run: cp .env.example .env"
    echo "   Then edit .env with your credentials"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Virtual environment not found. Running setup..."
    ./setup.sh
fi

# Activate virtual environment
source .venv/bin/activate

# Check if dependencies are installed
if ! python -c "import hyperliquid" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the bot
echo "🚀 Starting trading bot..."
echo "   Mode: $(grep BOT_MODE .env | cut -d'=' -f2)"
echo "   Symbol: $(grep TRADING_SYMBOL .env | cut -d'=' -f2)"
echo "   Leverage: $(grep LEVERAGE .env | cut -d'=' -f2)x"
echo ""
echo "Press Ctrl+C to stop"
echo "================================"
echo ""

python app/bot.py
