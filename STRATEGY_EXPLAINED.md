# 📊 Complete Trading Strategy Explanation

## 🎯 Strategy Overview: Scalping 2%

**Name**: Scalping 2% TP / 1% SL Strategy  
**Type**: Momentum-based scalping  
**Goal**: Catch short-term price movements with favorable risk/reward  
**Style**: High-frequency, quick in-and-out trades

---

## 📈 How Trades Are Taken - Step by Step

### **1. Data Collection (Every ~1 second)**

The bot continuously monitors market data:
```
Bot Loop → HyperLiquid API → Get Current Price
                           → Get Orderbook
                           → Get Volume
                           → Store in Memory
```

**What's tracked:**
- Last 20 prices (rolling buffer)
- Last 20 volumes (rolling buffer)  
- Current orderbook (bid/ask)
- Account balance & positions

---

### **2. Signal Generation Process**

Every loop cycle (~1 second), the strategy runs these checks:

#### **Check #1: Cooldown Timer** ⏱️
```python
if last_signal < 30 seconds ago:
    return None  # Wait at least 30s between signals
```
**Why**: Prevents over-trading and allows time for orders to execute

#### **Check #2: Data Sufficiency** 📊
```python
if len(recent_prices) < 10:
    return None  # Need at least 10 price points
```
**Why**: Need historical data to calculate momentum

#### **Check #3: Momentum Calculation** 📈
```python
price_10_ago = recent_prices[-10]
current_price = recent_prices[-1]
momentum_pct = ((current_price - price_10_ago) / price_10_ago) * 100
```

**Example:**
- Price 10 periods ago: $141.50
- Current price: $141.71
- Momentum: +0.15%

#### **Check #4: Signal Direction** 🎯
```python
if momentum_pct > +0.1%:
    signal = "LONG"  # Price rising
elif momentum_pct < -0.1%:
    signal = "SHORT"  # Price falling
else:
    return None  # Not enough momentum
```

**Threshold**: ±0.1% momentum required
- **LONG**: When price moved up 0.1% or more
- **SHORT**: When price moved down 0.1% or more

#### **Check #5: Position Check** 🔍
```python
if already_in_position(symbol):
    return None  # Only 1 position at a time
```

#### **Check #6: Position Size Calculation** 💰
```python
account_value = $47.14
collateral = account_value * 68% = $32.05
position_value = collateral * 5x leverage = $160.25
position_size = position_value / current_price

Example for HYPE @ $23.50:
position_size = $160.25 / $23.50 = 6.82 HYPE
```

#### **Check #7: Stop Loss & Take Profit** 🎲

**For LONG trades:**
```python
Entry: $23.50
Stop Loss: $23.50 * (1 - 1%) = $23.27
Take Profit: $23.50 * (1 + 2%) = $23.97
```

**For SHORT trades:**
```python
Entry: $23.50
Stop Loss: $23.50 * (1 + 1%) = $23.74
Take Profit: $23.50 * (1 - 2%) = $23.03
```

---

### **3. Risk Management Validation** 🛡️

Before placing the trade, multiple risk checks:

#### **Position Size Check**
```python
if position_size > 68% of equity:
    reject_signal("Position too large")
```

#### **Leverage Check**
```python
if leverage > MAX_LEVERAGE (5x):
    reject_signal("Leverage too high")
```

#### **Daily Loss Check**
```python
if daily_loss > 5%:
    reject_signal("Daily loss limit reached")
```

#### **Drawdown Check**
```python
if total_drawdown > 10%:
    reject_signal("Max drawdown exceeded")
```

---

### **4. Order Execution** 📤

If all checks pass:

```
1. Create market order with HyperLiquid
2. Set leverage to 5x
3. Place main order (entry)
4. Set stop-loss order (1% away)
5. Set take-profit order (2% away)
6. Log trade for AI training
```

**Order Example:**
```json
{
  "symbol": "HYPE",
  "side": "buy",
  "size": 6.82,
  "leverage": 5,
  "stop_loss": 23.27,
  "take_profit": 23.97
}
```

---

## ⏰ Timeframes & Candles

### **Current Implementation: TICK-BASED (Not Candle-Based)**

❗ **Important**: This strategy does NOT use traditional candlesticks!

Instead, it uses:
- **Live price ticks** (1-second updates)
- **Rolling 10-period lookback** (~10 seconds)
- **Continuous monitoring** (not waiting for candle close)

