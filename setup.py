import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import HyperliquidTradingBot
from utils.data_manager import DataManager
from ml.ml_predictor import MLPredictor
from loguru import logger
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta

load_dotenv()

async def backtest_strategy():
    """Run backtest on historical data"""
    logger.info("Starting backtest...")
    
    # Initialize bot components
    bot = HyperliquidTradingBot()
    
    # Get historical data for backtesting
    symbols = ['ETH-USD', 'BTC-USD']
    
    backtest_results = {}
    
    for symbol in symbols:
        logger.info(f"Backtesting {symbol}...")
        
        # Get historical data (last 30 days for demo)
        market_data = await bot.data_manager.get_market_data(symbol, '5m', 8640)  # 30 days of 5min data
        
        if market_data.empty:
            logger.warning(f"No data for {symbol}")
            continue
        
        # Run backtest simulation
        results = await simulate_trading(bot, symbol, market_data)
        backtest_results[symbol] = results
        
        logger.info(f"Backtest results for {symbol}: {results}")
    
    return backtest_results

async def simulate_trading(bot, symbol, market_data):
    """Simulate trading on historical data"""
    initial_capital = 10000
    current_capital = initial_capital
    position = None
    trades = []
    
    for i in range(100, len(market_data)):
        # Get data up to current point
        current_data = market_data.iloc[:i+1]
        
        # Analyze market conditions
        analysis = await bot.analyze_market_conditions(symbol)
        
        if not analysis:
            continue
        
        # Check for entry signals
        should_trade, direction, strength = await bot.should_open_position(analysis)
        
        current_price = current_data['close'].iloc[-1]
        
        # If no position and signal to enter
        if position is None and should_trade and strength > 0.6:
            position_size = current_capital * 0.1 * strength  # 10% of capital
            
            position = {
                'direction': direction,
                'entry_price': current_price,
                'size': position_size,
                'entry_time': current_data.index[-1]
            }
            
            logger.info(f"Simulated entry: {direction} {symbol} @ {current_price}")
        
        # If have position, check exit conditions
        elif position is not None:
            entry_price = position['entry_price']
            
            if position['direction'] == 'long':
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100
            
            should_exit = False
            exit_reason = ""
            
            # Check exit conditions
            if pnl_pct <= -2.0:  # Stop loss
                should_exit = True
                exit_reason = "Stop Loss"
            elif pnl_pct >= 2.0:  # Take profit
                should_exit = True
                exit_reason = "Take Profit"
            
            if should_exit:
                trade_pnl = position['size'] * (pnl_pct / 100)
                current_capital += trade_pnl
                
                trades.append({
                    'symbol': symbol,
                    'direction': position['direction'],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': trade_pnl,
                    'exit_reason': exit_reason,
                    'entry_time': position['entry_time'],
                    'exit_time': current_data.index[-1]
                })
                
                logger.info(f"Simulated exit: {exit_reason} @ {current_price}, PnL: {pnl_pct:.2f}%")
                position = None
    
    # Calculate results
    total_return = (current_capital - initial_capital) / initial_capital * 100
    winning_trades = len([t for t in trades if t['pnl_dollar'] > 0])
    total_trades = len(trades)
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    
    return {
        'initial_capital': initial_capital,
        'final_capital': current_capital,
        'total_return_pct': total_return,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'win_rate': win_rate,
        'trades': trades
    }

async def train_ml_models():
    """Train ML models with historical data"""
    logger.info("Training ML models...")
    
    # Initialize components
    bot = HyperliquidTradingBot()
    
    symbols = ['ETH-USD', 'BTC-USD', 'SOL-USD']
    
    for symbol in symbols:
        logger.info(f"Training models for {symbol}...")
        
        # Get more historical data for training
        market_data = await bot.data_manager.get_market_data(symbol, '5m', 10000)
        
        if len(market_data) < 1000:
            logger.warning(f"Insufficient data for {symbol}")
            continue
        
        # Train models
        success = await bot.ml_predictor.train_models(market_data)
        
        if success:
            logger.info(f"Successfully trained models for {symbol}")
        else:
            logger.error(f"Failed to train models for {symbol}")

async def validate_setup():
    """Validate bot setup and configuration"""
    logger.info("Validating bot setup...")
    
    try:
        # Check environment variables
        required_vars = ['PRIVATE_KEY', 'WALLET_ADDRESS']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Missing environment variables: {missing_vars}")
            return False
        
        # Initialize bot
        bot = HyperliquidTradingBot()
        
        # Test connection
        account_info = await bot.get_account_info()
        if account_info:
            logger.info("Successfully connected to Hyperliquid")
            logger.info(f"Account value: ${account_info.get('marginSummary', {}).get('accountValue', 0)}")
        else:
            logger.error("Failed to connect to Hyperliquid")
            return False
        
        # Test data retrieval
        test_symbol = 'ETH-USD'
        market_data = await bot.data_manager.get_market_data(test_symbol, limit=100)
        
        if not market_data.empty:
            logger.info(f"Successfully retrieved data for {test_symbol}")
            logger.info(f"Data shape: {market_data.shape}")
        else:
            logger.error(f"Failed to retrieve data for {test_symbol}")
            return False
        
        logger.info("Bot setup validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Setup validation failed: {e}")
        return False

async def main():
    """Main function for setup and testing"""
    print("Hyperliquid Trading Bot Setup and Testing")
    print("=" * 50)
    
    # Validate setup
    if not await validate_setup():
        print("Setup validation failed. Please check your configuration.")
        return
    
    # Menu
    while True:
        print("\nOptions:")
        print("1. Run backtest")
        print("2. Train ML models")
        print("3. Test current market analysis")
        print("4. Start live trading")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            await backtest_strategy()
        elif choice == '2':
            await train_ml_models()
        elif choice == '3':
            await test_market_analysis()
        elif choice == '4':
            print("Starting live trading bot...")
            bot = HyperliquidTradingBot()
            await bot.run()
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

async def test_market_analysis():
    """Test market analysis on current data"""
    logger.info("Testing market analysis...")
    
    bot = HyperliquidTradingBot()
    symbols = ['ETH-USD', 'BTC-USD']
    
    for symbol in symbols:
        logger.info(f"Analyzing {symbol}...")
        
        # Get current market data
        market_data = await bot.data_manager.get_market_data(symbol, limit=200)
        
        if market_data.empty:
            logger.warning(f"No data for {symbol}")
            continue
        
        # Analyze market conditions
        analysis = await bot.analyze_market_conditions(symbol)
        
        if analysis:
            logger.info(f"Analysis for {symbol}:")
            logger.info(f"  Technical signals: {len(analysis.get('technical_signals', {}))}")
            logger.info(f"  ML prediction: {analysis.get('ml_prediction', {})}")
            logger.info(f"  Sentiment score: {analysis.get('sentiment_score', 0):.3f}")
            
            # Check trading decision
            should_trade, direction, strength = await bot.should_open_position(analysis)
            logger.info(f"  Trading decision: {should_trade} | {direction} | {strength:.3f}")
        else:
            logger.warning(f"Failed to analyze {symbol}")

if __name__ == "__main__":
    asyncio.run(main())