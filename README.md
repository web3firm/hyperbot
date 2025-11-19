# 🤖 HyperBot - Automated Trading Bot for HyperLiquid DEX

[![Production Ready](https://img.shields.io/badge/status-production%20ready-success)](https://github.com/web3firm/hyperbot)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Enterprise-grade automated trading bot** combining rule-based strategies with machine learning for cryptocurrency futures trading on HyperLiquid DEX.

---

## ⚡ Quick Start

### **1. Clone & Install**
```bash
git clone https://github.com/web3firm/hyperbot.git
cd hyperbot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### **2. Configure**
```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

Required settings:
- `HYPERLIQUID_ACCOUNT` - Your trading wallet address
- `HYPERLIQUID_API_KEY` - API wallet address  
- `HYPERLIQUID_API_SECRET` - API wallet private key
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID
- `DATABASE_URL` - PostgreSQL connection (optional)

### **3. Start Trading**
```bash
# Using PM2 (recommended for production)
npm install -g pm2
pm2 start ecosystem.config.js
pm2 logs hyperbot

# Or using systemd
sudo cp hyperbot.service /etc/systemd/system/
sudo systemctl enable hyperbot
sudo systemctl start hyperbot
```

---

## 📊 Key Features

### **🎯 Trading Strategies**
- **Swing Trading (70%)** - Trend-following, 1-3% moves
- **Scalping (30%)** - Quick momentum, 0.4-0.8% moves
- **Breakout Detection** - Volume + price action
- **Mean Reversion** - Oversold/overbought bounces

### **🛡️ Risk Management**
- **Kill Switch** - Auto-stops at -5% daily loss
- **Drawdown Monitor** - 10% max from peak
- **Position Limits** - Max 2 positions, 5x leverage
- **Trailing Stop-Loss** - Locks profits at 7% PnL
- **Trailing Take-Profit** - Dynamic profit protection

### **📈 Analytics & Monitoring**
- **PostgreSQL Database** - Full trade history & analytics
- **Telegram Bot** - Real-time monitoring & control
- **ML Training** - Auto-retrains models on new data
- **Performance Metrics** - Win rate, P&L, strategy stats

---

## 🔧 Architecture

```
Main Loop (1s interval)
├─ Fetch Market Data (price, volume, indicators)
├─ Run All Strategies in Parallel
│  ├─ Swing Trader
│  ├─ Scalping Strategy
│  ├─ Breakout Strategy
│  └─ Mean Reversion Strategy
├─ Filter Valid Signals (confidence >70%)
├─ Risk Engine Validation
│  ├─ Check daily loss limit
│  ├─ Check position limits
│  ├─ Check leverage limits
│  └─ Check correlation
└─ Execute Trade if Approved

Monitoring Loops (parallel)
├─ Account Updates (5s) - equity, margin, positions
├─ Position Monitoring (1s) - SL/TP tracking, trailing
├─ Risk Checks (10s) - drawdown, kill switch
└─ ML Training (24h) - auto-retrain on new data
```

---

## 💬 Telegram Commands

### **Monitoring**
- `/status` - Bot status, account balance, uptime
- `/positions` - Active positions with live P&L
- `/trades` - Last 10 completed trades
- `/pnl` - Daily and weekly P&L breakdown
- `/stats` - Strategy performance statistics
- `/logs` - Recent bot logs (last 30 entries)

### **Analytics**
- `/analytics` - Full performance dashboard
- `/analytics daily` - Last 30 days breakdown
- `/analytics symbols` - Best trading pairs
- `/analytics hours` - Optimal trading hours
- `/analytics ml` - ML model accuracy
- `/dbstats` - Database health and statistics

### **Control**
- `/help` - Show all commands
- `/train` - Trigger ML model retraining
- 🚀 **START** button - Resume trading
- 🛑 **STOP** button - Pause trading

---

## 📁 Project Structure

```
hyperbot/
├── app/                  # Main application
│   ├── bot.py           # Master controller
│   ├── telegram_bot.py  # Telegram interface
│   ├── hl/              # HyperLiquid integration
│   ├── strategies/      # Trading strategies
│   ├── risk/            # Risk management
│   ├── database/        # PostgreSQL integration
│   └── utils/           # Utilities
├── ml/                  # Machine learning
├── config/              # Configuration files
├── logs/                # Log files
├── .env                 # Environment variables (not in git)
├── requirements.txt     # Python dependencies
├── ecosystem.config.js  # PM2 configuration
├── hyperbot.service     # Systemd service file
├── README.md            # This file
└── PRODUCTION_GUIDE.md  # Complete deployment guide
```

---

## 🎓 Documentation

- **[PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md)** - Complete deployment guide
  - Trading schedule & activity patterns
  - Strategy explanations
  - Risk management details
  - Performance expectations
  - Troubleshooting guide
  - Security best practices

- **[archive/old_docs/](archive/old_docs/)** - Historical documentation
  - Database migration notes
  - VPS deployment guides
  - Feature explanations

---

## ⚙️ Configuration

### **Trading Parameters** (config/trading_rules.yml)
```yaml
loop_interval: 0.5          # Main loop speed (seconds)
max_leverage: 5             # Maximum leverage
position_size_pct: 0.8      # % of balance per trade
max_positions: 2            # Concurrent positions limit
daily_loss_limit_pct: 5     # Kill switch trigger
```

### **Strategy Settings**
- **Swing Trading**: 1% SL, 3% TP, RSI + EMA
- **Scalping**: 0.4% SL, 0.8% TP, Quick momentum
- **Breakout**: Volume spike + price breakout
- **Mean Reversion**: RSI oversold/overbought

---

## 📊 Performance Targets

- **Win Rate**: 70% (target)
- **Risk-Reward**: 3:1 ratio
- **Daily Target**: +2-5% account growth
- **Max Daily Loss**: -5% (kill switch)
- **Trading Frequency**: 10-50 trades/day (varies)

---

## 🔐 Security

- ✅ API keys automatically masked in logs
- ✅ Tokens hidden: `8374468872:AAG...aOGI`
- ✅ HTTP requests sanitized
- ✅ No sensitive data in git repository
- ✅ Dedicated API wallet recommended

---

## 🆘 Support & Monitoring

### **Health Checks**
```bash
# Check bot status
pm2 status hyperbot
pm2 logs hyperbot --lines 50

# Check in Telegram
/status
/logs
```

### **Diagnostics**
```bash
# Run diagnostic script
./diagnose_vps.sh

# Check database
/dbstats  # in Telegram
```

### **Common Issues**
- **Not trading?** Check `/status` and `/logs` for errors
- **Kill switch active?** Check `/pnl` - may have hit -5% daily loss
- **Database issues?** Verify `DATABASE_URL` in `.env`

---

## ⚠️ Disclaimer

This bot is a **trading tool**, not financial advice:
- Cryptocurrency trading is highly risky
- Past performance does not guarantee future results
- Only trade with capital you can afford to lose
- Monitor the bot regularly
- Understand the strategies before deploying
- Start with small capital and testnet first

---

## 📈 Getting Started Guide

1. **Test on Testnet First**
   - Set `HYPERLIQUID_TESTNET=true` in `.env`
   - Use testnet tokens (free)
   - Verify all features work

2. **Start Small on Mainnet**
   - Begin with $50-100
   - Monitor for 24-48 hours
   - Verify P&L matches expectations

3. **Scale Gradually**
   - Increase capital slowly
   - Adjust position size (`POSITION_SIZE_PCT`)
   - Monitor risk metrics closely

4. **Stay Informed**
   - Check Telegram daily
   - Review `/analytics` weekly
   - Update bot regularly (`git pull`)

---

## 🚀 Next Steps

1. Read **[PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md)** for complete details
2. Set up your `.env` file with correct API keys
3. Test on testnet first
4. Deploy to production with small capital
5. Monitor via Telegram
6. Scale gradually as confidence grows

---

## 📞 Contact & Contributing

- **Issues**: [GitHub Issues](https://github.com/web3firm/hyperbot/issues)
- **Pull Requests**: Welcome! Please test thoroughly
- **Documentation**: Help improve guides

---

**Version**: 2.0 (Production Ready)  
**Last Updated**: November 19, 2025  
**License**: MIT

**⚡ Ready to trade? Let's go! 🚀**
