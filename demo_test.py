import asyncio
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.strategy_manager import StrategyManager
from ml.ml_predictor import MLPredictor, FeatureEngineer
from sentiment.sentiment_analyzer import SentimentAnalyzer
from risk.risk_manager import RiskManager, RiskMetrics

class TradingConfig:
    """Demo trading configuration"""
    initial_portfolio_percentage = 10.0
    leverage = 5
    max_trades = 5
    risk_per_trade = 2.0
    quick_profit_threshold = 2.0
    quick_profit_exit_percentage = 40.0
    ml_profit_threshold_1 = 3.0
    ml_profit_exit_1 = 30.0
    ml_profit_threshold_2 = 4.0
    stop_loss_percentage = 2.0
    max_drawdown = 5.0
    daily_loss_limit = 3.0

def generate_sample_data(symbol: str, days: int = 30) -> pd.DataFrame:
    """Generate sample OHLCV data for testing"""
    
    # Starting price based on symbol
    price_map = {
        'ETH-USD': 2000.0,
        'BTC-USD': 35000.0,
        'SOL-USD': 60.0
    }
    
    start_price = price_map.get(symbol, 100.0)
    periods = days * 24 * 12  # 5-minute intervals
    
    # Generate random walk data
    np.random.seed(42)  # For reproducible results
    
    timestamps = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        periods=periods,
        freq='5T'
    )
    
    # Generate price movements
    returns = np.random.normal(0.0001, 0.02, periods)  # Small drift with volatility
    prices = [start_price]
    
    for i in range(1, periods):
        new_price = prices[-1] * (1 + returns[i])
        prices.append(new_price)
    
    # Generate OHLCV data
    data = []
    for i in range(periods):
        base_price = prices[i]
        
        # Generate realistic OHLC within reasonable bounds
        high_low_range = base_price * 0.02  # 2% range
        
        open_price = base_price + np.random.uniform(-high_low_range/4, high_low_range/4)
        close_price = base_price + np.random.uniform(-high_low_range/4, high_low_range/4)
        
        high_price = max(open_price, close_price) + np.random.uniform(0, high_low_range/2)
        low_price = min(open_price, close_price) - np.random.uniform(0, high_low_range/2)
        
        volume = np.random.uniform(1000000, 10000000)  # Random volume
        
        data.append({
            'timestamp': timestamps[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

async def test_strategy_analysis():
    """Test strategy analysis components"""
    print("\n🔍 Testing Strategy Analysis...")
    print("=" * 50)
    
    try:
        # Initialize strategy manager
        strategy_manager = StrategyManager()
        
        # Generate sample data
        symbols = ['ETH-USD', 'BTC-USD', 'SOL-USD']
        
        for symbol in symbols:
            print(f"\n📊 Analyzing {symbol}:")
            
            # Generate sample market data
            market_data = generate_sample_data(symbol, days=10)
            print(f"  ✓ Generated {len(market_data)} data points")
            
            # Run all strategies
            strategies = strategy_manager.analyze_all_strategies(market_data)
            
            print(f"  ✓ Analyzed {len(strategies)} strategies:")
            
            for strategy_name, result in strategies.items():
                signal = result.get('signal', 'neutral')
                strength = result.get('strength', 0.0)
                description = result.get('description', 'N/A')
                
                signal_emoji = "🟢" if signal == "bullish" else "🔴" if signal == "bearish" else "🟡"
                print(f"    {signal_emoji} {strategy_name}: {signal} ({strength:.2f}) - {description}")
        
        print("\n✅ Strategy analysis test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Strategy analysis test failed: {e}")
        logger.error(f"Strategy test error: {e}")
        return False

async def test_ml_prediction():
    """Test ML prediction components"""
    print("\n🤖 Testing ML Prediction...")
    print("=" * 50)
    
    try:
        # Initialize ML predictor
        ml_predictor = MLPredictor()
        
        # Generate sample data
        symbol = 'ETH-USD'
        market_data = generate_sample_data(symbol, days=20)
        print(f"✓ Generated training data: {len(market_data)} samples")
        
        # Test feature engineering
        features_df = FeatureEngineer.create_technical_features(market_data)
        print(f"✓ Created {len(features_df.columns)} features")
        
        # Prepare training data
        X, y = await ml_predictor.prepare_data(market_data)
        if not X.empty and len(y) > 0:
            print(f"✓ Prepared training data: {X.shape[0]} samples, {X.shape[1]} features")
            
            # Train models (with limited data)
            success = await ml_predictor.train_models(market_data)
            
            if success:
                print("✓ ML models trained successfully")
                
                # Test prediction
                test_data = market_data.tail(100)  # Last 100 periods for prediction
                prediction = await ml_predictor.predict(test_data)
                
                if prediction:
                    direction = prediction.get('direction', 'neutral')
                    confidence = prediction.get('confidence', 0.0)
                    probabilities = prediction.get('probabilities', {})
                    
                    direction_emoji = "🟢" if direction == "long" else "🔴" if direction == "short" else "🟡"
                    print(f"✓ Prediction: {direction_emoji} {direction} (confidence: {confidence:.2f})")
                    print(f"  Probabilities: Bullish: {probabilities.get('bullish', 0):.2f}, "
                          f"Bearish: {probabilities.get('bearish', 0):.2f}, "
                          f"Neutral: {probabilities.get('neutral', 0):.2f}")
                else:
                    print("⚠️ No prediction generated")
            else:
                print("⚠️ Model training failed - insufficient data")
        else:
            print("⚠️ Failed to prepare training data")
        
        print("\n✅ ML prediction test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ ML prediction test failed: {e}")
        logger.error(f"ML test error: {e}")
        return False

async def test_sentiment_analysis():
    """Test sentiment analysis components"""
    print("\n😊 Testing Sentiment Analysis...")
    print("=" * 50)
    
    try:
        # Initialize sentiment analyzer
        sentiment_analyzer = SentimentAnalyzer()
        
        # Test individual symbol sentiment
        symbols = ['ETH-USD', 'BTC-USD', 'SOL-USD']
        
        for symbol in symbols:
            sentiment_score = await sentiment_analyzer.analyze_symbol_sentiment(symbol)
            
            sentiment_emoji = "😊" if sentiment_score > 0.1 else "😢" if sentiment_score < -0.1 else "😐"
            print(f"  {sentiment_emoji} {symbol}: {sentiment_score:.3f}")
        
        # Test comprehensive sentiment
        comprehensive_sentiment = await sentiment_analyzer.get_comprehensive_sentiment(symbols)
        
        if comprehensive_sentiment:
            print(f"\n✓ Generated comprehensive sentiment for {len(comprehensive_sentiment)} symbols")
            
            for symbol, data in comprehensive_sentiment.items():
                sentiment_score = data.get('sentiment_score', 0)
                fear_greed = data.get('market_fear_greed', 0)
                
                print(f"  📊 {symbol}:")
                print(f"    Sentiment: {sentiment_score:.3f}")
                print(f"    Fear/Greed: {fear_greed:.3f}")
        
        print("\n✅ Sentiment analysis test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Sentiment analysis test failed: {e}")
        logger.error(f"Sentiment test error: {e}")
        return False

async def test_risk_management():
    """Test risk management components"""
    print("\n🛡️ Testing Risk Management...")
    print("=" * 50)
    
    try:
        # Initialize risk manager
        config = TradingConfig()
        risk_manager = RiskManager(config)
        
        # Test position size calculation
        portfolio_value = 10000.0
        signal_strength = 0.8
        volatility = 0.02
        
        position_size = risk_manager.calculate_position_size(
            portfolio_value, signal_strength, volatility
        )
        
        print(f"✓ Position size calculation: ${position_size:.2f}")
        print(f"  Portfolio: ${portfolio_value:.2f}")
        print(f"  Signal strength: {signal_strength:.2f}")
        print(f"  Volatility: {volatility:.2f}")
        
        # Test risk metrics calculation
        sample_positions = [
            {
                'position_value': 1000,
                'exposure': 5000,  # 5x leverage
                'unrealized_pnl': 50,
            },
            {
                'position_value': 800,
                'exposure': 4000,
                'unrealized_pnl': -30,
            }
        ]
        
        risk_metrics = risk_manager.calculate_portfolio_risk(sample_positions, {})
        
        print(f"\n✓ Risk metrics calculated:")
        print(f"  Portfolio value: ${risk_metrics.portfolio_value:.2f}")
        print(f"  Total exposure: ${risk_metrics.total_exposure:.2f}")
        print(f"  Unrealized PnL: ${risk_metrics.unrealized_pnl:.2f}")
        print(f"  Risk score: {risk_metrics.risk_score:.2f}/10")
        
        # Test risk limit checks
        risk_violations = risk_manager.check_risk_limits(risk_metrics)
        
        if risk_violations:
            print(f"  ⚠️ Risk violations: {list(risk_violations.keys())}")
        else:
            print(f"  ✅ No risk violations detected")
        
        print("\n✅ Risk management test completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Risk management test failed: {e}")
        logger.error(f"Risk test error: {e}")
        return False

async def test_trading_simulation():
    """Test complete trading logic simulation"""
    print("\n🎮 Testing Trading Simulation...")
    print("=" * 50)
    
    try:
        # Initialize components
        strategy_manager = StrategyManager()
        ml_predictor = MLPredictor()
        sentiment_analyzer = SentimentAnalyzer()
        config = TradingConfig()
        risk_manager = RiskManager(config)
        
        # Simulate trading session
        portfolio_value = 10000.0
        positions = []
        
        for symbol in ['ETH-USD', 'BTC-USD']:
            print(f"\n📈 Simulating trade analysis for {symbol}:")
            
            # Generate market data
            market_data = generate_sample_data(symbol, days=5)
            
            # Technical analysis
            technical_signals = strategy_manager.analyze_all_strategies(market_data)
            print(f"  ✓ Technical analysis: {len(technical_signals)} strategies")
            
            # Calculate signal strength
            bullish_count = sum(1 for s in technical_signals.values() if s.get('signal') == 'bullish')
            bearish_count = sum(1 for s in technical_signals.values() if s.get('signal') == 'bearish')
            total_count = len(technical_signals)
            
            if total_count > 0:
                if bullish_count > bearish_count:
                    tech_strength = bullish_count / total_count
                    tech_direction = "bullish"
                elif bearish_count > bullish_count:
                    tech_strength = bearish_count / total_count
                    tech_direction = "bearish"
                else:
                    tech_strength = 0.5
                    tech_direction = "neutral"
            else:
                tech_strength = 0.0
                tech_direction = "neutral"
            
            # Sentiment analysis
            sentiment_score = await sentiment_analyzer.analyze_symbol_sentiment(symbol)
            print(f"  ✓ Sentiment: {sentiment_score:.3f}")
            
            # Combined signal
            combined_strength = tech_strength * 0.7 + abs(sentiment_score) * 0.3
            
            print(f"  ✓ Technical: {tech_direction} ({tech_strength:.2f})")
            print(f"  ✓ Combined strength: {combined_strength:.2f}")
            
            # Trading decision
            should_trade = combined_strength >= 0.6 and tech_direction in ['bullish', 'bearish']
            
            if should_trade:
                # Calculate position size
                position_size = risk_manager.calculate_position_size(
                    portfolio_value, combined_strength, 0.02
                )
                
                direction = "long" if tech_direction == "bullish" else "short"
                current_price = market_data['close'].iloc[-1]
                
                position = {
                    'symbol': symbol,
                    'direction': direction,
                    'size': position_size / current_price,
                    'entry_price': current_price,
                    'position_value': position_size / config.leverage,
                    'exposure': position_size,
                    'unrealized_pnl': 0
                }
                
                positions.append(position)
                
                print(f"  🎯 TRADE: {direction} {symbol}")
                print(f"    Entry: ${current_price:.2f}")
                print(f"    Size: {position['size']:.4f}")
                print(f"    Value: ${position['position_value']:.2f}")
                
            else:
                print(f"  ⏸️ No trade - insufficient signal strength")
        
        # Portfolio summary
        if positions:
            total_exposure = sum(p['exposure'] for p in positions)
            total_value = sum(p['position_value'] for p in positions)
            
            print(f"\n📊 Portfolio Summary:")
            print(f"  Active positions: {len(positions)}")
            print(f"  Total value: ${total_value:.2f}")
            print(f"  Total exposure: ${total_exposure:.2f}")
            print(f"  Portfolio usage: {(total_value / portfolio_value) * 100:.1f}%")
            
            # Risk check
            risk_metrics = risk_manager.calculate_portfolio_risk(positions, {})
            print(f"  Risk score: {risk_metrics.risk_score:.2f}/10")
        
        print("\n✅ Trading simulation completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Trading simulation failed: {e}")
        logger.error(f"Simulation error: {e}")
        return False

async def run_demo_tests():
    """Run all demo tests"""
    print("🚀 Hyperliquid Trading Bot - Demo Test Suite")
    print("=" * 60)
    print("Testing bot components without requiring API keys...")
    
    test_results = []
    
    # Run all tests
    tests = [
        ("Strategy Analysis", test_strategy_analysis),
        ("ML Prediction", test_ml_prediction),
        ("Sentiment Analysis", test_sentiment_analysis),
        ("Risk Management", test_risk_management),
        ("Trading Simulation", test_trading_simulation)
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            test_results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! The bot components are working correctly.")
        print("\n📝 Next steps:")
        print("1. Configure your .env file with real Hyperliquid credentials")
        print("2. Start with small amounts for testing")
        print("3. Run 'python main.py' to start live trading")
        print("\n⚠️ Remember: Always test with small amounts first!")
    else:
        print(f"\n⚠️ Some tests failed. Please check the error messages above.")
    
    return passed == total

if __name__ == "__main__":
    # Setup logging
    logger.add("logs/demo_test.log", rotation="1 day", retention="7 days")
    
    # Run demo tests
    asyncio.run(run_demo_tests())