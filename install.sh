#!/bin/bash

# Hyperliquid Trading Bot Installation Script

echo "Installing Hyperliquid Trading Bot..."
echo "===================================="

# Check if Python 3.8+ is installed
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    echo "✓ Python $python_version is installed"
else
    echo "✗ Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install system dependencies for TA-Lib
echo "Installing system dependencies..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update
    sudo apt-get install -y build-essential wget
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install ta-lib
fi

# Download and install TA-Lib from source (for Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Installing TA-Lib from source..."
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr
    make
    sudo make install
    cd ..
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
fi

# Install Python requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create logs directory
mkdir -p logs

# Create ml/models directory
mkdir -p ml/models

# Set permissions
chmod +x setup.py

echo ""
echo "Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Copy your environment variables:"
echo "   cp .env.example .env"
echo ""
echo "2. Edit the .env file with your credentials:"
echo "   nano .env"
echo ""
echo "3. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "4. Run the setup script:"
echo "   python setup.py"
echo ""
echo "5. Start the bot:"
echo "   python main.py"
echo ""
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "   - Never commit your .env file to version control"
echo "   - Keep your private keys secure"
echo "   - Start with small amounts for testing"
echo "   - Monitor the bot closely during initial runs"
echo ""