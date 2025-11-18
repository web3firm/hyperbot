# 🚀 HyperBot Enterprise - Quick Start

**Enterprise-level trading bot with 70% win rate target, Telegram controls, and VPS deployment.**

---

## ⚡ Quick Deploy to VPS (5 Minutes)

### 1. Clone & Configure
```bash
# On your VPS
git clone https://github.com/YOUR_USERNAME/hyperbot.git
cd hyperbot

# Copy and edit config
cp .env.example .env
nano .env
```

**Edit `.env` with your credentials:**
- HyperLiquid: Account address, API private key, wallet address
- Telegram: Bot token (from @BotFather), Chat ID (from @userinfobot)

### 2. Start Bot
```bash
# Run automated setup
./start_vps.sh
```

That's it! Bot is running with systemd auto-restart.

---

## 📱 Telegram Commands

Once running, control via Telegram:

- `/start` - Main control panel with buttons
- `/status` - Account & bot status
- `/positions` - Active positions  
- `/trades` - Last 10 trades
- `/pnl` - Daily PnL breakdown
- `/stats` - Performance statistics

**Emergency Controls:**
- 🚀 **START** button - Resume trading
- 🛑 **STOP** button - Pause trading (closes no positions, just stops new entries)

---

## 🎯 System Features

### Trading System
- **70% Win Rate Target** (vs 37.5% baseline)
- **2 Professional Strategies:**
  - Swing Trading: RSI + MACD + EMA + Bollinger + ADX filters
  - Improved Scalping: 0.3% momentum + trend + confirmation
- **3:1 Risk/Reward Ratio**
- **2-5 trades/day** (quality over quantity)

### Risk Management
- Leverage: 5x (adjustable)
- Position Size: 50% per trade
- Stop Loss: 1% PnL max loss
- Take Profit: 3% PnL target
- Daily Loss Limit: 5%
- Auto-pause at 12% drawdown

### Monitoring
- Real-time Telegram notifications
- Position P&L warnings
- Trade execution alerts
- Emergency kill switch
- Automatic logging

---

## 📊 Management Commands

```bash
# Check bot status
./check_bot.sh

# View live logs
tail -f logs/bot_$(date +%Y%m%d).log

# Restart bot
sudo systemctl restart hyperbot

# Stop bot
sudo systemctl stop hyperbot

# View systemd logs
journalctl -u hyperbot -f

# Check account
python3 -c "from app.hl.hl_client import *; # check balance"
```

---

## 🔧 Configuration Options

Edit `.env` to customize:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SYMBOL` | HYPE | Trading symbol |
| `MAX_LEVERAGE` | 5 | Leverage (1-50x) |
| `POSITION_SIZE_PCT` | 50 | % of account per trade |
| `MAX_DAILY_LOSS_PCT` | 5 | Daily loss limit % |
| `STOP_LOSS_PCT` | 1.0 | Stop loss % PnL |
| `TAKE_PROFIT_PCT` | 3.0 | Take profit % PnL |

---

## 📈 Expected Performance

**Enterprise System (Current):**
- Win Rate: 70% target
- R:R: 3:1
- Trades/Day: 2-5
- Fees: <20% of profit

**Example 100 Trades:**
- 70 wins @ +3% = +210%
- 30 losses @ -1% = -30%
- **Net: +180% gain**

**With $42.49:**
- 70% @ 3:1 → $120 → $340 → $950 over time

---

## 🛡️ Security Best Practices

### On VPS:
```bash
# Setup firewall
sudo ufw enable
sudo ufw allow 22/tcp

# Secure .env
chmod 600 .env

# SSH key only (disable password)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh
```

### Backups:
```bash
# Auto-backup script (daily at 2 AM)
chmod +x backup.sh
crontab -e
# Add: 0 2 * * * /path/to/hyperbot/backup.sh
```

---

## 🐛 Troubleshooting

### Bot Won't Start
```bash
# Check logs
journalctl -u hyperbot -n 50 --no-pager
tail -50 logs/error.log

# Test manually
cd /path/to/hyperbot
source venv/bin/activate
python -m app.bot
```

### Telegram Not Working
```bash
# Test bot token
curl https://api.telegram.org/bot<TOKEN>/getMe

# Get chat ID
# Message your bot, then:
curl https://api.telegram.org/bot<TOKEN>/getUpdates
```

### High Resource Usage
```bash
# Check resources
htop

# Restart bot
sudo systemctl restart hyperbot

# Add swap (1GB RAM VPS)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📦 Requirements

- **VPS:** 1GB RAM minimum, 2GB recommended
- **Python:** 3.11+
- **Storage:** 10GB
- **Network:** 100 Mbps
- **OS:** Ubuntu 20.04+ or Debian 11+

---

## 🎯 Roadmap

**Current: V1 Enterprise (70% Target)**
- ✅ Swing + Scalping strategies
- ✅ Technical indicators (RSI, MACD, EMA, BB, ADX)
- ✅ Telegram bot with controls
- ✅ Risk management
- ✅ VPS deployment

**Future: V2 AI Integration**
- AI model training on collected data
- Hybrid rule + AI validation
- Multi-timeframe analysis
- Portfolio optimization

---

## 📞 Support

**Common Issues:**
1. Check `.env` credentials
2. Review logs: `tail -f logs/bot_*.log`
3. Test HyperLiquid connection: `curl -s https://api.hyperliquid.xyz/info`
4. Verify Telegram: `/status` command

**Resources:**
- [VPS_DEPLOYMENT.md](VPS_DEPLOYMENT.md) - Full deployment guide
- [BOT_EXPLANATION.md](BOT_EXPLANATION.md) - System architecture
- Logs: `logs/bot_YYYYMMDD.log`

---

## ⚖️ Disclaimer

Trading cryptocurrencies carries risk. This bot is for educational purposes. Past performance does not guarantee future results. Trade responsibly and only with funds you can afford to lose.

**USE AT YOUR OWN RISK.**

---

## 📄 License

MIT License - See LICENSE file

---

**Good luck trading! 🚀**

*Remember: Quality over quantity. Let the bot do its job. Check results tomorrow!*
