import os
import sys
import asyncio
import time
import traceback
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

import numpy as np
import pandas as pd
from loguru import logger
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount

# Hyperliquid SDK
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Custom modules
from strategies.strategy_manager import StrategyManager
from ml.ml_predictor import MLPredictor
from sentiment.sentiment_analyzer import SentimentAnalyzer
from risk.risk_manager import RiskManager
from utils.data_manager import DataManager
from utils.position_manager import PositionManager
from telegram_notifications import notify_trade, notify_risk, notify_pnl, notify_prediction, notify_system

load_dotenv()

@dataclass
class TradingConfig:
    """Trading configuration parameters"""
    initial_portfolio_percentage: float = float(os.getenv('INITIAL_PORTFOLIO_PERCENTAGE', 10.0))
    leverage: int = int(os.getenv('LEVERAGE', 5))
    max_trades: int = int(os.getenv('MAX_TRADES', 5))
    risk_per_trade: float = float(os.getenv('RISK_PER_TRADE', 2.0))
    quick_profit_threshold: float = float(os.getenv('QUICK_PROFIT_THRESHOLD', 2.0))
    quick_profit_exit_percentage: float = float(os.getenv('QUICK_PROFIT_EXIT_PERCENTAGE', 40.0))
    ml_profit_threshold_1: float = float(os.getenv('ML_PROFIT_THRESHOLD_1', 3.0))
    ml_profit_exit_1: float = float(os.getenv('ML_PROFIT_EXIT_1', 30.0))
    ml_profit_threshold_2: float = float(os.getenv('ML_PROFIT_THRESHOLD_2', 4.0))
    stop_loss_percentage: float = float(os.getenv('STOP_LOSS_PERCENTAGE', 2.0))
    # High-volume tokens for maximum trading opportunities
    symbols: List[str] = field(default_factory=lambda: [
        # Major tokens (highest volume)
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'DOGE-USD',
        # High-volume alts (great for scalping)
        'HYPE-USD', 'FARTCOIN-USD', 'POPCAT-USD', 'PUMP-USD', 'VIRTUAL-USD',
        'TRUMP-USD', 'ASTER-USD', 'ZEC-USD', 'PAXG-USD', 'XPL-USD',
        # Medium-high volume (consistent opportunities)
        'UNI-USD', 'LTC-USD', 'LINK-USD', 'ADA-USD', 'AAVE-USD',
        'NEAR-USD', 'TON-USD', 'RENDER-USD', 'TAO-USD', 'ENA-USD',
        'STRK-USD', 'WIF-USD', 'ONDO-USD', 'ARB-USD', 'SUI-USD',
        # Volatile meme tokens (high profit potential)
        'kPEPE-USD', 'kBONK-USD', 'kFLOKI-USD', 'BRETT-USD', 'MEW-USD',
        'PNUT-USD', 'GOAT-USD', 'MOODENG-USD', 'PENGU-USD', 'AIXBT-USD',
        # DeFi tokens (strong fundamentals)
        'JUP-USD', 'JTO-USD', 'EIGEN-USD', 'ETHFI-USD', 'PENDLE-USD',
        'CRV-USD', 'LDO-USD', 'SUSHI-USD', 'COMP-USD', 'MKR-USD',
        # Layer 1/2 tokens
        'AVAX-USD', 'DOT-USD', 'ATOM-USD', 'TIA-USD', 'MNT-USD',
        'POL-USD', 'FIL-USD', 'AR-USD', 'HBAR-USD', 'ICP-USD',
        # Gaming/AI tokens
        'IMX-USD', 'SAND-USD', 'GALA-USD', 'SUPER-USD', 'FET-USD',
        'ZRO-USD', 'W-USD', 'IO-USD', 'ZK-USD', 'TURBO-USD'
    ] if 'SYMBOLS' not in os.environ else os.getenv('SYMBOLS', '').split(','))
    timeframe: str = os.getenv('TIMEFRAME', '1m')
    max_drawdown: float = float(os.getenv('MAX_DRAWDOWN', 5.0))
    daily_loss_limit: float = float(os.getenv('DAILY_LOSS_LIMIT', 3.0))
    # Multi-symbol configuration
    max_concurrent_positions: int = int(os.getenv('MAX_CONCURRENT_POSITIONS', 8))
    max_symbols_per_cycle: int = int(os.getenv('MAX_SYMBOLS_PER_CYCLE', 20))
    min_signal_strength: float = float(os.getenv('MIN_SIGNAL_STRENGTH', 0.65))

