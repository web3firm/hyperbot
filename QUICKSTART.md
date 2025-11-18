# 🚀 QUICK START GUIDE

## ⚡ Get Trading in 5 Minutes

### Step 1: Setup
```bash
./setup.sh
```

### Step 2: Configure Credentials
Edit `.env` file with your HyperLiquid credentials:
```bash
ACCOUNT_ADDRESS=0xYourMainAccount...
API_KEY=0xYourAPIWallet...
API_SECRET=0xYourPrivateKey...
```

### Step 3: Start Trading
```bash
python app/bot.py
```

That's it! The bot will:
- ✅ Connect to HyperLiquid
- ✅ Start scalping SOL with 2% TP / 1% SL / 5x leverage
- ✅ Log all trades to `data/trades/` for AI training
- ✅ Target 50-120 trades per day
- ✅ Apply full risk management (stop at 5% daily loss or 10% drawdown)

---

## 📊 Monitor Your Bot

### Real-time Logs
```bash
tail -f logs/bot_*.log
```

### Check Collected Trades
```bash
ls -lh data/trades/
```

### Generate Training Dataset (after 1,000+ trades)
```bash
python ml/training/dataset_builder.py
python ml/training/feature_engineering.py
```

---

## 🛡️ Safety Features Active

- **Pre-trade validation**: 8 safety checks before every order
- **Kill switch**: Auto-stop at 10% daily loss or 15% drawdown
- **Position limits**: Max 3 positions, 70% size each
- **Leverage limit**: Fixed 5x
- **Drawdown monitoring**: Auto-pause at 12% drawdown

---

## 📈 Strategy Details

**Base Scalping Strategy (Phase 1)**:
- Symbol: SOL-PERP
- Take Profit: +2%
- Stop Loss: -1%
- Leverage: 5x
- Position Size: 70% of capital
- Signal Cooldown: 30 seconds between trades

**Entry Conditions**:
- Minimum 0.1% momentum in direction
- No existing position
- Passes all risk checks

---

## 🤖 AI Evolution Path

### Phase 1: Data Collection (NOW)
Run bot to collect 1,000-3,000 trades

### Phase 2: Train AI Models
```bash
# Build dataset
python ml/training/dataset_builder.py

# Engineer features
python ml/training/feature_engineering.py

# Train model (coming soon)
python ml/training/trainer.py
```

### Phase 3: Switch to AI Mode
Edit `.env`:
```
BOT_MODE=ai
```

### Phase 4: Full Autonomy
AI learns from every trade and self-optimizes

---

## 🔧 Configuration

### Strategy Settings
Edit `config.yaml` to adjust:
- Take profit / stop loss percentages
- Position sizing
- Risk limits
- Trading frequency

### Environment Variables
Edit `.env` for:
- Exchange credentials
- Trading symbol
- Mode (rule_based/hybrid/ai)
- Leverage

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `app/bot.py` | Main trading bot |
| `app/strategies/rule_based/scalping_2pct.py` | Base strategy |
| `config.yaml` | Strategy configuration |
| `.env` | Credentials and settings |
| `data/trades/*.jsonl` | Trade logs for AI training |
| `logs/*.log` | System logs |

---

## ⚠️ Before Going Live

1. ✅ Test with small position sizes first
2. ✅ Monitor for at least 1 hour
3. ✅ Verify risk controls trigger correctly
4. ✅ Check trade logs are being saved
5. ✅ Confirm P&L tracking is accurate

---

## 🆘 Troubleshooting

### Bot won't start
- Check credentials in `.env`
- Verify HyperLiquid API wallet is approved
- Check Python dependencies: `pip install -r requirements.txt`

### No trades executing
- Check if kill switch triggered (see logs)
- Verify strategy parameters in `config.yaml`
- Check minimum momentum threshold

### Trades not logging
- Verify `data/trades/` directory exists
- Check disk space
- Review logs for errors

---

## 📞 Support

- Check logs first: `tail -f logs/bot_*.log`
- Review configuration: `config.yaml` and `.env`
- See full documentation in `README.md`

---

**Status**: ✅ Production Ready
**Mode**: Rule-Based → AI Evolution
**Target**: 50-120 trades/day
**Data Collection**: Automatic
