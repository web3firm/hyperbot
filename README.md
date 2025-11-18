# HyperAI Trader

**Advanced Algorithmic Trading System with AI Evolution**

## 🎯 System Overview

HyperAI Trader is a complete trading system that evolves from rule-based strategies to fully autonomous AI trading:

- **Phase 1**: Rule-based scalping (2% TP / 1% SL / 5x leverage)
- **Phase 2**: Data collection from live trades (target: 1,000-3,000 trades)
- **Phase 3**: ML model training on execution history
- **Phase 4**: Hybrid AI + Rule-based validation
- **Phase 5**: Full autonomous AI trading

## 🏗️ Architecture

```
app/                    # Core trading application
├── bot.py             # Master orchestrator
├── portfolio_manager.py
├── position_controller.py
├── execution_router.py
├── exchanges/         # Exchange integrations
├── strategies/        # Rule-based → AI strategies
├── risk/             # Risk management
├── indicators/       # Technical indicators
├── orders/           # Order management (OCO, trailing stops)
├── monitoring/       # Dashboards and alerts
└── utils/            # Utilities

ml/                    # Machine Learning
├── models/           # AI models (Transformer, RL)
├── training/         # Training pipeline
├── inference/        # Live prediction
└── evaluation/       # Model comparison

data/                  # Data pipeline
├── raw/              # Raw market data
├── trades/           # Executed trade logs
└── model_dataset/    # ML training data

backtesting/          # Strategy testing
simulation/           # Paper trading
deployment/           # Docker, K8s configs
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run the Bot
```bash
python app/bot.py
```

## 📊 Current Strategy

**Base Scalping Strategy (2% / 1% / 5x)**:
- Symbol: SOL-PERP
- Take Profit: +2%
- Stop Loss: -1%
- Leverage: 5x
- Position Size: 70% of capital
- Target: 50-120 trades/day

## 🛡️ Safety Features

- Pre-trade risk validation
- Kill switch (8 emergency triggers)
- Drawdown monitoring
- Position limits
- Leverage limits
- Loss limits (5% daily, 10% total)
- Comprehensive logging

## 📈 Performance Monitoring

- Real-time metrics dashboard
- Telegram/Discord alerts
- Trade logging for AI training
- PnL visualization
- Error tracking

## 🤖 AI Evolution

After collecting 1,000+ trades:
1. Run `ml/training/dataset_builder.py`
2. Train models with `ml/training/trainer.py`
3. Switch bot to AI mode in config

## 📚 Documentation

See `/docs` for detailed documentation on:
- Exchange integration
- Strategy development
- Risk management
- AI training pipeline
- Deployment guides

## 🔧 Development

```bash
# Run tests
pytest tests/

# Run backtesting
python backtesting/engine.py

# Paper trading
python simulation/paper_trading_env.py
```

## 📝 License

Proprietary - All rights reserved

## 🤝 Support

For issues or questions, see documentation or contact support.