class HyperliquidTradingBot:
    """Main trading bot class for Hyperliquid"""
    
    def __init__(self):
        self.config = TradingConfig()
        self.setup_logging()
        self.initialize_components()
        self.active_positions: Dict[str, dict] = {}
        self.trade_count = 0
        self.daily_pnl = 0.0
        self.start_time = datetime.now()
        
    def setup_logging(self):
        """Configure logging"""
        logger.remove()
        logger.add(
            os.getenv('LOG_FILE', 'logs/trading_bot.log'),
            rotation="1 day",
            retention="30 days",
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
        )
        logger.add(sys.stdout, level="INFO")
        
    def initialize_components(self):
        """Initialize all bot components"""
        try:
            # Initialize Hyperliquid connection
            self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
            
            # Initialize exchange connection - updated for new SDK
            private_key = os.getenv('PRIVATE_KEY')
            if not private_key:
                raise ValueError("PRIVATE_KEY environment variable is required")
            
            # Create LocalAccount from private key
            self.wallet = eth_account.Account.from_key(private_key)
            
            # Get main account address (the one with funds)
            main_account = os.getenv('MAIN_ACCOUNT_ADDRESS')
            if not main_account:
                # Fallback to wallet address if not specified
                main_account = os.getenv('WALLET_ADDRESS')
                
            self.exchange = Exchange(
                wallet=self.wallet,
                base_url=constants.MAINNET_API_URL,
                vault_address=None,
                account_address=main_account
            )
            
            # Initialize components
            self.data_manager = DataManager(self.info)
            self.strategy_manager = StrategyManager()
            self.ml_predictor = MLPredictor()
            self.sentiment_analyzer = SentimentAnalyzer()
            self.risk_manager = RiskManager(self.config)
            self.position_manager = PositionManager(self.exchange, self.info)
            
            logger.info("Bot components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
            
    async def get_account_info(self) -> dict:
        """Get account information"""
        try:
            # Get the main account address (the one with funds)
            address = self.exchange.account_address or self.exchange.wallet.address
            
            user_state = self.info.user_state(address)
            return user_state
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
            
    async def get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        try:
            user_state = await self.get_account_info()
            if user_state and 'marginSummary' in user_state:
                return float(user_state['marginSummary']['accountValue'])
            return 0.0
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return 0.0
            
    async def calculate_position_size(self, symbol: str, signal_strength: float) -> float:
        """Calculate position size based on portfolio and risk management"""
        try:
            portfolio_value = await self.get_portfolio_value()
            if portfolio_value == 0:
                return 0.0
                
            # Base position size (10% of portfolio)
            base_size = portfolio_value * (self.config.initial_portfolio_percentage / 100)
            
            # Adjust by signal strength
            adjusted_size = base_size * signal_strength
            
            # Apply leverage
            leveraged_size = adjusted_size * self.config.leverage
            
            # Risk management check
            max_risk = portfolio_value * (self.config.risk_per_trade / 100)
            final_size = min(leveraged_size, max_risk)
            
            logger.info(f"Position size for {symbol}: ${final_size:.2f}")
            return final_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
            
    async def analyze_market_conditions(self, symbol: str) -> dict:
        """Comprehensive market analysis"""
        try:
            # Get market data
            market_data = await self.data_manager.get_market_data(symbol)
            
            # Technical analysis
            technical_signals = self.strategy_manager.analyze_all_strategies(market_data)
            
            # ML prediction
            ml_prediction = await self.ml_predictor.predict(market_data)
            
            # Sentiment analysis
            sentiment_score = await self.sentiment_analyzer.analyze_symbol_sentiment(symbol)
            
            # Combine signals
            combined_analysis = {
                'symbol': symbol,
                'technical_signals': technical_signals,
                'ml_prediction': ml_prediction,
                'sentiment_score': sentiment_score,
                'timestamp': datetime.now().isoformat()
            }
            
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions for {symbol}: {e}")
            return {}
            
    async def should_open_position(self, analysis: dict) -> Tuple[bool, str, float]:
        """Determine if we should open a position"""
        try:
            if not analysis:
                return False, "No analysis", 0.0
                
            technical_signals = analysis.get('technical_signals', {})
            ml_prediction = analysis.get('ml_prediction', {})
            sentiment_score = analysis.get('sentiment_score', 0.0)
            
            # Check if we've reached max trades
            if self.trade_count >= self.config.max_trades:
                return False, "Max trades reached", 0.0
                
            # Technical signal strength
            tech_score = 0.0
            tech_direction = "none"
            
            if technical_signals:
                bullish_signals = sum(1 for signal in technical_signals.values() if signal.get('signal') == 'bullish')
                bearish_signals = sum(1 for signal in technical_signals.values() if signal.get('signal') == 'bearish')
                total_signals = len(technical_signals)
                
                if total_signals > 0:
                    if bullish_signals > bearish_signals:
                        tech_score = bullish_signals / total_signals
                        tech_direction = "long"
                    elif bearish_signals > bullish_signals:
                        tech_score = bearish_signals / total_signals
                        tech_direction = "short"
                        
            # ML prediction weight
            ml_confidence = ml_prediction.get('confidence', 0.0) if ml_prediction else 0.0
            ml_direction = ml_prediction.get('direction', 'none') if ml_prediction else 'none'
            
            # Sentiment weight
            sentiment_weight = abs(sentiment_score) * 0.3  # 30% weight for sentiment
            
            # Combined signal strength
            combined_strength = (tech_score * 0.5) + (ml_confidence * 0.3) + (sentiment_weight * 0.2)
            
            # Determine direction
            final_direction = "none"
            if tech_direction == ml_direction and tech_direction != "none":
                final_direction = tech_direction
            elif tech_score > ml_confidence:
                final_direction = tech_direction
            elif ml_confidence > tech_score:
                final_direction = ml_direction
                
            # Decision threshold
            min_signal_strength = 0.6
            should_trade = (combined_strength >= min_signal_strength and 
                          final_direction != "none")
            
            return should_trade, final_direction, combined_strength
            
        except Exception as e:
            logger.error(f"Error in should_open_position: {e}")
            return False, "Error", 0.0
            
    async def open_position(self, symbol: str, direction: str, signal_strength: float) -> bool:
        """Open a new position"""
        try:
            # Calculate position size
            position_size = await self.calculate_position_size(symbol, signal_strength)
            
            if position_size <= 0:
                logger.warning(f"Invalid position size: {position_size}")
                return False
                
            # Get current price for reference
            market_data = await self.data_manager.get_current_price(symbol)
            current_price = market_data.get('price', 0.0)
            
            if current_price <= 0:
                logger.warning(f"Invalid current price for {symbol}: {current_price}")
                return False
                
            # Calculate quantity based on position size and price
            quantity = position_size / current_price
            
            # Determine side
            is_buy = direction == "long"
            
            # Place market order
            order_result = await self.position_manager.place_market_order(
                symbol=symbol,
                is_buy=is_buy,
                sz=quantity,
                reduce_only=False
            )
            
            if order_result:
                # Store position info
                position_info = {
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': current_price,
                    'quantity': quantity,
                    'timestamp': datetime.now(),
                    'signal_strength': signal_strength,
                    'position_size': position_size
                }
                
                self.active_positions[symbol] = position_info
                self.trade_count += 1
                
                logger.info(f"Opened {direction} position for {symbol}: {quantity:.6f} @ ${current_price:.2f}")
                
                # Send Telegram notification
                try:
                    if os.getenv('TELEGRAM_NOTIFY_TRADES', 'false').lower() == 'true':
                        await notify_trade(
                            action='OPEN',
                            symbol=symbol,
                            side=direction.upper(),
                            size=quantity,
                            price=current_price,
                            reason=f"Signal strength: {signal_strength:.2f}"
                        )
                except Exception as e:
                    logger.error(f"Failed to send trade notification: {e}")
                
                return True
            else:
                logger.error(f"Failed to open position for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error opening position for {symbol}: {e}")
            return False
            
    async def manage_positions(self):
        """Manage existing positions with hybrid TP/SL strategy"""
        try:
            for symbol, position_info in list(self.active_positions.items()):
                # Get current position from exchange
                current_position = await self.position_manager.get_position(symbol)
                
                if not current_position:
                    # Position closed externally, remove from tracking
                    del self.active_positions[symbol]
                    continue
                    
                # Calculate PnL
                unrealized_pnl = float(current_position.get('unrealizedPnl', 0))
                position_value = abs(float(current_position.get('positionValue', 1)))
                pnl_percentage = (unrealized_pnl / position_value) * 100 if position_value > 0 else 0
                
                logger.info(f"{symbol} PnL: {pnl_percentage:.2f}% (${unrealized_pnl:.2f})")
                
                # Check stop loss
                if pnl_percentage <= -self.config.stop_loss_percentage:
                    await self.close_position(symbol, "Stop Loss")
                    continue
                    
                # Check quick profit exit (2% -> 40% exit)
                elif pnl_percentage >= self.config.quick_profit_threshold:
                    partial_quantity = float(current_position.get('size', 0)) * (self.config.quick_profit_exit_percentage / 100)
                    if partial_quantity > 0:
                        await self.close_partial_position(symbol, partial_quantity, "Quick Profit Exit")
                        
                # ML-based exits
                elif pnl_percentage >= self.config.ml_profit_threshold_1:
                    # Get ML prediction for exit decision
                    market_data = await self.data_manager.get_market_data(symbol)
                    ml_prediction = await self.ml_predictor.predict(market_data)
                    
                    if ml_prediction and ml_prediction.get('confidence', 0) > 0.7:
                        if pnl_percentage >= self.config.ml_profit_threshold_2:
                            # Exit remaining position at 4%+
                            await self.close_position(symbol, "ML Exit - High Profit")
                        elif pnl_percentage >= self.config.ml_profit_threshold_1:
                            # Exit 30% at 3%+
                            partial_quantity = float(current_position.get('size', 0)) * (self.config.ml_profit_exit_1 / 100)
                            if partial_quantity > 0:
                                await self.close_partial_position(symbol, partial_quantity, "ML Exit - Moderate Profit")
                                
        except Exception as e:
            logger.error(f"Error managing positions: {e}")
            
    async def close_position(self, symbol: str, reason: str = "") -> bool:
        """Close entire position"""
        try:
            result = await self.position_manager.close_position(symbol)
            if result:
                if symbol in self.active_positions:
                    del self.active_positions[symbol]
                logger.info(f"Closed position for {symbol}. Reason: {reason}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False
            
    async def close_partial_position(self, symbol: str, quantity: float, reason: str = "") -> bool:
        """Close partial position"""
        try:
            result = await self.position_manager.close_partial_position(symbol, quantity)
            if result:
                logger.info(f"Partially closed {quantity:.6f} of {symbol}. Reason: {reason}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error partially closing position for {symbol}: {e}")
            return False
            
    async def update_daily_pnl(self):
        """Update daily PnL tracking"""
        try:
            total_pnl = 0.0
            for symbol in self.active_positions:
                position = await self.position_manager.get_position(symbol)
                if position:
                    total_pnl += float(position.get('unrealizedPnl', 0))
                    
            self.daily_pnl = total_pnl
            
            # Check daily loss limit
            portfolio_value = await self.get_portfolio_value()
            if portfolio_value > 0:
                daily_loss_percentage = abs(self.daily_pnl) / portfolio_value * 100
                if self.daily_pnl < 0 and daily_loss_percentage >= self.config.daily_loss_limit:
                    logger.warning(f"Daily loss limit reached: {daily_loss_percentage:.2f}%")
                    await self.close_all_positions("Daily Loss Limit")
                    
        except Exception as e:
            logger.error(f"Error updating daily PnL: {e}")
            
    async def close_all_positions(self, reason: str = ""):
        """Close all open positions"""
        try:
            for symbol in list(self.active_positions.keys()):
                await self.close_position(symbol, reason)
            logger.info(f"Closed all positions. Reason: {reason}")
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            
    async def get_symbol_priorities(self):
        """Get symbols prioritized by volume, volatility, and opportunity potential"""
        try:
            symbol_data = []
            
            for symbol in self.config.symbols:
                try:
                    # Get basic market data
                    market_data = await self.data_manager.get_market_data(symbol, "1h", 24)
                    if market_data is None or len(market_data) < 20:
                        continue
                    
                    # Calculate priority metrics
                    current_price = float(market_data.iloc[-1]['close'])
                    volume_24h = float(market_data['volume'].tail(24).sum())
                    volatility = float(market_data['close'].tail(24).pct_change().std() * 100)
                    
                    # Simple trend strength (last 6 hours vs previous 6)
                    recent_avg = float(market_data['close'].tail(6).mean())
                    previous_avg = float(market_data['close'].iloc[-12:-6].mean())
                    trend_strength = abs((recent_avg - previous_avg) / previous_avg * 100)
                    
                    # Composite priority score
                    priority_score = (
                        (volume_24h / 1000000) * 0.4 +  # Volume weight
                        volatility * 0.3 +              # Volatility weight
                        trend_strength * 0.3            # Trend weight
                    )
                    
                    symbol_data.append({
                        'symbol': symbol,
                        'price': current_price,
                        'volume_24h': volume_24h,
                        'volatility': volatility,
                        'trend_strength': trend_strength,
                        'priority_score': priority_score
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to get priority data for {symbol}: {e}")
                    continue
            
            # Sort by priority score (highest first)
            symbol_data.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # Log top symbols
            top_symbols = [f"{s['symbol']}({s['priority_score']:.1f})" for s in symbol_data[:10]]
            logger.info(f"Top priority symbols: {', '.join(top_symbols)}")
            
            return symbol_data
            
        except Exception as e:
            logger.error(f"Error getting symbol priorities: {e}")
            # Fallback to original symbol order
            return [{'symbol': s, 'priority_score': 0} for s in self.config.symbols]

    async def run_trading_cycle(self):
        """Enhanced multi-symbol trading cycle with intelligent symbol selection"""
        try:
            logger.info("Starting enhanced trading cycle...")
            
            # Update daily PnL and manage existing positions
            await self.update_daily_pnl()
            await self.manage_positions()
            
            # Check if we can take new positions
            current_positions = len(self.active_positions)
            max_new_positions = min(
                self.config.max_concurrent_positions - current_positions,
                self.config.max_trades - self.trade_count
            )
            
            if max_new_positions > 0:
                # Get symbol priorities (volume, volatility, trend strength)
                symbol_priorities = await self.get_symbol_priorities()
                
                # Process top symbols for new opportunities
                symbols_to_analyze = symbol_priorities[:self.config.max_symbols_per_cycle]
                logger.info(f"Analyzing {len(symbols_to_analyze)} high-priority symbols")
                
                new_positions = 0
                for symbol_data in symbols_to_analyze:
                    symbol = symbol_data['symbol']
                    
                    # Skip if already have position
                    if symbol in self.active_positions:
                        continue
                        
                    # Analyze market
                    analysis = await self.analyze_market_conditions(symbol)
                    
                    # Check if should open position
                    should_trade, direction, strength = await self.should_open_position(analysis)
                    
                    # Enhanced signal filtering for multi-symbol trading
                    if should_trade and strength >= self.config.min_signal_strength:
                        logger.info(f"Strong signal for {symbol}: {direction} (strength: {strength:.3f})")
                        success = await self.open_position(symbol, direction, strength)
                        if success:
                            new_positions += 1
                            # Wait between trades to avoid overloading
                            await asyncio.sleep(2)
                            
                            # Stop if we've reached max new positions
                            if new_positions >= max_new_positions:
                                break
                
                logger.info(f"Opened {new_positions} new positions")
            else:
                logger.info("Portfolio at maximum capacity - focusing on position management")
                
            logger.info(f"Trading cycle completed. Active positions: {len(self.active_positions)}/{self.config.max_concurrent_positions}")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            traceback.print_exc()
            
    async def run(self):
        """Main run loop"""
        logger.info("Starting Hyperliquid Trading Bot...")
        
        # Send startup notification
        try:
            if os.getenv('TELEGRAM_NOTIFY_SYSTEM', 'false').lower() == 'true':
                await notify_system('STARTUP', 'Hyperliquid trading bot started and monitoring markets')
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
        
        last_daily_summary = datetime.now().date()
        
        try:
            while True:
                start_time = time.time()
                
                # Run trading cycle
                await self.run_trading_cycle()
                
                # Train ML model periodically
                if datetime.now().hour % 4 == 0:  # Every 4 hours
                    await self.ml_predictor.train_models()
                    
                # Send daily summary at end of day
                current_date = datetime.now().date()
                if (current_date != last_daily_summary and 
                    datetime.now().hour >= 23 and 
                    os.getenv('TELEGRAM_DAILY_SUMMARY', 'false').lower() == 'true'):
                    
                    try:
                        await self._send_daily_summary()
                        last_daily_summary = current_date
                    except Exception as e:
                        logger.error(f"Failed to send daily summary: {e}")
                    
                # Wait for next cycle (1 minute)
                elapsed = time.time() - start_time
                sleep_time = max(0, 60 - elapsed)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}")
        finally:
            # Cleanup
            await self.close_all_positions("Bot Shutdown")
            logger.info("Bot shutdown complete")

if __name__ == "__main__":
    bot = HyperliquidTradingBot()
    asyncio.run(bot.run())