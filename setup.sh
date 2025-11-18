#!/bin/bash
# HyperAI Trader - Setup Script
# Automated installation and configuration

echo "🚀 HyperAI Trader - Setup Starting..."
echo "======================================"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p data/raw data/processed data/trades data/model_dataset
mkdir -p logs
mkdir -p ml/models/checkpoints
mkdir -p backtesting/results
mkdir -p app/exchanges/hyperliquid app/exchanges/lighter
mkdir -p app/strategies/rule_based app/strategies/ai app/strategies/experimental

echo "✓ Directories created"

# Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠️  IMPORTANT: Edit .env with your credentials!"
else
    echo "✓ .env file exists"
fi

# Create __init__.py files
echo "📝 Creating Python package files..."
touch app/__init__.py
touch app/exchanges/__init__.py
touch app/exchanges/hyperliquid/__init__.py
touch app/exchanges/lighter/__init__.py
touch app/strategies/__init__.py
touch app/strategies/rule_based/__init__.py
touch app/strategies/ai/__init__.py
touch app/strategies/experimental/__init__.py
touch ml/__init__.py
touch ml/models/__init__.py
touch ml/training/__init__.py
touch ml/inference/__init__.py
touch ml/evaluation/__init__.py

echo "✓ Package files created"

# Set permissions
echo "🔐 Setting permissions..."
chmod +x app/bot.py
chmod +x ml/training/dataset_builder.py
chmod +x ml/training/feature_engineering.py

echo "✓ Permissions set"

# Verify installation
echo ""
echo "🔍 Verifying installation..."
python3 -c "import hyperliquid; print('✓ HyperLiquid SDK installed')"
python3 -c "import pandas; print('✓ Pandas installed')"
python3 -c "import numpy; print('✓ NumPy installed')"

echo ""
echo "======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env with your HyperLiquid credentials"
echo "2. Review config.yaml for strategy settings"
echo "3. Run: python app/bot.py"
echo ""
echo "For more information, see README.md"
echo ""