**Why tick-based?**
- ✅ Faster signal generation
- ✅ No waiting for candle close
- ✅ More trading opportunities
- ✅ Better for scalping

**Equivalent timeframe**: ~10-second momentum window

---

## 📊 Indicators Used

### **Current Strategy: MINIMAL INDICATORS**

The strategy is intentionally simple for reliable data collection:

#### **1. Momentum (Primary Indicator)**
```python
Calculation: (current_price - price_10_periods_ago) / price_10_periods_ago * 100
Threshold: ±0.1%
Usage: Entry signal generation
```

**What it measures**: Short-term price velocity

#### **2. Price Action**
```python
Data: Last 20 prices stored
Usage: Calculate momentum, detect reversals
```

#### **3. Position Tracking**
```python
Check: Open positions for symbol
Usage: Prevent multiple entries
```

### **No Traditional Indicators!**

❌ **NOT using:**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Moving Averages (SMA/EMA)
- Volume indicators
- ATR (Average True Range)

**Why so simple?**
- Purpose is data collection for AI
- AI will learn which conditions work
- Complex indicators come later with ML

---

## 🎲 Risk/Reward Profile

### **Per Trade Math**

**Risk/Reward Ratio**: 1:2 (risk 1% to make 2%)

**Example with $47.14 account:**
```
Collateral Used: $32.05 (68%)
Position Value: $160.25 (5x leverage)
Entry Price: $23.50

Potential Profit: $160.25 * 2% = $3.21 (6.8% account gain)
Potential Loss: $160.25 * 1% = -$1.60 (3.4% account loss)

Risk/Reward = $3.21 / $1.60 = 2.0:1
```

### **Win Rate Needed to Break Even**

With 2:1 R:R, need >33% win rate to profit:
```
If 50% win rate:
  10 trades → 5 wins, 5 losses
  Profit: (5 * $3.21) - (5 * $1.60) = $8.05
  Return: +17% on account
```

---

## 🔄 Complete Trade Lifecycle

### **1. Signal Generation** (10 seconds)
```
Monitor prices → Calculate momentum → Generate signal
```

### **2. Risk Validation** (<1 second)
```
Check position size → Check leverage → Check daily loss
```

### **3. Order Placement** (1-2 seconds)
```
Send to HyperLiquid → Set SL/TP → Confirm execution
```

### **4. Trade Management** (Minutes to Hours)
```
Monitor position → Wait for TP or SL to hit → Exit
```

### **5. Data Logging** (<1 second)
```
Log to data/trades/*.jsonl → Store for AI training
```

---

## 📊 Trade Frequency

**Expected per day:**
- **Minimum**: 20-50 trades
- **Average**: 50-100 trades  
- **Maximum**: 100-200 trades

**Depends on:**
- Market volatility (higher = more trades)
- Momentum frequency (how often price moves 0.1%+)
- Cooldown period (30 seconds between signals)
- Risk limits (daily loss, max positions)

**Calculation:**
```
Trading Day: 24 hours
Cooldown: 30 seconds minimum

Max Possible: (24 * 60 * 60) / 30 = 2,880 signals/day
Realistic: ~50-100 trades/day (2-4% of max)
```

---

## 🎯 Entry & Exit Conditions

### **Entry Conditions (ALL must be true)**

1. ✅ **No cooldown active** (>30s since last signal)
2. ✅ **Enough price data** (≥10 price points)
3. ✅ **Momentum exists** (±0.1% or more)
4. ✅ **No existing position** (max 1 at a time)
5. ✅ **Account has balance** (>$0)
6. ✅ **Position size valid** (<68% of equity)
7. ✅ **Risk checks pass** (leverage, daily loss, drawdown)

### **Exit Conditions (First to trigger)**

1. 🎯 **Take Profit Hit**: +2% from entry → Close with profit
2. 🛑 **Stop Loss Hit**: -1% from entry → Close with loss
3. ⚠️ **Kill Switch Triggered**: Emergency exit if:
   - Daily loss >5%
   - Drawdown >10%
   - Margin usage >90%

---

## 💡 Strategy Philosophy

### **Why This Design?**

1. **Simple is Better**
   - Easy to understand
   - Easy to debug
   - Consistent data for AI

2. **High Frequency**
   - More data points collected
   - Faster AI training
   - Better learning

3. **Fixed Risk/Reward**
   - Predictable outcomes
   - Easy to backtest
   - Clear statistics

