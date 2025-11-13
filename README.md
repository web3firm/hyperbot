# Hyperliquid Automated Trading Bot 🚀

A sophisticated automated trading bot for Hyperliquid DEX featuring advanced strategies, machine learning predictions, sentiment analysis, and comprehensive risk management.

## ⚠️ Disclaimer

**This bot is for educational and research purposes. Trading cryptocurrencies involves substantial risk of loss. Only use funds you can afford to lose. The authors are not responsible for any financial losses.**

## ✨ Features

### Trading Features
- **Multi-Strategy Trading**: Technical analysis, ML predictions, sentiment analysis
- **Risk Management**: Stop-loss, take-profit, position sizing, portfolio heat monitoring
- **Hybrid Exit Strategy**: Quick profits + ML-based scaling out
- **Portfolio Management**: Max 50% portfolio usage across 5 trades with 5x leverage
- **Advanced Position Management**: Partial exits, trailing stops, correlation analysis

### Technical Analysis
- **10+ Technical Indicators**: RSI, MACD, Bollinger Bands, Stochastic, Williams %R
- **Candlestick Pattern Recognition**: 15+ patterns including hammers, engulfing, stars
- **Multiple Timeframe Analysis**: 1m execution with 5m strategy confirmation
- **Support/Resistance Detection**: Dynamic pivot point calculation
- **Volume Analysis**: Volume-weighted price action signals

### Machine Learning
- **4 ML Models**: Random Forest, Gradient Boosting, Logistic Regression, SVM
- **Advanced Feature Engineering**: 50+ technical and time-based features
- **Ensemble Predictions**: Combined model predictions with confidence scoring
- **Auto-Retraining**: Models retrain every 24 hours with new data
- **Performance Tracking**: Model accuracy and performance monitoring

### Sentiment Analysis
- **Multi-Source Sentiment**: News, social media, Reddit discussions
- **Crypto-Specific Analysis**: Fear & Greed Index integration
- **Real-time Processing**: TextBlob + VADER sentiment analysis
- **Market Sentiment**: Volume and momentum sentiment indicators

### Risk Management
- **Portfolio Limits**: 10% per trade, max 5 trades, 50% total exposure
- **Dynamic Stop-Loss**: 2% stop-loss on all positions
- **Drawdown Protection**: 5% max portfolio drawdown limit
- **Daily Limits**: 3% daily loss limit with auto-shutdown
- **Correlation Analysis**: Avoid highly correlated positions

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Linux/macOS (Windows with WSL)
- Hyperliquid account with API access

### Quick Install
```bash
# Clone the repository
git clone https://github.com/web3firm/hyperbot.git
cd hyperbot

# Make install script executable and run
chmod +x install.sh
./install.sh

# Copy environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

### Manual Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p logs ml/models

# Copy and configure environment
cp .env.example .env
```

## ⚙️ Configuration

### Essential Settings (.env file)
```bash
# Your Hyperliquid credentials
PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=your_wallet_address_here

# Trading parameters
INITIAL_PORTFOLIO_PERCENTAGE=10.0  # 10% per trade
LEVERAGE=5                         # 5x leverage
MAX_TRADES=5                       # Max concurrent trades
STOP_LOSS_PERCENTAGE=2.0          # 2% stop loss

# Symbols to trade
SYMBOLS=ETH-USD,BTC-USD,SOL-USD

# Risk management
MAX_DRAWDOWN=5.0                  # 5% max drawdown
DAILY_LOSS_LIMIT=3.0             # 3% daily loss limit
```

### Trading Strategy Configuration
```bash
# Profit taking strategy
QUICK_PROFIT_THRESHOLD=2.0        # Take 40% profit at 2%
QUICK_PROFIT_EXIT_PERCENTAGE=40.0
ML_PROFIT_THRESHOLD_1=3.0         # Take 30% profit at 3%
ML_PROFIT_EXIT_1=30.0
ML_PROFIT_THRESHOLD_2=4.0         # Exit remaining at 4%

# ML Configuration
PREDICTION_CONFIDENCE_THRESHOLD=0.7
MODEL_RETRAIN_INTERVAL=24         # Retrain every 24 hours
```

## 🚀 Usage

### Setup and Testing
```bash
# Activate environment
source venv/bin/activate

# Run setup and testing script
python setup.py
```

This will show a menu with options:
1. **Run Backtest** - Test strategies on historical data
2. **Train ML Models** - Train models with historical data
3. **Test Market Analysis** - Test current market analysis
4. **Start Live Trading** - Begin live trading
5. **Exit** - Exit the application

### Live Trading
```bash
# Start the bot
python main.py
```

### Configuration Validation
The setup script will:
- Validate your API credentials
- Test connection to Hyperliquid
- Verify data retrieval
- Check all configurations

## 📊 Trading Logic

### Entry Conditions
1. **Technical Signal Strength** ≥ 60%
2. **Multiple Indicator Confluence**:
   - RSI oversold/overbought levels
   - MACD crossovers
   - Bollinger Band touches
   - Moving average alignments
   - Candlestick patterns

3. **ML Prediction** with >70% confidence
4. **Sentiment Confirmation** (30% weight)
5. **Risk Limits** not exceeded

