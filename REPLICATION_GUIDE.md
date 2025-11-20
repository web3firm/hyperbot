# 🤖 HyperBot Replication Guide

**Complete step-by-step guide to create another trading bot from scratch**

Last Updated: November 19, 2025  
Tested: ✅ Production-ready template

---

## 📋 Prerequisites

### **Required Accounts**
1. **HyperLiquid Account**
   - Main trading wallet (MetaMask/WalletConnect)
   - API wallet (separate for bot access)
   - Get API credentials: https://app.hyperliquid.xyz/API

2. **NeonDB Account** (Recommended)
   - Sign up: https://neon.tech
   - Free tier: 0.5GB storage, perfect for trading bot
   - Region: Choose closest to your VPS

3. **Telegram Bot**
   - Create bot via @BotFather on Telegram
   - Get your chat ID from @userinfobot

4. **VPS/Server**
   - Ubuntu 22.04+ LTS
   - 2GB RAM minimum (4GB recommended)
   - 2 CPU cores minimum
   - Stable network connection

### **Development Tools**
- Python 3.11 or higher
- Git
- VS Code (optional but recommended)
- Node.js 18+ (for PM2)

---

## 🚀 Step-by-Step Setup

### **STEP 1: Clone and Setup Repository**

```bash
# 1.1 Clone the repository
git clone https://github.com/web3firm/hyperbot.git
cd hyperbot

# 1.2 Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 1.3 Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 1.4 Verify installation
python -c "import hyperliquid; print('✅ HyperLiquid SDK installed')"
python -c "import telegram; print('✅ Telegram bot installed')"
python -c "import asyncpg; print('✅ PostgreSQL driver installed')"
```

---

### **STEP 2: Create HyperLiquid API Wallet**

```bash
# 2.1 Go to HyperLiquid
# Visit: https://app.hyperliquid.xyz/API

# 2.2 Create new API wallet
# - Click "Create API Wallet"
# - Save the private key securely (YOU CAN'T RECOVER IT!)
# - Note the public address (0x...)

# 2.3 Connect API wallet to your trading account
# - Your main wallet approves the API wallet
# - Set permissions: Trading only (NO withdrawals)
# - Set max order size limits (optional safety)

# 2.4 Test on TESTNET first
# Visit: https://app.hyperliquid-testnet.xyz
# Get testnet tokens from faucet
# Create testnet API wallet same way
```

**Important:** Keep these safe:
- Main wallet address: `0x...` (your trading account)
- API wallet address: `0x...` (bot uses this)
- API wallet private key: `0x...` (NEVER share, keep secure)

---

### **STEP 3: Setup PostgreSQL Database (NeonDB)**

```bash
# 3.1 Create NeonDB account
# Visit: https://console.neon.tech/signup

# 3.2 Create new project
# - Click "New Project"
# - Name: "hyperbot-db" (or any name)
# - Region: Choose closest to your VPS
#   * Netherlands VPS → Europe (Frankfurt)
#   * US VPS → US East/West
# - Postgres version: 16 (latest)

# 3.3 Get connection string
# Copy the connection string (looks like):
# postgresql://user:pass@host.neon.tech/dbname?sslmode=require

# 3.4 Initialize database schema
# Download schema file
curl -O https://raw.githubusercontent.com/web3firm/hyperbot/main/app/database/schema.sql

# Apply schema
psql "YOUR_DATABASE_URL_HERE" -f app/database/schema.sql

# 3.5 Verify database
psql "YOUR_DATABASE_URL_HERE" -c "\dt"
# Should show 7 tables: trades, signals, ml_predictions, etc.
```

---

### **STEP 4: Create Telegram Bot**

```bash
# 4.1 Open Telegram and message @BotFather

# 4.2 Create new bot
/newbot

# Follow prompts:
# - Bot name: "My Trading Bot" (can be anything)
# - Bot username: "mytradingrobot_bot" (must end in 'bot')

# 4.3 Copy the token
# Looks like: 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789
# Save this token!

# 4.4 Get your Chat ID
# Message @userinfobot on Telegram
# Copy your user ID (looks like: 123456789)

# 4.5 Test bot
# - Click the link BotFather sends you
# - Send /start to your bot
# - Bot won't respond yet (we'll configure it next)
```

---

### **STEP 5: Configure Environment Variables**

```bash
# 5.1 Copy example env file
cp .env.example .env

# 5.2 Edit .env file
nano .env  # or use: code .env

# 5.3 Fill in all values
```

**Required .env configuration:**

