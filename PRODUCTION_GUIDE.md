# HyperBot - Production Deployment Guide

## 🤖 What is HyperBot?

HyperBot is an **enterprise-grade automated trading bot** for HyperLiquid DEX that combines rule-based strategies with machine learning for cryptocurrency futures trading. It features real-time risk management, PostgreSQL analytics, and Telegram monitoring.

---

## ⏰ Trading Schedule & Activity

### **Active Trading Hours**
- **24/7 Continuous Operation** - Bot runs around the clock
- **Main Loop**: Checks market every **1 second** for trading opportunities
- **Account Updates**: Every **5 seconds** (equity, margin, positions)
- **Position Monitoring**: Every **1 second** (stop-loss, take-profit tracking)
- **Risk Checks**: Every **10 seconds** (drawdown, kill-switch monitoring)

### **When Bot Becomes "Idle"**

The bot is **NEVER truly idle** - it's always monitoring. However, trading frequency varies:

#### **High Activity (Multiple Trades/Hour)**
- High volatility periods (news events, market moves >2%)
- Strong trending markets with clear signals
- Multiple strategies triggering simultaneously
- Volume spikes above 150% average

#### **Low Activity (Few Trades/Hour)**
- Low volatility consolidation (price range <0.5%)
- Weekend low-volume periods
- Conflicting signals causing trade rejection
- After reaching daily loss limits

#### **No Trading (Still Monitoring)**
- Kill switch activated (-5% daily loss)
- All positions at max leverage
- Risk engine rejecting all signals
- Extreme market conditions (>10% volatility spike)

### **Typical Trading Patterns**
```
00:00-04:00 UTC: Low activity (Asian night hours)
04:00-08:00 UTC: Moderate (Asian morning)
08:00-12:00 UTC: High activity (European open)
12:00-16:00 UTC: Peak activity (US market overlap)
16:00-20:00 UTC: Moderate (US afternoon)
20:00-24:00 UTC: Low-moderate (US evening)
```

**Note**: Actual trading depends on market conditions, not time schedules.

---

## 🎯 Trading Strategy

### **Strategy Mix (Enterprise Mode)**
1. **Swing Trading (70% allocation)**
   - Targets: 1-3% price moves
   - Duration: Minutes to hours
   - Stop-loss: 1% (5% PnL at 5x leverage)
   - Take-profit: 3% (15% PnL at 5x leverage)

2. **Scalping (30% allocation)**
   - Targets: 0.4-0.8% price moves
   - Duration: Seconds to minutes
   - Stop-loss: 0.4% (2% PnL at 5x leverage)
   - Take-profit: 0.8% (4% PnL at 5x leverage)

### **Trade Execution Logic**
```
Every 1 second:
├─ Fetch market data (price, volume, indicators)
├─ Run all strategies in parallel (4 strategies)
│  ├─ Swing Trader (trend-following)
│  ├─ Scalping (quick momentum)
│  ├─ Breakout (volume + price action)
│  └─ Mean Reversion (oversold/overbought)
├─ Filter valid signals (confidence >70%)
├─ Risk engine validation
│  ├─ Check daily loss limit (-5% max)
│  ├─ Check position limits (max 2 positions)
│  ├─ Check leverage (5x max)
│  └─ Check correlation (avoid similar positions)
└─ Execute if approved (success rate: ~70%)
```

---

## 📊 Performance Metrics

### **Target Performance**
- **Win Rate**: 70% (7 wins out of 10 trades)
- **Risk-Reward**: 3:1 (make $3 for every $1 risked)
- **Daily Target**: +2-5% account growth
- **Max Daily Loss**: -5% (kill switch activates)
- **Max Position Risk**: 1% of account per trade

### **Live Monitoring**
- **Loop Status**: Every 100 loops (~100 seconds)
- **Telegram Notifications**:
  - ⚠️ Risk warnings at -0.8% PnL
  - 🎯 Take-profit alerts at +1.6% PnL
  - 🚨 Emergency alerts for kill switch
  - 📊 Trade execution confirmations

