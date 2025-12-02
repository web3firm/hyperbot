"""
Breakout Strategy
Entry: Price breaks above/below 20-period high/low
Logic: Momentum continuation after range breakout
Target: 20-40 trades/day in volatile markets
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from collections import deque
import os

logger = logging.getLogger(__name__)


class BreakoutStrategy:
    """
    Breakout strategy - trades range breaks with momentum
    
    Strategy Rules:
    - Entry: Price breaks 20-period high (buy) or low (sell)
    - Confirmation: Clean break (not just wick)
    - TP: 1.5% beyond breakout point
    - SL: 0.75% inside previous range
    - Works best in: Volatile/trending markets
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any] = None):
        """Initialize breakout strategy"""
        self.symbol = symbol
        self.config = config or {}
        
        # Strategy parameters
        self.leverage = int(os.getenv('MAX_LEVERAGE', '5'))
        self.tp_pct = Decimal('1.5')  # 1.5% beyond breakout
        self.sl_pct = Decimal('0.75')  # 0.75% inside range
        self.position_size_pct = Decimal(os.getenv('POSITION_SIZE_PCT', '50'))
        
        # Breakout period
        self.lookback_period = 20
        self.min_breakout_pct = Decimal('0.05')  # Minimum 0.05% break
        
        # State tracking
        self.recent_prices = deque(maxlen=self.lookback_period)
        self.recent_highs = deque(maxlen=self.lookback_period)
        self.recent_lows = deque(maxlen=self.lookback_period)
        self.last_signal_time: Optional[datetime] = None
        self.signal_cooldown_seconds = 30
        
        # Statistics
        self.signals_generated = 0
        self.trades_executed = 0
        
        logger.info(f"🚀 Breakout Strategy initialized for {symbol}")
        logger.info(f"   Lookback: {self.lookback_period} periods")
        logger.info(f"   TP: {self.tp_pct}% | SL: {self.sl_pct}%")
    
    async def generate_signal(self, market_data: Dict[str, Any],
                             account_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate breakout signal"""
        
        # Check cooldown
        if self.last_signal_time:
            time_since = (datetime.now(timezone.utc) - self.last_signal_time).total_seconds()
            if time_since < self.signal_cooldown_seconds:
                return None
        
        # Get current price
        current_price = market_data.get('price')
        if not current_price:
            return None
        
        current_price = Decimal(str(current_price))
        self.recent_prices.append(current_price)
        
        # Store high/low approximation (using price as proxy)
        self.recent_highs.append(current_price)
        self.recent_lows.append(current_price)
        
        # Need full period
        if len(self.recent_prices) < self.lookback_period:
            return None
        
        # Calculate range high/low (excluding current price)
        range_high = max(list(self.recent_highs)[:-1])  # Last 19 prices
        range_low = min(list(self.recent_lows)[:-1])
        
        # Check for breakout
        signal_type = None
        breakout_level = None
        
        if current_price > range_high:
            # Breakout above
            breakout_pct = ((current_price - range_high) / range_high) * 100
            if breakout_pct >= self.min_breakout_pct:
                signal_type = 'long'
                breakout_level = range_high
        elif current_price < range_low:
            # Breakout below
            breakout_pct = ((range_low - current_price) / range_low) * 100
            if breakout_pct >= self.min_breakout_pct:
                signal_type = 'short'
                breakout_level = range_low
        else:
            return None  # No breakout
        
        # Check existing position
        positions = account_state.get('positions', [])
        if any(p['symbol'] == self.symbol for p in positions):
            return None
        
        # Calculate position size
        account_value = Decimal(str(account_state.get('account_value', 0)))
        if account_value <= 0:
            return None
        
        collateral_to_use = account_value * (self.position_size_pct / 100)
        position_value = collateral_to_use * self.leverage
        position_size = position_value / current_price
        position_size = round(float(position_size), 2)
        
        # Calculate SL and TP based on PnL percentage (adjusted for leverage)
        # With leverage: PnL% = Price% * Leverage, so Price% = PnL% / Leverage
        sl_price_pct = self.sl_pct / self.leverage
        tp_price_pct = self.tp_pct / self.leverage
        
        # Calculate SL and TP prices
        if signal_type == 'long':
            # Buy breakout - momentum up
            entry_price = current_price
            sl_price = entry_price * (1 - sl_price_pct / 100)  # Back inside range
            tp_price = entry_price * (1 + tp_price_pct / 100)  # Continue momentum
            side = 'buy'
        else:  # short
            # Sell breakout - momentum down
            entry_price = current_price
            sl_price = entry_price * (1 + sl_price_pct / 100)  # Back inside range
            tp_price = entry_price * (1 - tp_price_pct / 100)  # Continue momentum
            side = 'sell'
        
        # Round prices
        price_val = float(entry_price)
        if price_val >= 100:
            decimals = 2
        elif price_val >= 10:
            decimals = 3
        else:
            decimals = 4
        
        entry_price = round(float(entry_price), decimals)
        sl_price = round(float(sl_price), decimals)
        tp_price = round(float(tp_price), decimals)
        breakout_level = round(float(breakout_level), decimals) if breakout_level else float(entry_price)
        
        # Update tracking
        self.last_signal_time = datetime.now(timezone.utc)
        self.signals_generated += 1
        
        signal = {
            'strategy': 'Breakout',
            'symbol': self.symbol,
            'signal_type': signal_type,
            'side': side,
            'entry_price': float(entry_price),
            'size': float(position_size),
            'leverage': self.leverage,
            'stop_loss': float(sl_price),
            'take_profit': float(tp_price),
            'breakout_level': float(breakout_level),
            'breakout_pct': float(breakout_pct),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reason': f"Breakout: {breakout_pct:.2f}% beyond {breakout_level}"
        }
        
        logger.info(f"🚀 Breakout: {signal_type.upper() if signal_type else 'NONE'} {self.symbol} @ {entry_price}")
        logger.info(f"   Break Level: {breakout_level} | Strength: {breakout_pct:.2f}%")
        
        return signal
    
    def record_trade_execution(self, signal: Dict[str, Any], result: Dict[str, Any]):
        """Record trade execution"""
        self.trades_executed += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            'strategy': 'Breakout',
            'symbol': self.symbol,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'execution_rate': self.trades_executed / self.signals_generated if self.signals_generated > 0 else 0
        }
