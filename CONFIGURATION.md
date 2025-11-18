# Configuration Guide

All bot parameters are configurable via environment variables in `.env` file.
**No hardcoded values** - everything can be adjusted without code changes.

## Environment Variables Reference

### 🔐 HyperLiquid API (Required)

```env
API_SECRET=0xYourPrivateKey           # HyperLiquid API wallet private key
ACCOUNT_ADDRESS=0xYourMainAccount     # Main trading account address
TESTNET=false                         # Use testnet (true) or mainnet (false)
```

### 📊 Trading Configuration

```env
SYMBOL=SOL                            # Trading symbol (SOL, BTC, ETH, etc.)
BOT_MODE=rule_based                   # rule_based | hybrid | ai
MAX_LEVERAGE=5                        # Maximum leverage (1-50x)
```

### 🛡️ Risk Management

All percentages are relative to account value:

```env
MAX_DRAWDOWN_PCT=10.0                 # Maximum drawdown before auto-pause
MAX_DAILY_LOSS_PCT=5.0                # Maximum daily loss limit
STOP_LOSS_PCT=1.0                     # Stop loss per trade (%)
TAKE_PROFIT_PCT=2.0                   # Take profit per trade (%)
```

### 💰 Position Sizing

```env
MAX_POSITIONS=3                       # Maximum concurrent positions
POSITION_SIZE_PCT=70.0                # Position size as % of equity
MAX_POSITION_PCT_PER_TRADE=70.0       # Maximum size per single trade
RISK_PER_TRADE_PCT=2.0                # Risk per trade as % of account
```

### 📱 Telegram Notifications (Optional)

```env
TELEGRAM_BOT_TOKEN=                   # Leave empty to disable
TELEGRAM_CHAT_ID=                     # Your Telegram chat ID
```

### ⚙️ System Configuration

```env
LOG_LEVEL=INFO                        # DEBUG | INFO | WARNING | ERROR
```

## Configuration Strategy

### Conservative (Low Risk)
```env
MAX_LEVERAGE=3
MAX_DRAWDOWN_PCT=5.0
MAX_DAILY_LOSS_PCT=3.0
STOP_LOSS_PCT=0.5
TAKE_PROFIT_PCT=1.0
POSITION_SIZE_PCT=50.0
MAX_POSITIONS=2
```

### Moderate (Balanced)
```env
MAX_LEVERAGE=5
MAX_DRAWDOWN_PCT=10.0
MAX_DAILY_LOSS_PCT=5.0
STOP_LOSS_PCT=1.0
TAKE_PROFIT_PCT=2.0
POSITION_SIZE_PCT=70.0
MAX_POSITIONS=3
```

### Aggressive (High Risk)
```env
MAX_LEVERAGE=10
MAX_DRAWDOWN_PCT=15.0
MAX_DAILY_LOSS_PCT=8.0
STOP_LOSS_PCT=1.5
TAKE_PROFIT_PCT=3.0
POSITION_SIZE_PCT=90.0
MAX_POSITIONS=5
```

## How to Change Configuration

1. **Stop the bot** (if running):
   ```bash
   kill $(pgrep -f "python app/bot.py")
   ```

2. **Edit .env file**:
   ```bash
   nano .env
   ```

3. **Restart the bot**:
   ```bash
   python app/bot.py
   ```

## Where Values Are Used

| Parameter | Used In | Purpose |
|-----------|---------|---------|
| `MAX_LEVERAGE` | Strategy, Risk Engine | Controls position leverage |
| `STOP_LOSS_PCT` | Strategy | Calculates SL price |
| `TAKE_PROFIT_PCT` | Strategy | Calculates TP price |
| `POSITION_SIZE_PCT` | Strategy | Position sizing calculation |
| `MAX_DRAWDOWN_PCT` | Risk Engine, Kill Switch | Auto-pause trigger |
| `MAX_DAILY_LOSS_PCT` | Risk Engine, Kill Switch | Daily loss limit |
| `MAX_POSITIONS` | Risk Engine | Concurrent position limit |
| `RISK_PER_TRADE_PCT` | Risk Engine | Risk validation |

## Important Notes

⚠️ **All changes require bot restart** to take effect

⚠️ **No hardcoded values** - everything reads from .env

⚠️ **Backup .env** before making changes

✅ **Test changes on testnet** first (set `TESTNET=true`)

## Validation

Run verification after changing config:
```bash
python verify_system.py
```

All values will be logged on bot startup for confirmation.
