# 🤖 HyperBot - Automated Trading Bot for HyperLiquid DEX

[![Production Ready](https://img.shields.io/badge/status-production%20ready-success)](https://github.com/web3firm/hyperbot)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Enterprise-grade automated trading bot** combining rule-based strategies with machine learning for cryptocurrency futures trading on HyperLiquid DEX.

## 🆕 Version 3.0 - Ultra-Lean SDK Integration

**Major upgrade using official HyperLiquid Python SDK:**
- **70% code reduction** in exchange integration (593 lines vs 1,970)
- **Atomic TP/SL orders** via `bulk_orders(grouping="normalTpsl")`
- **Direct SDK passthrough** for maximum execution speed
- **Client Order IDs (cloid)** for reliable order tracking
- **Dead man's switch** via `schedule_cancel()`

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
```env
ACCOUNT_ADDRESS=0x...        # Your trading wallet address
API_SECRET=0x...             # API wallet private key
SYMBOL=SOL                   # Trading pair (BTC, ETH, SOL, etc.)
MAX_LEVERAGE=5               # Leverage (1-50x)
TAKE_PROFIT_PCT=2.0          # Take profit % per trade
STOP_LOSS_PCT=1.0            # Stop loss % per trade
POSITION_SIZE_PCT=70         # % of balance per trade
TELEGRAM_BOT_TOKEN=...       # From @BotFather
TELEGRAM_CHAT_ID=...         # Your Telegram chat ID
DATABASE_URL=...             # PostgreSQL connection (optional)
```

### **3. Start Trading**
```bash
# Using PM2 (recommended for production)
npm install -g pm2
pm2 start ecosystem.config.js
pm2 logs hyperbot

# Or run directly
python -m app.bot
```

---

## 📊 Trading Strategies

### **Active Strategies (Enterprise Mode)**

| Strategy | Target Win Rate | R:R Ratio | Description |
|----------|----------------|-----------|-------------|
| **Swing Trading** | 70% | 3:1 | RSI + MACD + EMA + ADX confirmation, 5/8 signal score required |
| **Scalping/Momentum** | 65% | 2:1 | Trend + momentum + confirmation bars, 60s cooldown |

### **Strategy Filters (Quality over Quantity)**
- ✅ **ADX > 20** - Only trade in trending markets
- ✅ **Signal Score ≥ 5/8** - Multi-indicator confirmation
- ✅ **Trend Alignment** - Trade with the trend, not against
- ✅ **Support/Resistance** - Avoid buying at highs, selling at lows
- ✅ **Volume Confirmation** - 1.2x average volume minimum

### **Disabled Strategies** (Low win rate)
- ❌ Mean Reversion (37.5% win rate)
- ❌ Breakout (insufficient filters)
- ❌ Volume Spike (overtrading)

---

## 🛡️ Risk Management

### **Multi-Layer Protection**
```
Kill Switch
├─ Daily Loss: -5% → Stop trading
├─ Drawdown: -10% from peak → Pause
├─ Position Loss: -8% single position → Close
└─ Error Rate: >50% failed trades → Halt

Position Limits
├─ Max Positions: 3 concurrent
├─ Max Leverage: 5x (configurable)
├─ Position Size: 70% of balance (configurable)
└─ Margin Usage: <80%

Dynamic Trailing
├─ At 7% PnL: Move SL to breakeven + 2.5%
├─ At 10% PnL: Move TP closer (target 12%)
└─ At 12% PnL: Aggressive trailing near current price
```

---

## 🔧 Architecture

### **Core Components**
```
app/
├── bot.py                 # Master controller (1024 lines)
├── telegram_bot.py        # Telegram interface
├── hl/                    # HyperLiquid SDK Integration (593 lines total)
│   ├── hl_client.py       # SDK passthrough (178 lines)
│   ├── hl_order_manager.py # Atomic TP/SL orders (203 lines)
│   └── hl_websocket.py    # Real-time subscriptions (212 lines)
├── strategies/
│   ├── strategy_manager.py # Parallel strategy execution
│   ├── rule_based/         # Active strategies
│   │   ├── swing_trader.py # Primary (741 lines)
│   │   └── scalping_2pct.py # Secondary (259 lines)
│   └── core/               # Shared components
├── risk/
│   ├── risk_engine.py     # Pre-trade validation
│   ├── kill_switch.py     # Emergency stop
│   └── drawdown_monitor.py # Equity tracking
└── utils/
    ├── indicator_calculator.py # Shared indicators
    └── trading_logger.py       # Logging
```

### **Execution Flow**
```
Main Loop (1s interval)
├─ Fetch Market Data (candles, price, volume)
├─ Calculate Indicators Once (shared calculator)
│   └─ RSI, MACD, EMA, ADX, ATR, Bollinger Bands
├─ Run Strategies in Parallel
│   ├─ Swing Trader (primary)
│   └─ Scalping (secondary)
├─ Validate Signal with Risk Engine
│   ├─ Position limits
│   ├─ Margin availability
│   ├─ Daily loss check
│   └─ Drawdown limit
├─ Execute with Atomic TP/SL
│   └─ bulk_orders(grouping="normalTpsl")
└─ Track & Log for ML Training
```

---

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/status` | Bot status, account balance, uptime |
| `/positions` | Active positions with live P&L |
| `/trades` | Last 10 completed trades |
| `/pnl` | Daily and weekly P&L |
| `/stats` | Strategy performance stats |
| `/analytics` | Full performance dashboard |
| `/logs` | Recent bot logs |
| `/help` | All available commands |

**Control Buttons:**
- 🚀 **START** - Resume trading
- 🛑 **STOP** - Pause trading

---

## 📈 Performance Targets

| Metric | Target |
|--------|--------|
| Win Rate | 70% |
| Risk-Reward | 3:1 |
| Daily Target | +2-5% |
| Max Daily Loss | -5% (kill switch) |
| Max Drawdown | -10% |
| Trades/Day | 10-30 (quality focused) |

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

**Version**: 3.0 (Ultra-Lean SDK Integration)  
**Last Updated**: December 2, 2025  
**License**: MIT

**⚡ Ready to trade? Let's go! 🚀**