```bash
# ============================================
# HYPERLIQUID SETTINGS
# ============================================
HYPERLIQUID_ACCOUNT=0xYourMainWalletAddress
HYPERLIQUID_API_KEY=0xYourAPIWalletAddress
HYPERLIQUID_API_SECRET=0xYourAPIWalletPrivateKey
HYPERLIQUID_TESTNET=false  # Use 'true' for testing

# ============================================
# TRADING PARAMETERS
# ============================================
SYMBOL=HYPE              # Trading pair (HYPE, SOL, BTC, ETH, etc)
BOT_MODE=rule_based      # Mode: rule_based, hybrid, ai
MAX_LEVERAGE=5           # Maximum leverage (1-50, recommend 5)
POSITION_SIZE_PCT=0.8    # % of balance per trade (0.1-1.0)

# ============================================
# TELEGRAM BOT (REQUIRED)
# ============================================
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789
TELEGRAM_CHAT_ID=123456789

# ============================================
# DATABASE (OPTIONAL BUT RECOMMENDED)
# ============================================
DATABASE_URL=postgresql://user:pass@host.neon.tech/dbname?sslmode=require

# ============================================
# RISK MANAGEMENT
# ============================================
DAILY_LOSS_LIMIT_PCT=5   # Kill switch at -5% daily loss
MAX_POSITIONS=2          # Maximum concurrent positions
POSITION_RISK_PCT=1      # Risk 1% of account per trade
```

**Save and close the file.**

---

### **STEP 6: Test Configuration**

```bash
# 6.1 Test database connection
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Testing database connection...')
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    result = await conn.fetchval('SELECT 1')
    await conn.close()
    print('✅ Database connected!' if result == 1 else '❌ Failed')

asyncio.run(test())
"

# 6.2 Test HyperLiquid connection
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Testing HyperLiquid connection...')
from hyperliquid.info import Info
info = Info(skip_ws=True)
try:
    meta = info.meta()
    print(f'✅ HyperLiquid connected! Found {len(meta[\"universe\"])} trading pairs')
except Exception as e:
    print(f'❌ Failed: {e}')
"

# 6.3 Test Telegram bot
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Testing Telegram bot...')
from telegram import Bot
import asyncio

async def test():
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
    try:
        await bot.send_message(
            chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            text='✅ Bot configuration test successful!'
        )
        print('✅ Telegram bot working! Check your messages.')
    except Exception as e:
        print(f'❌ Failed: {e}')

asyncio.run(test())
"
```

---

### **STEP 7: Start Bot Locally (Testing)**

```bash
# 7.1 Activate virtual environment (if not already active)
source .venv/bin/activate

# 7.2 Start bot
python app/bot.py

# 7.3 Watch the logs
# You should see:
# ✅ HyperLiquid client initialized
# ✅ Risk management initialized
# ✅ Database connected
# ✅ Telegram bot started
# 📊 Trading loop started

# 7.4 Test in Telegram
# Send to your bot:
/status   # Should show bot status
/help     # Should show all commands

# 7.5 Stop bot (when ready)
# Press Ctrl+C to stop
```

---

### **STEP 8: Deploy to VPS Production**

```bash
# 8.1 SSH into your VPS
ssh root@your-vps-ip

# 8.2 Install dependencies on VPS
apt update && apt upgrade -y
apt install -y python3.11 python3-pip python3-venv git nodejs npm postgresql-client

# 8.3 Install PM2
npm install -g pm2

# 8.4 Clone repository on VPS
cd /root
git clone https://github.com/web3firm/hyperbot.git
cd hyperbot

# 8.5 Setup Python environment on VPS
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 8.6 Configure .env on VPS
nano .env
# Copy your .env content from local machine
# Save and exit (Ctrl+X, Y, Enter)

# 8.7 Test on VPS
python app/bot.py
# Watch logs for a minute, then Ctrl+C to stop

# 8.8 Start with PM2
pm2 start ecosystem.config.js
pm2 logs hyperbot

# 8.9 Setup auto-restart on reboot
pm2 startup
pm2 save

# 8.10 Verify running
pm2 status
pm2 monit
```

---

### **STEP 9: Configure Systemd (Alternative to PM2)**

```bash
# 9.1 Create service file (if you prefer systemd over PM2)
sudo nano /etc/systemd/system/hyperbot.service

# 9.2 Paste this configuration:
```

```ini
[Unit]
Description=HyperBot Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/hyperbot
Environment="PATH=/root/hyperbot/.venv/bin"
ExecStart=/root/hyperbot/.venv/bin/python /root/hyperbot/app/bot.py
Restart=always
RestartSec=10
StandardOutput=append:/root/hyperbot/logs/systemd.log
StandardError=append:/root/hyperbot/logs/systemd.log

[Install]
WantedBy=multi-user.target
```

```bash
# 9.3 Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable hyperbot
sudo systemctl start hyperbot

# 9.4 Check status
sudo systemctl status hyperbot
sudo journalctl -u hyperbot -f  # Follow logs
```