---

## 🛡️ Risk Management

### **Multi-Layer Protection**

#### **1. Kill Switch (Emergency Stop)**
- Triggers at **-5% daily loss**
- Closes all positions immediately
- Prevents further trading until manual reset
- Telegram alert sent

#### **2. Drawdown Monitor**
- **Max Drawdown**: 10% from peak equity
- **Daily Loss Limit**: 5%
- **Recovery Mode**: Reduces position size by 50%

#### **3. Position Limits**
- **Max Positions**: 2 concurrent
- **Max Leverage**: 5x
- **Max Risk Per Trade**: 1% of account
- **Correlation Check**: Avoids similar positions

#### **4. Stop-Loss Protection**
- **Primary**: HyperLiquid stop-loss orders
- **Backup**: Bot monitors every 1 second
- **Trailing**: Activates at 7% PnL
  - Moves SL to breakeven +0.5% price
  - Locks minimum 2.5% PnL at 5x leverage

#### **5. Take-Profit Management**
- **Standard TP**: 3% price move (15% PnL at 5x)
- **Trailing TP** (at 10% PnL):
  - Moves TP from 3% to 2.4% price (12% PnL)
- **Aggressive TP** (at 12% PnL):
  - Moves TP to just 0.4% above current price
  - Locks ~12% PnL before reversal

---

## 🗄️ Database & Analytics

### **PostgreSQL Schema (NeonDB)**
```
Tables:
├─ trades (all executed trades)
├─ signals (ML training data with indicators)
├─ ml_predictions (AI model predictions)
├─ account_snapshots (equity history)
├─ performance_metrics (daily stats)
├─ market_data (OHLCV candles)
└─ system_events (bot events, errors)

Views:
├─ daily_performance (aggregated daily stats)
├─ symbol_performance (per-symbol breakdown)
├─ hourly_activity (best trading hours)
└─ ml_model_accuracy (AI model performance)
```

### **Analytics Features**
- **Real-time P&L tracking**
- **Win rate by strategy**
- **Best trading hours analysis**
- **Symbol performance comparison**
- **ML model accuracy monitoring**
- **Daily/weekly/monthly reports**

---

## 💬 Telegram Commands

### **Monitoring Commands**
```
/status      - Bot status, account balance, uptime
/positions   - Active positions with P&L
/trades      - Last 10 completed trades
/pnl         - Daily and weekly P&L breakdown
/stats       - Strategy performance statistics
/logs        - Recent bot logs (last 30 entries)
```

### **Analytics Commands**
```
/analytics          - Full performance dashboard
/analytics daily    - Last 30 days breakdown
/analytics symbols  - Best trading pairs
/analytics hours    - Optimal trading hours
/analytics ml       - ML model accuracy
/dbstats            - Database health and size
```

### **Control Commands**
```
/help    - Show all commands
/train   - Trigger ML model retraining
```

### **Inline Buttons**
- 🚀 **START** - Resume trading
- 🛑 **STOP** - Pause trading (emergency)

---

## 🚀 Production Deployment

### **1. VPS Requirements**
- **OS**: Ubuntu 22.04+ LTS
- **RAM**: 2GB minimum (4GB recommended)
- **CPU**: 2 cores minimum
- **Storage**: 20GB SSD
- **Network**: Stable connection (<50ms to exchange)

### **2. Environment Setup**

```bash
# Clone repository
git clone https://github.com/web3firm/hyperbot.git
cd hyperbot

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### **3. Configuration (.env)**

```bash
# Trading Settings
SYMBOL=HYPE                    # Trading symbol
BOT_MODE=rule_based           # Mode: rule_based, hybrid, ai
MAX_LEVERAGE=5                # Maximum leverage
POSITION_SIZE_PCT=0.8         # % of balance per trade

