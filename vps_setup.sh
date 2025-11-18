#!/bin/bash
# VPS Setup Script for HyperBot
# Run this ONCE on your VPS after first login

echo "🚀 Setting up HyperBot VPS environment..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required tools
echo "🔧 Installing required tools..."
sudo apt install -y screen git python3 python3-pip python3-venv

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Make scripts executable
chmod +x check_bot.sh

echo ""
echo "✅ VPS Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Configure your .env file with your API keys"
echo "2. Run bot in screen session:"
echo "   screen -S hyperbot"
echo "   python3 -m app.bot"
echo "   Press Ctrl+A then D to detach"
echo ""
echo "3. Reattach to session:"
echo "   screen -r hyperbot"
echo ""
echo "4. List all sessions:"
echo "   screen -ls"
echo ""
echo "5. Kill session:"
echo "   screen -XS hyperbot quit"