---

### **STEP 10: Monitoring and Maintenance**

```bash
# 10.1 Monitor with PM2
pm2 logs hyperbot          # View logs
pm2 monit                  # Resource monitor
pm2 status                 # Check status
pm2 restart hyperbot       # Restart bot
pm2 stop hyperbot          # Stop bot

# 10.2 Monitor with Systemd
sudo systemctl status hyperbot
sudo journalctl -u hyperbot -f
sudo systemctl restart hyperbot

# 10.3 Telegram monitoring
# Send these commands to your bot:
/status      # Bot health
/positions   # Open positions
/pnl         # Profit/loss
/analytics   # Full dashboard

# 10.4 Check logs
tail -f logs/bot_$(date +%Y%m%d).log

# 10.5 Database health
/dbstats  # in Telegram
# or
psql $DATABASE_URL -c "SELECT COUNT(*) FROM trades;"

# 10.6 Diagnostics script
./diagnose_vps.sh
```

---

### **STEP 11: Update Bot**

```bash
# 11.1 SSH into VPS
ssh root@your-vps-ip
cd /root/hyperbot

# 11.2 Pull latest changes
git pull origin main

# 11.3 Update dependencies (if changed)
source .venv/bin/activate
pip install -r requirements.txt --upgrade

# 11.4 Restart bot
pm2 restart hyperbot
# or
sudo systemctl restart hyperbot

# 11.5 Monitor for issues
pm2 logs hyperbot --lines 100
# or  
sudo journalctl -u hyperbot -f
```

---

## 🔧 Common Customizations

### **Change Trading Symbol**

```bash
# Edit .env
nano .env

# Change this line:
SYMBOL=HYPE  # Change to: SOL, BTC, ETH, etc.

# Restart bot
pm2 restart hyperbot
```

### **Adjust Risk Settings**

```bash
# Edit .env
nano .env

# Modify these:
MAX_LEVERAGE=5              # Lower for less risk (1-3)
POSITION_SIZE_PCT=0.8       # Lower for smaller positions
DAILY_LOSS_LIMIT_PCT=5      # Lower to stop sooner (2-3%)
POSITION_RISK_PCT=1         # Risk per trade

# Restart bot
pm2 restart hyperbot
```

### **Change Strategy Mix**

Edit `config/trading_rules.yml`:

```yaml
strategies:
  enabled: true
  execution_mode: 'weighted'  # Options: best, weighted, round_robin, priority
  
  # Adjust weights (must total 100)
  weights:
    swing_trader: 70      # Change to 50 for less swing
    scalping_2pct: 30     # Change to 50 for more scalping
    breakout: 0           # Enable by setting > 0
    mean_reversion: 0     # Enable by setting > 0
```

---

## 🔐 Security Checklist

Before going live:

- [ ] API wallet has **NO withdrawal permissions**
- [ ] Tested on **testnet first**
- [ ] `.env` file **NOT committed to git**
- [ ] Strong VPS password or SSH key only
- [ ] Firewall enabled (UFW): `ufw enable`
- [ ] API keys masked in logs (automatically done)
- [ ] Telegram bot token kept secret
- [ ] Database credentials secure
- [ ] Regular backups enabled
- [ ] Kill switch configured (-5% loss limit)
- [ ] Position size tested with small capital first

---

## 📊 Expected Timeline

**Total Time: 2-4 hours**

- Prerequisites & accounts: 30-60 mins
- Clone & install: 15 mins
- Configuration: 30 mins
- Testing locally: 30 mins
- VPS deployment: 30 mins
- Monitoring setup: 15 mins
- Final testing: 30 mins

**Speed up by:**
- Having accounts ready (HyperLiquid, NeonDB, Telegram)
- Using testnet first
- Reading documentation beforehand

---

## 🎯 Pre-Launch Checklist

### **Before First Trade**

- [ ] Tested on testnet successfully
- [ ] All Telegram commands working (`/status`, `/help`, `/pnl`)
- [ ] Database connected (`/dbstats` shows "Connected")
- [ ] Account balance shown correctly in `/status`
- [ ] Kill switch configured (check `/status` shows limits)
- [ ] Start with **small capital** ($50-100)
- [ ] Monitor first 10-20 trades closely
- [ ] Understand how to **stop bot** (PM2 stop or Ctrl+C)

### **Trading Readiness**

- [ ] Understand stop-loss and take-profit levels
- [ ] Know when bot trades vs when it's idle
- [ ] Can read `/logs` to see what bot is doing
- [ ] Know how to check `/positions` and `/pnl`
- [ ] Emergency contact ready (exchange support)
- [ ] Backup plan if bot fails

---

## 🆘 Troubleshooting

### **Bot won't start**

