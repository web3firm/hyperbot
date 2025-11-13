# 📱 Telegram Bot Setup Guide

## 🚀 Quick Setup

### 1. Create Telegram Bot
1. Message **@BotFather** on Telegram
2. Send `/newbot`
3. Choose a name: `Hyperbot Trading Controller`
4. Choose username: `your_hyperbot_controller_bot`
5. **Copy the bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrSTUvwxyz`)

### 2. Get Your User ID
1. Message **@userinfobot** on Telegram
2. **Copy your user ID** (looks like: `123456789`)

### 3. Configure Environment
Add to your `.env` file:
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
TELEGRAM_AUTHORIZED_USERS=123456789

# Notification Settings
TELEGRAM_NOTIFY_TRADES=true
TELEGRAM_NOTIFY_RISKS=true
TELEGRAM_NOTIFY_SYSTEM=true
TELEGRAM_DAILY_SUMMARY=true
```

### 4. Install Dependencies
```bash
pip install python-telegram-bot psutil
```

### 5. Start Telegram Bot Controller
```bash
python telegram_launcher.py
```

---

## 🎯 Features Overview

### **🎮 Remote Control**
- ▶️ Start/Stop trading bot
- 🆘 Emergency stop (closes all positions)
- ⚙️ Adjust trading parameters
- 📊 Real-time status monitoring

### **💰 Portfolio Management**
- 💼 Portfolio overview with charts
- 📋 Position management (close 25%, 50%, 75%, 100%)
- 📈 Performance tracking
- 💸 Risk analysis

### **🤖 ML & Analytics**
- 🧠 ML model status and retraining
- 📊 Live predictions with confidence scores
- 📈 Technical analysis results
- 😊 Sentiment analysis data

### **📱 Live Notifications**
- 🟢 Trade executions
- ⚠️ Risk alerts
- 📊 Daily P&L summaries
- 🚨 System alerts
- 🎯 ML predictions

### **📊 Advanced Features**
- 📈 Real-time chart generation
- 📋 Live log streaming
- 🎯 Symbol-specific analysis
- ⚡ Emergency position closure
- 🔄 Automatic daily summaries

---

## 📱 Bot Commands

### **Basic Controls**
- `/start` - Welcome and main menu
- `/status` - Bot status and positions
- `/portfolio` - Detailed portfolio view
- `/start_bot` - Start trading
- `/stop_bot` - Stop trading
- `/emergency_stop` - Emergency halt

### **Monitoring**
- `/logs` - View/stream live logs
- `/positions` - Manage individual positions
- `/charts` - Generate performance charts
- `/ml_status` - ML model information

### **Quick Buttons**
- 📊 Status - Quick status check
- 💰 Portfolio - Portfolio overview
- ▶️ Start - Start trading
- ⏹️ Stop - Stop trading
- 📈 Charts - View charts
- 📋 Logs - Live logs
- 🆘 Emergency - Emergency stop

---

## 🔧 Advanced Configuration

### **Multiple Users**
Add multiple authorized users:
```bash
TELEGRAM_AUTHORIZED_USERS=123456789,987654321,555666777
```

### **Custom Notifications**
Customize notification types:
```bash
TELEGRAM_NOTIFY_TRADES=true        # Trade execution alerts
TELEGRAM_NOTIFY_RISKS=true         # Risk management alerts  
TELEGRAM_NOTIFY_SYSTEM=true        # Bot status alerts
TELEGRAM_DAILY_SUMMARY=true        # End-of-day summaries
TELEGRAM_ML_PREDICTIONS=true       # ML prediction alerts
TELEGRAM_MARKET_ALERTS=true        # Market movement alerts
```

### **Notification Thresholds**
```bash
TELEGRAM_MIN_TRADE_VALUE=100       # Minimum trade value to notify
TELEGRAM_RISK_ALERT_LEVEL=5        # Risk score threshold for alerts
TELEGRAM_PNL_UPDATE_INTERVAL=3600  # PnL update interval (seconds)
```

---

## 🚨 Security Notes

### **Bot Security**
- ✅ Only authorized user IDs can access the bot
- ✅ Bot token should be kept secret
- ✅ Use environment variables, not hardcoded values
- ✅ Consider IP restrictions if running on VPS

### **API Security**
- ✅ Bot runs with same API credentials as main bot
- ✅ Can execute trades and close positions
- ✅ Emergency stop provides immediate control
- ✅ All actions logged for audit trail

---

## 🎮 Usage Examples

### **Start Trading Session**
1. Send `/start_bot` or tap "▶️ Start"
2. Bot confirms startup
3. Monitor with `/status` or "📊 Status"

### **Monitor Portfolio**
1. Send `/portfolio` or tap "💰 Portfolio"
2. View position details and charts
3. Use inline buttons to manage positions

### **Emergency Stop**
1. Send `/emergency_stop` or tap "🆘 Emergency"
2. Confirm emergency action
3. Bot stops trading and closes all positions

### **View Performance**
1. Send `/charts` or tap "📈 Charts"
2. Bot generates and sends performance charts
3. View portfolio distribution and P&L

---

## ⚡ Troubleshooting

### **Bot Not Responding**
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify bot is started with `/start`
- Check authorized user IDs

### **Permission Denied**
- Verify your user ID in `TELEGRAM_AUTHORIZED_USERS`
- Check environment variable spelling
- Restart bot after config changes

### **Trading Commands Failing**
- Ensure main trading bot API is configured
- Check Hyperliquid API credentials
- Verify network connectivity

### **Charts Not Generating**
- Install matplotlib: `pip install matplotlib seaborn`
- Check if positions exist for chart data
- Verify file permissions for temp chart files

---

## 🎯 Pro Tips

1. **Test with Small Amounts**: Start with minimal position sizes
2. **Monitor Closely**: Use live logs and status checks frequently  
3. **Emergency Preparedness**: Know how to use emergency stop
4. **Regular Health Checks**: Use `/status` to verify bot health
5. **Chart Analysis**: Review performance charts daily
6. **Risk Management**: Monitor risk alerts and portfolio heat
7. **ML Monitoring**: Check ML model performance regularly
8. **Backup Control**: Always have manual trading access ready

---

## 🔄 Running Multiple Bots

If running multiple trading bots:

### **Separate Bot Tokens**
```bash
# Bot 1 (Main)
TELEGRAM_BOT_TOKEN_1=token1
# Bot 2 (Backup)  
TELEGRAM_BOT_TOKEN_2=token2
```

### **Environment Isolation**
- Use different `.env` files
- Separate log directories
- Distinct database/model files
- Unique notification settings

---

This Telegram bot gives you complete remote control over your trading operations with enterprise-grade monitoring and emergency controls! 🚀