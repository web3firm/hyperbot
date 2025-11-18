# HyperBot VPS Deployment Guide

## 🚀 Quick Deployment (Your VPS is Already Running!)

Since your bot is already deployed, here's how to upgrade it with auto-restart:

### Option 1: PM2 (Recommended - Node.js based)

```bash
# On your VPS:
cd /path/to/hyperbot

# Pull latest changes
git pull origin main

# Install PM2 (if not installed)
npm install -g pm2

# Stop current bot (if running manually)
# Press Ctrl+C or kill the process

# Start with PM2
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
pm2 startup
# Follow the command it shows

# Check status
pm2 status
pm2 logs hyperbot
```

### Option 2: Systemd (Linux native)

```bash
# On your VPS:
cd /path/to/hyperbot

# Pull latest changes
git pull origin main

# Copy service file
sudo cp hyperbot.service /etc/systemd/system/

# Edit service file with correct paths
sudo nano /etc/systemd/system/hyperbot.service
# Replace %USER% with your username
# Replace /path/to/hyperbot with actual path

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable hyperbot

# Stop current bot (if running manually)
# Press Ctrl+C or kill the process

# Start with systemd
sudo systemctl start hyperbot

# Check status
sudo systemctl status hyperbot

# View logs
sudo journalctl -u hyperbot -f
```

### Option 3: Screen/Tmux (Simple, what you're probably using now)

```bash
# On your VPS:
cd /path/to/hyperbot

# Pull latest changes
git pull origin main

# Create wrapper script for auto-restart
cat > start.sh << 'EOF'
#!/bin/bash
while true; do
    python3 app/bot.py
    echo "Bot crashed, restarting in 10 seconds..."
    sleep 10
done
EOF

chmod +x start.sh

# Stop current bot (Ctrl+C in your screen session)

# Start with auto-restart
screen -S hyperbot
./start.sh
# Detach: Ctrl+A, D
```

---

## 🛡️ New Features Added:

### 1. **PM2 Process Manager**
- ✅ Auto-restart on crash
- ✅ Memory limit (500MB)
- ✅ Daily restart at 4am UTC
- ✅ Log rotation
- ✅ Monitoring dashboard

### 2. **Enhanced Error Handler**
- ✅ Telegram error notifications
- ✅ Consecutive error tracking
- ✅ Auto-recovery attempts
- ✅ Detailed error logging

### 3. **Deployment Script**
```bash
./deploy.sh install   # Install dependencies
./deploy.sh start     # Start bot
./deploy.sh stop      # Stop bot
./deploy.sh restart   # Restart bot
./deploy.sh status    # Check status
./deploy.sh logs      # View logs
```

---

## 📊 Monitoring Commands:

### PM2:
```bash
pm2 status              # Quick status
pm2 monit               # Real-time monitoring
pm2 logs hyperbot       # Stream logs
pm2 describe hyperbot   # Detailed info
pm2 restart hyperbot    # Restart
```

### Systemd:
```bash
sudo systemctl status hyperbot          # Status
sudo journalctl -u hyperbot -f          # Live logs
sudo systemctl restart hyperbot         # Restart
```

---

## 🚨 Error Notifications:

Your Telegram bot will now send:
- **Critical errors** with full context
- **Consecutive error warnings** (when 3+ errors in a row)
- **Recovery confirmations** (when errors clear)
- **Crash alerts** (if bot restarts)

---

## ✅ Health Checks:

The bot now tracks:
- Total errors
- Consecutive errors
- Last error time
- Health status (healthy/warning/critical)

Use `/status` command in Telegram to see health metrics.

---

## 🔄 Auto-Restart Scenarios:

Bot will auto-restart on:
1. **Crashes** - Python exceptions, segfaults
2. **Memory leaks** - Exceeds 500MB
3. **Network errors** - API disconnections
4. **Scheduled** - Daily at 4am UTC (optional)

---

## 💡 Recommended Setup:

**Best for reliability: PM2**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

This gives you:
- Web dashboard
- Process monitoring
- Auto-restart
- Log management
- Zero-downtime restarts

---

## 🆘 Troubleshooting:

**Bot keeps restarting?**
```bash
pm2 logs hyperbot --err --lines 100
# Check for repeated errors
```

**Can't connect to Telegram?**
- Check TELEGRAM_BOT_TOKEN in .env
- Verify bot is not blocked
- Check network connectivity

**High memory usage?**
```bash
pm2 monit
# Monitor memory in real-time
```

**Need to update code?**
```bash
git pull origin main
pm2 restart hyperbot
# Changes applied instantly
```

---

## 📞 Support:

If bot crashes repeatedly (5+ times), you'll get a Telegram alert.

Check logs immediately:
```bash
pm2 logs hyperbot --lines 200
# Or
tail -100 logs/bot_*.log
```

Common issues:
1. API key expired → Update .env
2. Network timeout → Check VPS connection
3. Memory limit → Increase PM2 limit
4. Exchange downtime → Bot will auto-retry

---

**Your bot is now BULLETPROOF! 🛡️**
