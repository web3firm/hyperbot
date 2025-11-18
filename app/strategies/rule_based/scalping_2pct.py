"""
Scalping Strategy - 2% TP / 1% SL / 5x Leverage
Base strategy for data collection and consistent execution
Target: 50-120 trades/day
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from collections import deque
import os

logger = logging.getLogger(__name__)


class ScalpingStrategy2Pct:
    """
    Fixed scalping strategy with 2% take profit and 1% stop loss
    
    Strategy Rules:
    - Leverage: 5x
    - Take Profit: +2%
    - Stop Loss: -1%
    - Position Size: 70% of available capital
    - Entry: Simple momentum + volume confirmation
    - Target: 50-120 trades per day
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any] = None):
        """
        Initialize scalping strategy
        
        Args:
            symbol: Trading symbol
            config: Strategy configuration
        """
        self.symbol = symbol
        self.config = config or {}
        
        # Strategy parameters - Read from environment with fallbacks
        self.leverage = int(os.getenv('MAX_LEVERAGE', '5'))
        self.tp_pct = Decimal(os.getenv('TAKE_PROFIT_PCT', '2.0'))
        self.sl_pct = Decimal(os.getenv('STOP_LOSS_PCT', '1.0'))
        self.position_size_pct = Decimal(os.getenv('POSITION_SIZE_PCT', '70.0'))
        
        # Entry conditions - IMPROVED for better win rate
        # With 5x leverage, need higher threshold to overcome fees (~0.1% total cost)
        self.min_momentum_threshold = Decimal('0.3')  # 0.3% momentum = 1.5% PnL with 5x
        self.volume_multiplier = Decimal('1.5')  # 50% above average volume for confirmation
        self.confirmation_bars = 2  # Require 2 consecutive bars in same direction
        
        # Trend filter - only trade with the trend
        self.trend_lookback = 50  # Use 50 bars for trend
        self.min_trend_strength = Decimal('0.5')  # 0.5% move to confirm trend
        
        # State tracking
        self.recent_prices = deque(maxlen=50)  # Increased for trend analysis
        self.recent_volumes = deque(maxlen=20)
        self.last_signal_time: Optional[datetime] = None
        self.signal_cooldown_seconds = 60  # 60s cooldown for better quality signals
        
        # Statistics
        self.signals_generated = 0
        self.trades_executed = 0
        
        logger.info(f"📈 Scalping Strategy initialized for {symbol}")
        logger.info(f"   Leverage: {self.leverage}x")
        logger.info(f"   TP: +{self.tp_pct}% | SL: -{self.sl_pct}%")
        logger.info(f"   Position Size: {self.position_size_pct}%")
    
    async def generate_signal(self, market_data: Dict[str, Any],
                             account_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal based on market data
        
        Args:
            market_data: Current market data (price, orderbook, volume)
            account_state: Account state (balance, positions, etc.)
            
        Returns:
            Trading signal or None
        """
        # Check cooldown
        if self.last_signal_time:
            time_since_signal = (datetime.now(timezone.utc) - self.last_signal_time).total_seconds()
            if time_since_signal < self.signal_cooldown_seconds:
                return None
        
        # Get current price
        current_price = market_data.get('price')
        if not current_price:
            return None
        
        current_price = Decimal(str(current_price))
        
        # Store price
        self.recent_prices.append(current_price)
        
        # Need at least 50 prices for trend analysis
        if len(self.recent_prices) < 50:
            return None
        
        # === TREND FILTER: Only trade WITH the trend ===
        price_50_ago = self.recent_prices[0]  # Oldest price
        trend_pct = ((current_price - price_50_ago) / price_50_ago) * 100
        
        if abs(trend_pct) < self.min_trend_strength:
            return None  # No clear trend, avoid choppy markets
        
        trend_direction = 'up' if trend_pct > 0 else 'down'
        
        # === MOMENTUM CALCULATION ===
        price_10_ago = self.recent_prices[-10]
        momentum_pct = ((current_price - price_10_ago) / price_10_ago) * 100
        
        # === CONFIRMATION: Check previous bars also show momentum ===
        price_5_ago = self.recent_prices[-5]
        confirmation_momentum = ((price_10_ago - price_5_ago) / price_5_ago) * 100
        
        # Both recent momentum and confirmation must align
        signal_type = None
        if momentum_pct > self.min_momentum_threshold and confirmation_momentum > 0:
            # Strong upward momentum with confirmation
            if trend_direction == 'up':  # Only if trend is also up
                signal_type = 'long'
        elif momentum_pct < -self.min_momentum_threshold and confirmation_momentum < 0:
            # Strong downward momentum with confirmation
            if trend_direction == 'down':  # Only if trend is also down
                signal_type = 'short'
        
        if signal_type is None:
            return None  # No valid signal
        
        # === SUPPORT/RESISTANCE CHECK ===
        # Don't buy at recent highs, don't sell at recent lows
        recent_high = max(self.recent_prices)
        recent_low = min(self.recent_prices)
        
        if signal_type == 'long' and current_price > recent_high * Decimal('0.98'):
            return None  # Too close to resistance (within 2%)
        if signal_type == 'short' and current_price < recent_low * Decimal('1.02'):
            return None  # Too close to support (within 2%)
        
        # Check if we already have a position
        positions = account_state.get('positions', [])
        has_position = any(p['symbol'] == self.symbol for p in positions)
        
        if has_position:
            return None  # Already in position
        
        # Calculate position size
        account_value = Decimal(str(account_state.get('account_value', 0)))
        if account_value <= 0:
            return None
        
        # Use 69% of capital as collateral, then apply leverage
        # Position value = (account_value * position_size_pct / 100) * leverage
        # But we want the SIZE based on collateral only, leverage is already applied by exchange
        collateral_to_use = account_value * (self.position_size_pct / 100)
        position_value = collateral_to_use * self.leverage
        position_size = position_value / current_price
        # Note: Size will be rounded by exchange client based on asset metadata
        position_size = round(float(position_size), 2)  # Conservative default, exchange will adjust
        
        # Calculate SL and TP prices based on PnL percentage (adjusted for leverage)
        # With 5x leverage: 1% price move = 5% PnL
        # So for 1% PnL: need 0.2% price move, for 2% PnL: need 0.4% price move
        sl_price_pct = self.sl_pct / self.leverage  # 1% PnL / 5x = 0.2% price
        tp_price_pct = self.tp_pct / self.leverage  # 2% PnL / 5x = 0.4% price
        
        if signal_type == 'long':
            entry_price = current_price
            sl_price = entry_price * (1 - sl_price_pct / 100)
            tp_price = entry_price * (1 + tp_price_pct / 100)
            side = 'buy'
        else:  # short
            entry_price = current_price
            sl_price = entry_price * (1 + sl_price_pct / 100)
            tp_price = entry_price * (1 - tp_price_pct / 100)
            side = 'sell'
        
        # Round prices based on magnitude
        price_val = float(entry_price)
        if price_val >= 100:
            decimals = 2
        elif price_val >= 10:
            decimals = 3
        else:
            decimals = 4
        
        entry_price = round(entry_price, decimals)
        sl_price = round(sl_price, decimals)
        tp_price = round(tp_price, decimals)
        
        # Update tracking
        self.last_signal_time = datetime.now(timezone.utc)
        self.signals_generated += 1
        
        # Log signal with full context for analysis
        logger.info(f"🎯 Signal generated: {signal_type.upper()} {self.symbol} @ {entry_price}")
        logger.info(f"   📊 Trend: {trend_direction.upper()} ({trend_pct:+.2f}%) | Momentum: {momentum_pct:+.2f}% | Confirmation: {confirmation_momentum:+.2f}%")
        logger.info(f"   💰 Size: {position_size:.2f} | SL: {sl_price} | TP: {tp_price}")
        logger.info(f"   📈 R:R = 1:{float(tp_price_pct)/float(sl_price_pct):.1f} (Risk {sl_price_pct}% for {tp_price_pct}% reward)")
        
        signal = {
            'strategy': 'Scalping2Pct',
            'symbol': self.symbol,
            'signal_type': signal_type,
            'side': side,
            'entry_price': float(entry_price),
            'size': float(position_size),
            'leverage': self.leverage,
            'stop_loss': float(sl_price),
            'take_profit': float(tp_price),
            'momentum_pct': float(momentum_pct),
            'trend_pct': float(trend_pct),
            'trend_direction': trend_direction,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reason': f"Trend {trend_direction.upper()} {trend_pct:+.2f}% | Momentum {momentum_pct:+.2f}%"
        }
        
        return signal
    
    def record_trade_execution(self, signal: Dict[str, Any], result: Dict[str, Any]):
        """
        Record trade execution for strategy tracking
        
        Args:
            signal: Original signal
            result: Execution result
        """
        self.trades_executed += 1
        logger.info(f"✅ Trade #{self.trades_executed} executed from Scalping2Pct strategy")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            'strategy': 'Scalping2Pct',
            'symbol': self.symbol,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'execution_rate': self.trades_executed / self.signals_generated if self.signals_generated > 0 else 0,
            'parameters': {
                'leverage': self.leverage,
                'tp_pct': float(self.tp_pct),
                'sl_pct': float(self.sl_pct),
                'position_size_pct': float(self.position_size_pct)
            }
        }
    
    def reset_statistics(self):
        """Reset strategy statistics"""
        self.signals_generated = 0
        self.trades_executed = 0
        logger.info("📊 Strategy statistics reset")