```bash
# Check logs
pm2 logs hyperbot --lines 50

# Common issues:
# 1. Missing .env file → cp .env.example .env
# 2. Wrong Python version → python3 --version (need 3.11+)
# 3. Missing dependencies → pip install -r requirements.txt
# 4. Database connection → Test with psql $DATABASE_URL
```

### **Telegram bot not responding**

```bash
# Test token
python -c "
from telegram import Bot
import asyncio
bot = Bot('YOUR_TOKEN')
print(asyncio.run(bot.get_me()))
"

# Check chat ID is correct
# Message @userinfobot to verify your ID
```

### **Database errors**

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Re-run schema
psql $DATABASE_URL -f app/database/schema.sql

# Check in Telegram
/dbstats
```

### **No trades happening**

```bash
# Check logs
tail -f logs/bot_*.log

# Verify in Telegram:
/status  # Should show "ACTIVE"
/logs    # See what bot is doing

# Common reasons:
# - Low volatility (bot waiting for opportunities)
# - Risk engine blocking (check logs)
# - Kill switch active (check /status)
# - No signals meeting confidence threshold
```

---

## 📚 Additional Resources

### **HyperLiquid Documentation**
- Website: https://hyperliquid.xyz
- Docs: https://hyperliquid.gitbook.io
- Testnet: https://app.hyperliquid-testnet.xyz
- API Reference: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api

### **NeonDB Documentation**
- Console: https://console.neon.tech
- Docs: https://neon.tech/docs
- Pricing: https://neon.tech/pricing (Free tier sufficient)

### **Telegram Bot**
- BotFather: @BotFather on Telegram
- Documentation: https://core.telegram.org/bots

### **Bot Documentation**
- PRODUCTION_GUIDE.md - Complete deployment guide
- README.md - Quick start
- QUICK_REFERENCE.txt - Command cheat sheet

---

## 💡 Tips for Success

1. **Start Small**: Begin with $50-100 on mainnet
2. **Test on Testnet**: Always test major changes on testnet first
3. **Monitor Daily**: Check Telegram `/status` and `/pnl` daily
4. **Review Weekly**: Use `/analytics` to review strategy performance
5. **Understand the Bot**: Read logs, watch how it trades
6. **Be Patient**: Bot may not trade during low volatility
7. **Trust the Process**: 70% win rate means 30% losses are normal
8. **Keep Learning**: Review `/analytics hours` to find best trading times
9. **Stay Updated**: `git pull` regularly for improvements
10. **Have an Exit Plan**: Know how to stop bot and close positions

---

## ⚠️ Important Reminders

- **This is NOT financial advice**
- **Crypto trading is risky** - only use funds you can afford to lose
- **Past performance ≠ future results**
- **Bot can lose money** - kill switch protects at -5% but losses can happen
- **Monitor regularly** - don't set and forget
- **Start with testnet** - practice before real money
- **Understand the strategies** - read PRODUCTION_GUIDE.md
- **Keep API keys safe** - never share private keys
- **Use dedicated API wallet** - not your main trading wallet

---

## 🎓 What You've Built

Congratulations! You now have:

✅ **Automated trading bot** running 24/7  
✅ **Multi-strategy system** (Swing + Scalping)  
✅ **Advanced risk management** (Kill switch, drawdown monitor)  
✅ **Real-time monitoring** via Telegram  
✅ **Full analytics** with PostgreSQL database  
✅ **Production-grade deployment** with PM2/Systemd  
✅ **Security hardened** (masked tokens, no withdrawal access)  
✅ **Complete documentation** for maintenance  

---

## 📝 Final Checklist

Before considering setup complete:

- [ ] Bot running on VPS with PM2 or Systemd
- [ ] Telegram commands working (`/status`, `/help`, `/pnl`, `/logs`)
- [ ] Database connected and logging trades
- [ ] Started with small capital for testing
- [ ] Monitoring via Telegram daily
- [ ] Know how to stop bot if needed
- [ ] Understand risk management (kill switch, stop-loss)
- [ ] Read PRODUCTION_GUIDE.md completely
- [ ] Saved all credentials securely
- [ ] Git repository cloned and can update easily

---

**🎉 You're Ready to Trade!**

Remember: Start small, monitor closely, scale gradually. Good luck! 🚀

---

**Document Version**: 1.0  
**Last Updated**: November 19, 2025  
**Compatible With**: HyperBot v2.0+  
**Tested On**: Ubuntu 22.04 LTS, Python 3.11+

---

**Need Help?**
- Check logs: `pm2 logs hyperbot` or `/logs` in Telegram
- Run diagnostics: `./diagnose_vps.sh`
- Review documentation: PRODUCTION_GUIDE.md
- Test configuration: Use test scripts in Step 6

**Happy Trading! 📈💰**
