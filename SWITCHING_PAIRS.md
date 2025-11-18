# 🔄 Switching Trading Pairs

The bot is **fully pair-agnostic** and works with ANY HyperLiquid perpetual contract!

## ✨ How It Works

The system automatically:
- ✅ Loads metadata for all 221 HyperLiquid assets on startup
- ✅ Uses correct decimal precision for each asset (position size)
- ✅ Adjusts price rounding based on asset price range
- ✅ No hardcoded values - works with any symbol

## 🚀 To Switch Pairs

### 1. Edit `.env` file:
```bash
# Change this line:
SYMBOL=SOL

# To any HyperLiquid asset:
SYMBOL=BTC
SYMBOL=ETH
SYMBOL=MATIC
# ... or any other asset
```

### 2. Restart the bot:
```bash
kill $(pgrep -f "python app/bot.py")
nohup python app/bot.py > logs/bot_live.log 2>&1 &
```

### 3. Monitor:
```bash
./monitor.sh
```

## 📊 Popular Assets & Their Specs

| Symbol | Size Decimals | Max Leverage | Example Size |
|--------|---------------|--------------|--------------|
| **BTC** | 5 | 40x | 0.12345 BTC |
| **ETH** | 4 | 25x | 1.2345 ETH |
| **SOL** | 2 | 20x | 12.34 SOL |
| **MATIC** | 1 | 20x | 123.4 MATIC |
| **DOGE** | 0 | 10x | 1234 DOGE |
| **WIF** | 0 | 5x | 123 WIF |

## ⚙️ What Changes Automatically

When you switch symbols, the bot automatically adjusts:

### Position Sizing
- BTC: 5 decimal places (0.00001 BTC minimum)
- ETH: 4 decimal places (0.0001 ETH minimum)
- SOL: 2 decimal places (0.01 SOL minimum)
- DOGE: Whole numbers only (1 DOGE minimum)

### Price Precision
- High-priced assets ($100+): 2 decimals
- Mid-priced assets ($10-$100): 3 decimals
- Low-priced assets (<$10): 4 decimals

### Leverage Limits
The bot respects each asset's maximum leverage:
- Will use your configured MAX_LEVERAGE or asset's max (whichever is lower)
- Example: If MAX_LEVERAGE=20 but trading WIF (max 5x), bot uses 5x

## 🎯 Strategy Compatibility

The **Scalping 2%** strategy works with ALL assets because:
- Uses percentage-based targets (2% TP / 1% SL)
- No absolute price thresholds
- Momentum calculated as percentage change
- Position sizing based on account equity percentage

## 💡 Recommendations by Asset

### High Volume (Best for Scalping)
- ✅ **BTC, ETH, SOL** - Tight spreads, high liquidity
- Strategy: Use default 2% TP / 1% SL

### Medium Volume
- ⚠️ **MATIC, AVAX, ARB** - Good liquidity during US hours
- Strategy: Consider 3% TP / 1.5% SL for wider swings

### Low Volume / Memecoins
- 🚨 **DOGE, WIF, BONK** - Wider spreads, more volatile
- Strategy: Use 5% TP / 2% SL, reduce leverage to 3x or less

## 🔍 Check Available Assets

To see all tradeable assets:
```bash
python -c "
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.MAINNET_API_URL, skip_ws=True)
meta = info.meta()

for asset in meta['universe'][:20]:  # First 20
    print(f\"{asset['name']:8} | {asset['szDecimals']} decimals | {asset['maxLeverage']}x max\")
"
```

## ⚡ Quick Switch Examples

### Switch to Bitcoin:
```bash
# Edit .env
sed -i 's/SYMBOL=.*/SYMBOL=BTC/' .env

# Restart
kill $(pgrep -f "python app/bot.py") && nohup python app/bot.py > logs/bot_live.log 2>&1 &
```

### Switch to Ethereum:
```bash
sed -i 's/SYMBOL=.*/SYMBOL=ETH/' .env
kill $(pgrep -f "python app/bot.py") && nohup python app/bot.py > logs/bot_live.log 2>&1 &
```

### Switch to Polygon:
```bash
sed -i 's/SYMBOL=.*/SYMBOL=MATIC/' .env
kill $(pgrep -f "python app/bot.py") && nohup python app/bot.py > logs/bot_live.log 2>&1 &
```

## 🎯 No Code Changes Needed!

Everything is configured via environment variables. The entire codebase is pair-agnostic:
- ❌ No hardcoded "SOL" references in logic
- ❌ No fixed decimal places
- ❌ No asset-specific conditions
- ✅ 100% dynamic based on HyperLiquid metadata

**Just change SYMBOL in .env and restart!** 🚀
