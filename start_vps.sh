#!/bin/bash
# ========================================
# HyperBot Enterprise - VPS Startup Script
# ========================================
# This script starts the bot on a VPS using systemd

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  HyperBot Enterprise - VPS Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Copy .env.example to .env and configure your credentials:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo -e "${RED}Error: Python 3.11+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create necessary directories
mkdir -p logs data backups ml/models

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/hyperbot.service"
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

echo -e "${YELLOW}Creating systemd service...${NC}"

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=HyperBot Enterprise Trading System
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$CURRENT_DIR/venv/bin/python -m app.bot
Restart=always
RestartSec=10
StandardOutput=append:$CURRENT_DIR/logs/bot.log
StandardError=append:$CURRENT_DIR/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable hyperbot

echo -e "${GREEN}✓ Systemd service created${NC}"

# Start the bot
echo -e "${YELLOW}Starting bot...${NC}"
sudo systemctl start hyperbot

# Wait a moment
sleep 3

# Check status
if sudo systemctl is-active --quiet hyperbot; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ Bot Started Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "View logs:"
    echo "  tail -f logs/bot_\$(date +%Y%m%d).log"
    echo ""
    echo "Check status:"
    echo "  sudo systemctl status hyperbot"
    echo ""
    echo "Stop bot:"
    echo "  sudo systemctl stop hyperbot"
    echo ""
    echo "Restart bot:"
    echo "  sudo systemctl restart hyperbot"
    echo ""
    echo "View live logs:"
    echo "  journalctl -u hyperbot -f"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ✗ Bot Failed to Start${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Check logs for errors:"
    echo "  journalctl -u hyperbot -n 50 --no-pager"
    echo "  tail -50 logs/error.log"
    exit 1
fi
