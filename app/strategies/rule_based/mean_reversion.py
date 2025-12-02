"""
Mean Reversion Strategy
Entry: Price deviates >0.3% from 20-period moving average
Logic: Overextended prices snap back to mean
Target: 30-50 trades/day in ranging markets
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from collections import deque
import os

logger = logging.getLogger(__name__)


class MeanReversionStrategy:
    """
    Mean reversion strategy - trades when price stretches from average
    
    Strategy Rules:
    - Entry: Price >0.3% away from 20-period SMA
    - Exit: Price returns to SMA (mean reversion)
    - TP: 0.3% back toward mean
    - SL: 0.15% beyond current deviation
    - Works best in: Ranging/choppy markets
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any] = None):
        """Initialize mean reversion strategy"""
        self.symbol = symbol
        self.config = config or {}
        
        # Strategy parameters
        self.leverage = int(os.getenv('MAX_LEVERAGE', '5'))
        self.deviation_threshold = Decimal('0.3')  # 0.3% from SMA triggers
        self.tp_pct = Decimal('0.3')  # Target return to mean
        self.sl_pct = Decimal('0.15')  # Stop beyond deviation
        self.position_size_pct = Decimal(os.getenv('POSITION_SIZE_PCT', '50'))
        
        # Moving average period
        self.sma_period = 20
        
        # State tracking
        self.recent_prices = deque(maxlen=self.sma_period)
        self.last_signal_time: Optional[datetime] = None
        self.signal_cooldown_seconds = 30
        
        # Statistics
        self.signals_generated = 0
        self.trades_executed = 0
        
        logger.info(f"📊 Mean Reversion Strategy initialized for {symbol}")
        logger.info(f"   SMA Period: {self.sma_period}")
        logger.info(f"   Deviation Threshold: {self.deviation_threshold}%")
        logger.info(f"   TP: {self.tp_pct}% | SL: {self.sl_pct}%")
    
    async def generate_signal(self, market_data: Dict[str, Any],
                             account_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate mean reversion signal"""
        
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
        
        # Need full period for SMA
        if len(self.recent_prices) < self.sma_period:
            return None
        
        # Calculate SMA
        sma = sum(self.recent_prices) / len(self.recent_prices)
        
        # Calculate deviation from SMA
        deviation_pct = ((current_price - sma) / sma) * 100
        
        # Determine signal (fade the move - contrarian)
        signal_type = None
        if deviation_pct > self.deviation_threshold:
            # Price too high → expect reversion down
            signal_type = 'short'
        elif deviation_pct < -self.deviation_threshold:
            # Price too low → expect reversion up
            signal_type = 'long'
        else:
            return None  # Not overextended enough
        
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
            # Buying oversold, expect bounce to SMA
            entry_price = current_price
            sl_price = entry_price * (1 - sl_price_pct / 100)  # Below entry
            tp_price = entry_price * (1 + tp_price_pct / 100)  # Toward SMA
            side = 'buy'
        else:  # short
            # Selling overbought, expect drop to SMA
            entry_price = current_price
            sl_price = entry_price * (1 + sl_price_pct / 100)  # Above entry
            tp_price = entry_price * (1 - tp_price_pct / 100)  # Toward SMA
            side = 'sell'
        
        # Round prices
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
        sma = round(sma, decimals)
        
        # Update tracking
        self.last_signal_time = datetime.now(timezone.utc)
        self.signals_generated += 1
        
        signal = {
            'strategy': 'MeanReversion',
            'symbol': self.symbol,
            'signal_type': signal_type,
            'side': side,
            'entry_price': float(entry_price),
            'size': float(position_size),
            'leverage': self.leverage,
            'stop_loss': float(sl_price),
            'take_profit': float(tp_price),
            'deviation_pct': float(deviation_pct),
            'sma': float(sma),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reason': f"Mean reversion: {deviation_pct:+.2f}% from SMA"
        }
        
        logger.info(f"📊 Mean Reversion: {signal_type.upper()} {self.symbol} @ {entry_price}")
        logger.info(f"   Deviation: {deviation_pct:+.2f}% | SMA: {sma}")
        
        return signal
    
    def record_trade_execution(self, signal: Dict[str, Any], result: Dict[str, Any]):
        """Record trade execution"""
        self.trades_executed += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            'strategy': 'MeanReversion',
            'symbol': self.symbol,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'execution_rate': self.trades_executed / self.signals_generated if self.signals_generated > 0 else 0
        }