### Exit Strategy
```
Position Entry (10% portfolio, 5x leverage)
    ↓
Quick Profit Check (2% PnL)
    ↓ (if 2%+ profit)
Exit 40% of position
    ↓
ML Analysis at 3%+ PnL
    ↓ (if confident exit signal)
Exit 30% of position
    ↓
ML Analysis at 4%+ PnL
    ↓
Exit remaining 30%

Stop Loss: -2% PnL = Close entire position
```

### Position Sizing Formula
```python
base_size = portfolio_value * 0.10  # 10% base
signal_adjusted = base_size * signal_strength
volatility_adjusted = signal_adjusted * volatility_factor
correlation_adjusted = volatility_adjusted / correlation_factor
final_size = min(correlation_adjusted, max_risk_per_trade)
leveraged_size = final_size * leverage
```

## 📈 Monitoring and Logging

### Real-time Monitoring
- Position PnL tracking
- Risk metric calculations
- Signal strength monitoring
- Market condition analysis

### Comprehensive Logging
```bash
# View live logs
tail -f logs/trading_bot.log

# Log levels: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

### Performance Metrics
- Total return %
- Sharpe ratio
- Maximum drawdown
- Win rate
- Average trade PnL
- Risk-adjusted returns

## 🔧 Advanced Features

### Machine Learning Pipeline
1. **Feature Engineering**: 50+ technical indicators and time features
2. **Model Training**: 4 ensemble models with cross-validation
3. **Prediction**: Confidence-weighted ensemble predictions
4. **Retraining**: Automated model updates every 24 hours

### Risk Management System
- **Portfolio Heat Monitoring**: Total exposure tracking
- **Correlation Analysis**: Avoid concentrated risk
- **Drawdown Protection**: Auto-shutdown on limits
- **Dynamic Position Sizing**: Volatility and correlation adjusted

### Sentiment Integration
- **Multi-source Analysis**: News, social media, market indicators
- **Real-time Processing**: Continuous sentiment updates
- **Signal Weighting**: 30% sentiment, 70% technical/ML

## 📁 Project Structure
```
hyperbot/
├── main.py                 # Main bot application
├── setup.py               # Setup and testing script
├── requirements.txt       # Python dependencies
├── .env.example          # Configuration template
├── install.sh            # Installation script
├── strategies/           # Trading strategies
│   ├── strategy_manager.py
│   └── __init__.py
├── ml/                   # Machine learning
│   ├── ml_predictor.py
│   ├── models/          # Trained models
│   └── __init__.py
├── sentiment/           # Sentiment analysis
│   ├── sentiment_analyzer.py
│   └── __init__.py
├── risk/               # Risk management
│   ├── risk_manager.py
│   └── __init__.py
├── utils/              # Utilities
│   ├── data_manager.py
│   ├── position_manager.py
│   └── __init__.py
└── logs/              # Log files
```

## 🛡️ Security Best Practices

1. **Environment Variables**: Never commit .env files
2. **Private Keys**: Use hardware wallets when possible
3. **API Permissions**: Limit to trading only
4. **Monitoring**: Set up alerts for unusual activity
5. **Testing**: Always test with small amounts first

## 🔧 Troubleshooting

### Common Issues

**Connection Errors**
```bash
# Check network connectivity
curl -I https://api.hyperliquid.xyz

# Verify credentials in .env file
grep PRIVATE_KEY .env
```

**TA-Lib Installation**
```bash
# Ubuntu/Debian
sudo apt-get install libta-lib-dev

# macOS
brew install ta-lib

# From source
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
# Follow manual installation steps
```

**Memory Issues**
```bash
# Reduce ML model complexity
# Adjust feature lookback period
FEATURE_LOOKBACK_PERIOD=50

# Reduce data cache size
# Implement in DataManager
```

### Debug Mode
```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# Run with verbose output
python main.py --verbose
```

## 📊 Performance Optimization

### Resource Usage
- **CPU**: Optimized for real-time analysis
- **Memory**: ~200MB typical usage
- **Network**: Minimal API calls with intelligent caching
- **Disk**: Log rotation, model persistence

### Scaling Considerations
- **Multiple Symbols**: Async processing for parallel analysis
- **High Frequency**: Websocket connections for real-time data
- **Large Portfolios**: Distributed processing capabilities

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Format code
black .
isort .
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Risk Warning

**IMPORTANT**: This software is for educational purposes only. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Only invest funds you can afford to lose entirely. The developers assume no responsibility for trading losses.

### Risk Factors
- **Market Volatility**: Crypto markets are highly volatile
- **Technical Risk**: Software bugs can cause losses  
- **API Risk**: Exchange downtime or API changes
- **Regulatory Risk**: Changing regulations may affect trading
- **Leverage Risk**: Amplified losses with leveraged positions

## 🙏 Acknowledgments

- [Hyperliquid](https://hyperliquid.xyz/) for the excellent DEX platform
- [TA-Lib](https://ta-lib.org/) for technical analysis functions
- [scikit-learn](https://scikit-learn.org/) for machine learning capabilities
- Open source community for various Python libraries

---

**Happy Trading! 🚀**

*Remember: Start small, test thoroughly, and never risk more than you can afford to lose.*