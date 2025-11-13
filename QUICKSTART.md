# 🚀 Hyperliquid Trading Bot - Quick Start Guide

## 📋 Prerequisites

1. **Python 3.8+** installed
2. **Hyperliquid account** with funds
3. **Private key** for your Hyperliquid wallet
4. **Basic understanding** of cryptocurrency trading risks

## 🛠️ Installation

### 1. Quick Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/web3firm/hyperbot.git
cd hyperbot

# Run the installation script
chmod +x install.sh
./install.sh
```

### 2. Manual Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p logs ml/models
```

## ⚙️ Configuration

### 1. Copy Environment File
```bash
cp .env.example .env
```

### 2. Edit Configuration
```bash
nano .env  # or use any text editor
```

**Essential settings:**
```env
PRIVATE_KEY=your_actual_private_key_here
WALLET_ADDRESS=your_wallet_address_here
SYMBOLS=ETH-USD,BTC-USD,SOL-USD
INITIAL_PORTFOLIO_PERCENTAGE=10.0
LEVERAGE=5
MAX_TRADES=5
STOP_LOSS_PERCENTAGE=2.0
```

### 3. Security Notes
- ⚠️ **Never commit your `.env` file**
- 🔐 Keep your private key secure
- 💰 Start with small amounts
- 📊 Test thoroughly before going live

## 🧪 Testing

### 1. Run Component Tests
```bash
# Test all components without API keys
python demo_test.py
```

### 2. Validate Setup
```bash
# Test with your actual configuration
python setup.py
```

Choose option 3 to test market analysis with your setup.

## 🎮 Usage

### 1. Start Live Trading
```bash
source venv/bin/activate  # Activate environment
python main.py
```

### 2. Monitor Logs
```bash
# In another terminal
tail -f logs/trading_bot.log
```

### 3. Using Setup Menu
```bash
python setup.py
```

**Menu Options:**
1. **Run Backtest** - Test strategies on historical data
2. **Train ML Models** - Train models with historical data
3. **Test Market Analysis** - Test current market conditions
4. **Start Live Trading** - Begin automated trading
5. **Exit** - Exit the program

## 📊 Trading Strategy Overview

### Entry Logic
1. **Technical Analysis** (70% weight)
   - 10+ indicators: RSI, MACD, Bollinger Bands, etc.
   - Candlestick patterns
   - Support/resistance levels
   - Multi-timeframe confirmation

2. **Machine Learning** (20% weight)
   - 4 ensemble models
   - 50+ engineered features
   - Confidence-based decisions

3. **Sentiment Analysis** (10% weight)
   - Multi-source sentiment
   - Market fear/greed index
   - Social media analysis

### Position Management
- **10% of portfolio** per trade
- **5x leverage** applied
- **Maximum 5 trades** (50% total exposure)
- **2% stop loss** on all positions

### Exit Strategy
```
Position Opened (10% portfolio, 5x leverage)
    ↓
2% Profit → Exit 40% of position (Quick Profit)
    ↓
3% Profit → ML Analysis → Exit 30% if confident
    ↓
4% Profit → Exit remaining 30%

-2% Loss → Close entire position (Stop Loss)
```

## ⚠️ Risk Management

### Automatic Protections
- **Maximum Drawdown**: 5% portfolio limit
- **Daily Loss Limit**: 3% daily limit
- **Position Size Limits**: Based on volatility and correlation
- **Exposure Monitoring**: Real-time portfolio heat tracking

### Manual Monitoring
- Monitor logs regularly
- Check positions daily
- Verify risk metrics
- Adjust settings as needed

## 🔧 Configuration Parameters

### Trading Parameters
```env
INITIAL_PORTFOLIO_PERCENTAGE=10.0    # Percentage per trade
LEVERAGE=5                           # Leverage multiplier
MAX_TRADES=5                         # Max concurrent positions
RISK_PER_TRADE=2.0                   # Risk per trade (%)
STOP_LOSS_PERCENTAGE=2.0             # Stop loss threshold
```

### Profit Taking
```env
QUICK_PROFIT_THRESHOLD=2.0           # Quick profit level
QUICK_PROFIT_EXIT_PERCENTAGE=40.0    # Exit percentage
ML_PROFIT_THRESHOLD_1=3.0            # First ML exit level
ML_PROFIT_EXIT_1=30.0               # First ML exit percentage
ML_PROFIT_THRESHOLD_2=4.0            # Final exit level
```

### Risk Management
```env
MAX_DRAWDOWN=5.0                     # Maximum portfolio drawdown
DAILY_LOSS_LIMIT=3.0                 # Daily loss limit
PREDICTION_CONFIDENCE_THRESHOLD=0.7   # ML confidence threshold
```

## 📈 Monitoring & Analytics

### Real-time Metrics
- Active positions and PnL
- Portfolio exposure and heat
- Risk scores and violations
- Signal strength and confidence

### Log Analysis
```bash
# View recent activity
tail -f logs/trading_bot.log

# Search for specific events
grep "TRADE" logs/trading_bot.log
grep "ERROR" logs/trading_bot.log
grep "Risk" logs/trading_bot.log
```

## 🚨 Troubleshooting

### Common Issues

**1. Connection Errors**
```bash
# Test network connection
curl -I https://api.hyperliquid.xyz

# Verify credentials
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Private Key:', 'SET' if os.getenv('PRIVATE_KEY') else 'NOT SET')
print('Wallet Address:', os.getenv('WALLET_ADDRESS', 'NOT SET'))
"
```

**2. TA-Lib Issues**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install libta-lib-dev

# macOS
brew install ta-lib

# Manual installation
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make && sudo make install
```

**3. Memory Issues**
- Reduce `FEATURE_LOOKBACK_PERIOD` to 50
- Use fewer symbols
- Restart the bot periodically

**4. API Rate Limits**
- Increase delays between API calls
- Use fewer symbols
- Monitor API usage

## 📊 Performance Optimization

### Resource Usage
- **CPU**: ~10-20% during analysis
- **Memory**: ~200-500MB typical
- **Network**: ~1-2 API calls per minute
- **Storage**: Log files rotate daily

### Scaling Tips
- Use SSD for faster model loading
- Increase RAM for more symbols
- Use multiple instances for different strategies
- Monitor system resources

## 🔄 Maintenance

### Daily Tasks
- Check log files for errors
- Monitor portfolio performance
- Verify active positions
- Review risk metrics

### Weekly Tasks
- Analyze trading performance
- Update configuration if needed
- Check for software updates
- Backup configuration files

### Monthly Tasks
- Review strategy performance
- Retrain ML models manually
- Update risk parameters
- Archive old log files

## 📞 Support & Community

### Getting Help
1. Check the troubleshooting section
2. Review log files for errors
3. Test components individually
4. Start with minimal configuration

### Best Practices
- Always test with small amounts first
- Monitor the bot closely initially
- Keep detailed records
- Regular backups of configuration
- Stay updated with Hyperliquid changes

## ⚖️ Legal & Risk Disclaimer

**IMPORTANT**: This software is for educational purposes only. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Only trade with funds you can afford to lose entirely.

The developers assume no responsibility for trading losses, technical failures, or any other damages resulting from the use of this software.

### Risk Factors
- Market volatility can cause significant losses
- Software bugs may result in unexpected trades
- API changes could disrupt functionality
- Regulatory changes may affect trading
- Leverage amplifies both gains and losses

---

**Remember**: Start small, test thoroughly, and never risk more than you can afford to lose! 🚀