# HyperLiquid API
HYPERLIQUID_ACCOUNT=0x...     # Your trading account
HYPERLIQUID_API_KEY=0x...     # API wallet address
HYPERLIQUID_API_SECRET=0x...  # API wallet private key
HYPERLIQUID_TESTNET=false     # Use mainnet

# Telegram (required)
TELEGRAM_BOT_TOKEN=1234:ABC...   # From @BotFather
TELEGRAM_CHAT_ID=123456789       # Your chat ID

# Database (optional but recommended)
DATABASE_URL=postgresql://...    # NeonDB connection string
```

### **4. Start with PM2**

```bash
# Install PM2
npm install -g pm2

# Start bot
pm2 start ecosystem.config.js

# Monitor
pm2 logs hyperbot
pm2 monit

# Setup auto-restart on reboot
pm2 startup
pm2 save
```

### **5. System Service (Alternative)**

```bash
# Copy service file
sudo cp hyperbot.service /etc/systemd/system/

# Enable and start
sudo systemctl enable hyperbot
sudo systemctl start hyperbot

# Check status
sudo systemctl status hyperbot
sudo journalctl -u hyperbot -f
```

---

## 📁 Project Structure

```
hyperbot/
├── app/                          # Main application code
│   ├── bot.py                   # Master bot controller
│   ├── telegram_bot.py          # Telegram interface
│   ├── hl/                      # HyperLiquid integration
│   │   ├── hl_client.py        # API client
│   │   ├── hl_order_manager.py # Order execution
│   │   └── hl_websocket.py     # WebSocket feeds
│   ├── strategies/              # Trading strategies
│   │   ├── strategy_manager.py
│   │   └── rule_based/
│   │       ├── swing_trader.py
│   │       ├── scalping_2pct.py
│   │       ├── breakout.py
│   │       └── mean_reversion.py
│   ├── risk/                    # Risk management
│   │   ├── risk_engine.py
│   │   ├── kill_switch.py
│   │   └── drawdown_monitor.py
│   ├── database/                # PostgreSQL integration
│   │   ├── db_manager.py
│   │   ├── schema.sql
│   │   └── analytics.py
│   └── utils/                   # Utilities
│       ├── error_handler.py
│       └── trading_logger.py
├── ml/                          # Machine learning
│   ├── auto_trainer.py         # Automatic retraining
│   └── ml_predictor.py         # AI predictions
├── config/                      # Configuration
│   └── trading_rules.yml       # Strategy parameters
├── logs/                        # Log files
├── .env                         # Environment variables (not in git)
├── requirements.txt             # Python dependencies
├── ecosystem.config.js          # PM2 configuration
└── PRODUCTION_GUIDE.md         # This file
```

---

## 🔧 Maintenance

### **Daily Tasks**
- ✅ Check Telegram for alerts
- ✅ Review `/pnl` for daily performance
- ✅ Monitor `/dbstats` for database health

### **Weekly Tasks**
- ✅ Review `/analytics` for strategy performance
- ✅ Check logs for errors: `pm2 logs --lines 100`
- ✅ Verify database backups
- ✅ Review and adjust stop-loss levels if needed

### **Monthly Tasks**
- ✅ Analyze best trading hours (`/analytics hours`)
- ✅ Review symbol performance (`/analytics symbols`)
- ✅ Consider ML model retraining (`/train`)
- ✅ Update dependencies: `pip install -r requirements.txt --upgrade`

### **Common Issues**

#### **Bot Not Trading**
```bash
# Check bot status
pm2 status hyperbot
pm2 logs hyperbot --lines 50

# Check in Telegram
/status  # See if running
/logs    # Check for errors
```

#### **Database Connection Issues**
```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1"

# Check in Telegram
/dbstats  # Should show "Connected"
```

#### **Kill Switch Activated**
```bash
# Check Telegram for alert
/status  # Will show kill switch active

