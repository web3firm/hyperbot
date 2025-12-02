"""
Volume Spike Strategy  
Entry: Unusual volume spike + momentum confirmation
Logic: Smart money moving, follow the flow
Target: 10-30 trades/day when volume surges
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from collections import deque
import os

logger = logging.getLogger(__name__)


class VolumeSpikeStrategy:
    """
    Volume spike strategy - trades on unusual volume + momentum
    
    Strategy Rules:
    - Entry: Volume >2x average + momentum >0.15%
    - Logic: Large players entering, ride the wave
    - TP: 2% (aggressive, high confidence)
    - SL: 1% (standard)
    - Works best in: News events, breakouts, momentum surges
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any] = None):
        """Initialize volume spike strategy"""
        self.symbol = symbol
        self.config = config or {}
        
        # Strategy parameters
        self.leverage = int(os.getenv('MAX_LEVERAGE', '5'))
        self.tp_pct = Decimal('2.0')  # Aggressive on high conviction
        self.sl_pct = Decimal('1.0')
        self.position_size_pct = Decimal(os.getenv('POSITION_SIZE_PCT', '50'))
        
        # Volume parameters
        self.volume_multiplier = Decimal('2.0')  # 2x average
        self.min_momentum = Decimal('0.15')  # 0.15% momentum required
        self.volume_period = 20
        
        # State tracking
        self.recent_prices = deque(maxlen=20)
        self.recent_volumes = deque(maxlen=self.volume_period)
        self.last_signal_time: Optional[datetime] = None
        self.signal_cooldown_seconds = 30
        
        # Statistics
        self.signals_generated = 0
        self.trades_executed = 0
        
        logger.info(f"📊 Volume Spike Strategy initialized for {symbol}")
        logger.info(f"   Volume Multiplier: {self.volume_multiplier}x")
        logger.info(f"   Min Momentum: {self.min_momentum}%")
    
    async def generate_signal(self, market_data: Dict[str, Any],
                             account_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate volume spike signal"""
        
        # Check cooldown
        if self.last_signal_time:
            time_since = (datetime.now(timezone.utc) - self.last_signal_time).total_seconds()
            if time_since < self.signal_cooldown_seconds:
                return None
        
        # Get current data
        current_price = market_data.get('price')
        current_volume = market_data.get('volume', 0)  # May not be available
        
        if not current_price:
            return None
        
        current_price = Decimal(str(current_price))
        current_volume = Decimal(str(current_volume)) if current_volume else Decimal('0')
        
        self.recent_prices.append(current_price)
        self.recent_volumes.append(current_volume)
        
        # Need full period
        if len(self.recent_prices) < 10 or len(self.recent_volumes) < self.volume_period:
            return None
        
        # Calculate momentum
        price_10_ago = self.recent_prices[-10]
        momentum_pct = ((current_price - price_10_ago) / price_10_ago) * 100
        
        # Calculate average volume (excluding current)
        avg_volume = sum(list(self.recent_volumes)[:-1]) / (len(self.recent_volumes) - 1)
        
        # Check for volume spike
        if avg_volume == 0:
            # No volume data available, fallback to momentum only
            volume_ratio = Decimal('1.0')
            if abs(momentum_pct) < self.min_momentum:
                return None
        else:
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else Decimal('0')
            
            # Need BOTH volume spike AND momentum
            if volume_ratio < self.volume_multiplier:
                return None  # No volume spike
            
            if abs(momentum_pct) < self.min_momentum:
                return None  # Not enough momentum
        
        # Determine direction
        signal_type = 'long' if momentum_pct > 0 else 'short'
        
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
            entry_price = current_price
            sl_price = entry_price * (1 - sl_price_pct / 100)
            tp_price = entry_price * (1 + tp_price_pct / 100)
            side = 'buy'
        else:  # short
            entry_price = current_price
            sl_price = entry_price * (1 + sl_price_pct / 100)
            tp_price = entry_price * (1 - tp_price_pct / 100)
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
        
        # Update tracking
        self.last_signal_time = datetime.now(timezone.utc)
        self.signals_generated += 1
        
        signal = {
            'strategy': 'VolumeSpike',
            'symbol': self.symbol,
            'signal_type': signal_type,
            'side': side,
            'entry_price': float(entry_price),
            'size': float(position_size),
            'leverage': self.leverage,
            'stop_loss': float(sl_price),
            'take_profit': float(tp_price),
            'momentum_pct': float(momentum_pct),
            'volume_ratio': float(volume_ratio),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reason': f"Volume: {volume_ratio:.1f}x | Momentum: {momentum_pct:+.2f}%"
        }
        
        logger.info(f"📊 Volume Spike: {signal_type.upper() if signal_type else 'NONE'} {self.symbol} @ {entry_price}")
        logger.info(f"   Volume: {volume_ratio:.1f}x avg | Momentum: {momentum_pct:+.2f}%")
        
        return signal
    
    def record_trade_execution(self, signal: Dict[str, Any], result: Dict[str, Any]):
        """Record trade execution"""
        self.trades_executed += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            'strategy': 'VolumeSpike',
            'symbol': self.symbol,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'execution_rate': self.trades_executed / self.signals_generated if self.signals_generated > 0 else 0
        }