4. **Momentum-Based**
   - Follows market flow
   - No predictions needed
   - Works in trends

---

## 🔮 What Happens Next (AI Evolution)

After collecting 1,000-3,000 trades, the AI will learn:

### **Phase 1: Current (Rule-Based)**
```
IF momentum > 0.1% THEN enter_long
IF momentum < -0.1% THEN enter_short
```

### **Phase 2: AI-Enhanced (Future)**
```
IF momentum > 0.1% 
   AND volatility = low
   AND hour = US_session
   AND volume > average
   AND ML_confidence > 70%
THEN enter_long
```

**The AI learns which conditions lead to winning trades:**
- Best hours to trade
- Best volatility regimes
- Best momentum levels
- Best position sizes
- When to skip trades

---

## 📈 Real Example: Trade Walkthrough

Let's trace an actual trade from start to finish:

### **T+0: Signal Check**
```
Time: 10:15:43 UTC
Symbol: HYPE
Account: $47.14
Positions: None

Recent Prices:
  10 periods ago: $23.50
  Current: $23.54
  
Momentum: ($23.54 - $23.50) / $23.50 * 100 = +0.17%
```
✅ Momentum > 0.1% → **LONG signal generated**

### **T+1: Position Calculation**
```
Collateral: $47.14 * 68% = $32.05
Position Value: $32.05 * 5x = $160.25
Size: $160.25 / $23.54 = 6.81 HYPE

Entry: $23.54
Stop Loss: $23.54 * 0.99 = $23.30
Take Profit: $23.54 * 1.02 = $24.01
```

### **T+2: Risk Validation**
```
✅ Position size: 68% < 69% limit
✅ Leverage: 5x = 5x limit
✅ Daily loss: 0% < 5% limit  
✅ Drawdown: 0% < 10% limit
```
**Risk check PASSED**

### **T+3: Order Execution**
```
Order sent to HyperLiquid:
  - Market buy 6.81 HYPE @ $23.54
  - Set 5x leverage
  - Place SL order @ $23.30
  - Place TP order @ $24.01
  
Order confirmed: ✅
Trade #1 opened
```

### **T+4: Trade Management**
```
Position open: 6.81 HYPE
Entry: $23.54
Current: $23.67 (+0.55%, floating profit)
Waiting for TP ($24.01) or SL ($23.30)...
```

### **T+5: Exit (Take Profit Hit!)**
```
Time: 10:47:22 UTC (31 minutes later)
Exit Price: $24.01
Profit: ($24.01 - $23.54) * 6.81 = $3.20
ROI: $3.20 / $32.05 collateral = +10% on collateral
Account: $47.14 → $50.34
```
✅ **Successful trade! +$3.20 profit**

### **T+6: Data Logging**
```json
{
  "timestamp": "2025-11-17T10:47:22Z",
  "signal": {
    "type": "long",
    "entry": 23.54,
    "size": 6.81,
    "momentum_pct": 0.17
  },
  "result": {
    "success": true,
    "pnl": 3.20,
    "duration_minutes": 31
  }
}
```
Logged to `data/trades/trades_20251117.jsonl` for AI training

---

## 🎓 Key Takeaways

1. **No Candles**: Uses live tick data, not candlesticks
2. **One Indicator**: Momentum (10-period price change)
3. **Fixed R:R**: Always 2:1 (2% TP / 1% SL)
4. **Fast Execution**: 30-second cooldown, high frequency
5. **Simple Logic**: Easy to understand, reliable data
6. **AI Ready**: All trades logged for machine learning

**The strategy is intentionally simple NOW to collect clean data. The AI will make it smarter LATER!** 🚀

---

## �� Quick Reference

| Parameter | Value | Why |
|-----------|-------|-----|
| **Timeframe** | ~10 ticks (~10s) | Fast scalping |
| **Leverage** | 5x | Amplify returns |
| **Position Size** | 68% equity | Conservative with buffer |
| **Take Profit** | +2% | Realistic target |
| **Stop Loss** | -1% | Limit losses |
| **Risk/Reward** | 2:1 | Favorable odds |
| **Momentum Threshold** | ±0.1% | Balance sensitivity |
| **Cooldown** | 30 seconds | Prevent over-trading |
| **Max Positions** | 1 | Focus & control |
| **Indicator Count** | 1 (momentum) | Simple = reliable |

