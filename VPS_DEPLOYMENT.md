# HyperBot - VPS Deployment Guide

## 🚀 Quick Start (Ubuntu/Debian VPS)

### 1. Initial Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip git -y

# Clone repository
git clone https://github.com/YOUR_USERNAME/hyperbot.git
cd hyperbot
```

### 2. Environment Setup
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuration
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required .env variables:**
```bash
# HyperLiquid
HYPERLIQUID_ACCOUNT_ADDRESS=0xYourAccountAddress
HYPERLIQUID_API_PRIVATE_KEY=0xYourPrivateKey
HYPERLIQUID_API_WALLET_ADDRESS=0xYourAPIWalletAddress

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_from_@BotFather
TELEGRAM_CHAT_ID=your_chat_id

# Trading Config
MAX_LEVERAGE=5
POSITION_SIZE_PCT=50.0
MAX_DAILY_LOSS_PCT=5.0
BOT_MODE=rule_based
SYMBOL=HYPE
```

### 4. Start Bot (Systemd Service - Recommended)

Create service file:
```bash
sudo nano /etc/systemd/system/hyperbot.service
```

Add this configuration:
```ini
[Unit]
Description=HyperBot Enterprise Trading System
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/hyperbot
Environment="PATH=/home/YOUR_USERNAME/hyperbot/venv/bin"
ExecStart=/home/YOUR_USERNAME/hyperbot/venv/bin/python -m app.bot
Restart=always
RestartSec=10
StandardOutput=append:/home/YOUR_USERNAME/hyperbot/logs/bot.log
StandardError=append:/home/YOUR_USERNAME/hyperbot/logs/error.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable autostart
sudo systemctl enable hyperbot

# Start bot
sudo systemctl start hyperbot

# Check status
sudo systemctl status hyperbot

# View logs
journalctl -u hyperbot -f
```

### 5. Alternative: Screen/Tmux Method
```bash
# Install screen
sudo apt install screen -y

# Start screen session
screen -S hyperbot

# Activate venv and run bot
cd /home/YOUR_USERNAME/hyperbot
source venv/bin/activate
python -m app.bot

# Detach: Ctrl+A, then D
# Reattach: screen -r hyperbot
# Kill session: screen -X -S hyperbot quit
```

### 6. Monitoring Commands
```bash
# View live logs
tail -f logs/bot_$(date +%Y%m%d).log

# Check bot process
ps aux | grep "app.bot"

# Check system resources
htop

# View recent trades
tail -50 logs/bot_$(date +%Y%m%d).log | grep "TRADE\|SIGNAL"
```

## 🔒 Security Best Practices

### Firewall Setup
```bash
# Enable UFW
sudo ufw enable

# Allow SSH (change 22 if using different port)
sudo ufw allow 22/tcp

# Check status
sudo ufw status
```

### SSH Key Authentication (Recommended)
```bash
# On your local machine, generate SSH key
ssh-keygen -t ed25519 -C "hyperbot@vps"

# Copy to VPS
ssh-copy-id user@your-vps-ip

# Disable password login (on VPS)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh
```

### Secure .env File
```bash
# Set proper permissions
chmod 600 .env
chmod 700 logs/
```

## 📊 Maintenance

### Update Bot
```bash
cd /home/YOUR_USERNAME/hyperbot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart hyperbot
```

### Backup Strategy
```bash
# Create backup script
nano backup.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR="/home/YOUR_USERNAME/hyperbot_backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/hyperbot_$DATE.tar.gz \
    /home/YOUR_USERNAME/hyperbot/logs/ \
    /home/YOUR_USERNAME/hyperbot/.env \
    /home/YOUR_USERNAME/hyperbot/data/

# Keep only last 7 days
find $BACKUP_DIR -name "hyperbot_*.tar.gz" -mtime +7 -delete
```

Make executable and schedule:
```bash
chmod +x backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/YOUR_USERNAME/hyperbot/backup.sh
```

### Log Rotation
```bash
sudo nano /etc/logrotate.d/hyperbot
```

Add:
```
/home/YOUR_USERNAME/hyperbot/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0644 YOUR_USERNAME YOUR_USERNAME
}
```

## 📱 Telegram Bot Commands

Once running, interact via Telegram:

- `/start` - Main control panel
- `/status` - Bot and account status
- `/positions` - Active positions
- `/trades` - Last 10 trades
- `/pnl` - Daily PnL breakdown
- `/stats` - Performance statistics

**Inline Buttons:**
- 🚀 START - Resume trading
- 🛑 STOP - Pause trading

## 🔧 Troubleshooting

### Bot Not Starting
```bash
# Check service logs
journalctl -u hyperbot -n 50 --no-pager

# Check Python errors
tail -50 logs/error.log

# Test manually
cd /home/YOUR_USERNAME/hyperbot
source venv/bin/activate
python -m app.bot
```

### High CPU/Memory Usage
```bash
# Check resource usage
htop

# Restart bot
sudo systemctl restart hyperbot
```

### Telegram Not Working
```bash
# Test bot token
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe

# Check chat ID
# Message your bot, then visit:
# https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

### Network Issues
```bash
# Test HyperLiquid connection
curl -s https://api.hyperliquid.xyz/info

# Check DNS
ping -c 3 api.hyperliquid.xyz

# Restart networking
sudo systemctl restart networking
```

## 📈 Performance Optimization

### For Low-Spec VPS (1GB RAM)
```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Enable Auto-Restart on Failure
The systemd service already includes `Restart=always`, but you can also add:
```bash
# Create watchdog script
nano watchdog.sh
```

Add:
```bash
#!/bin/bash
if ! pgrep -f "python -m app.bot" > /dev/null; then
    echo "Bot crashed, restarting..." >> /home/YOUR_USERNAME/hyperbot/logs/watchdog.log
    sudo systemctl restart hyperbot
fi
```

Schedule every 5 minutes:
```bash
chmod +x watchdog.sh
crontab -e
# Add: */5 * * * * /home/YOUR_USERNAME/hyperbot/watchdog.sh
```

## 🎯 Expected Results

**Enterprise System Performance:**
- 70% win rate target
- 2-5 trades per day (quality over quantity)
- 3:1 Risk:Reward ratio
- Real-time Telegram notifications
- Automatic position monitoring

**System Requirements:**
- VPS: 1GB RAM minimum, 2GB recommended
- CPU: 1 core minimum
- Storage: 10GB
- Network: 100 Mbps (crypto exchanges require low latency)

## 📞 Support

If issues persist:
1. Check logs: `journalctl -u hyperbot -f`
2. Test manually: `python -m app.bot`
3. Review Telegram messages for errors
4. Check account permissions on HyperLiquid

**Good luck trading! 🚀**