# Review what happened
/pnl     # Check daily loss

# Manually restart after fixing issue
# (Requires code modification or wait 24h)
```

---

## 🔐 Security Best Practices

### **API Keys**
- ✅ Use dedicated API wallet (not main trading account)
- ✅ Set withdrawal limits to zero
- ✅ Never commit `.env` to git
- ✅ Rotate keys every 90 days

### **Logs**
- ✅ Bot automatically masks sensitive data
- ✅ Tokens shown as: `8374468872:AAG...aOGI`
- ✅ API secrets shown as: `***MASKED***`
- ✅ HTTP logs suppressed (no token leaks)

### **Server Access**
- ✅ Use SSH keys (no passwords)
- ✅ Enable firewall (UFW)
- ✅ Regular system updates
- ✅ Monitor with fail2ban

---

## 📈 Expected Results

### **Realistic Expectations**
- **Good Day**: +2% to +5% account growth
- **Normal Day**: +0.5% to +2% account growth
- **Bad Day**: -1% to -5% account loss (kill switch at -5%)
- **Win Rate**: 65-75% (target: 70%)
- **Trading Frequency**: 10-50 trades per day (varies by volatility)

### **Not Financial Advice**
This bot is a **tool**, not a guaranteed profit machine:
- ⚠️ Crypto trading is highly risky
- ⚠️ Past performance ≠ future results
- ⚠️ Only trade with funds you can afford to lose
- ⚠️ Monitor the bot regularly
- ⚠️ Understand the strategies before deploying

---

## 🆘 Support & Development

### **Getting Help**
1. Check logs: `/logs` in Telegram or `pm2 logs`
2. Review error messages in `/status`
3. Check database: `/dbstats`
4. Review this guide's troubleshooting section

### **Contributing**
- Report bugs via GitHub issues
- Suggest features via pull requests
- Document any modifications
- Test thoroughly before deploying

### **Updates**
```bash
# Pull latest changes
cd /root/hyperbot
git pull

# Restart bot
pm2 restart hyperbot

# Monitor for issues
pm2 logs hyperbot
```

---

## 📋 Pre-Launch Checklist

Before deploying to production:

### **Configuration**
- [ ] `.env` file configured with correct values
- [ ] API keys tested on testnet first
- [ ] Database connection working (`/dbstats`)
- [ ] Telegram bot responding (`/help`)

### **Risk Settings**
- [ ] Max leverage set to comfortable level (default: 5x)
- [ ] Position size appropriate for account (default: 0.8%)
- [ ] Kill switch enabled and tested
- [ ] Stop-loss levels reviewed

### **Monitoring**
- [ ] PM2 installed and bot started
- [ ] Logs accessible via `/logs` command
- [ ] Telegram notifications working
- [ ] Database analytics accessible

### **Backup Plan**
- [ ] Know how to stop bot: `pm2 stop hyperbot`
- [ ] Manual position close method ready
- [ ] Emergency contact (exchange support) saved
- [ ] Backup of configuration files

---

## 🎓 Learning Resources

### **HyperLiquid DEX**
- Docs: https://hyperliquid.gitbook.io
- Testnet: https://app.hyperliquid-testnet.xyz
- Mainnet: https://app.hyperliquid.xyz

### **Trading Concepts**
- Risk Management: Position sizing, stop-loss, take-profit
- Technical Analysis: RSI, MACD, EMA, ADX indicators
- Leverage Trading: Understand liquidation prices
- Market Orders: Slippage and execution risks

### **Python & Async**
- asyncio: Concurrent programming
- Decimal: Precise financial calculations
- PostgreSQL: Database operations
- Telegram Bot API: Notification system

---

**Last Updated**: November 19, 2025
**Version**: 2.0 (Production Ready)
**Maintainer**: HyperBot Development Team

---

**⚡ Ready to deploy? Start with testnet first, then gradually move to mainnet with small capital. Good luck! 🚀**
