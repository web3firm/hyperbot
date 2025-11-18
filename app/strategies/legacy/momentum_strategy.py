"""
Momentum Strategy - Simple but Effective
Based on price momentum and volume confirmation
"""

import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timezone
from collections import deque

from .base_strategy import BaseStrategy, Signal

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """
    Momentum-based trading strategy
    
    Rules:
    - LONG: Price moving up with volume confirmation
    - SHORT: Price moving down with volume confirmation
    - CLOSE: Reversal detected or profit target hit
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        super().__init__(symbol, config)
        
        # Price history for momentum calculation
        self.price_history = deque(maxlen=20)  # Last 20 prices
        self.volume_history = deque(maxlen=20)  # Last 20 volumes
        
        # Strategy parameters
        self.momentum_threshold = config.get('momentum_threshold', 0.3)  # 0.3%
        self.volume_multiplier = config.get('volume_multiplier', 1.2)   # 20% above average
        self.min_prices = config.get('min_prices', 10)  # Minimum prices before trading
        
        # State tracking
        self.current_position = None  # 'long', 'short', or None
        self.entry_price = None
        self.last_signal_time = None
        self.signal_cooldown = 60  # seconds between signals
        
        logger.info(f"MomentumStrategy initialized for {symbol}")
        logger.info(f"  Momentum threshold: {self.momentum_threshold}%")
        logger.info(f"  Volume multiplier: {self.volume_multiplier}x")
    
    def get_name(self) -> str:
        return "Momentum"
    
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Analyze market data for momentum signals
        
        market_data structure:
        {
            'symbol': 'SOL',
            'mid_price': Decimal('140.50'),
            'bid': Decimal('140.48'),
            'ask': Decimal('140.52'),
            'volume': Decimal('1234567.89'),
            'timestamp': datetime
        }
        """
        try:
            # Extract data
            mid_price = market_data['mid_price']
            volume = market_data.get('volume', Decimal('0'))
            
            # Update history
            self.price_history.append(mid_price)
            self.volume_history.append(volume)
            self.last_update = datetime.now(timezone.utc)
            
            # Need minimum data points
            if len(self.price_history) < self.min_prices:
                logger.debug(f"Waiting for data: {len(self.price_history)}/{self.min_prices}")
                return None
            
            # Check cooldown
            if self.last_signal_time:
                elapsed = (datetime.now(timezone.utc) - self.last_signal_time).total_seconds()
                if elapsed < self.signal_cooldown:
                    return None
            
            # Calculate momentum
            momentum = self._calculate_momentum()
            volume_ratio = self._calculate_volume_ratio()
            
            # Generate signal based on current position
            if self.current_position is None:
                # Look for entry signals
                signal = self._check_entry_signals(mid_price, momentum, volume_ratio)
            else:
                # Look for exit signals
                signal = self._check_exit_signals(mid_price, momentum)
            
            if signal:
                self.last_signal = signal
                self.last_signal_time = datetime.now(timezone.utc)
                logger.info(f"🎯 Signal generated: {signal.direction} {signal.symbol} @ ${signal.entry_price} (strength: {signal.strength:.2f})")
                logger.info(f"   Reason: {signal.reason}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing market data: {e}")
            return None
    
    def _calculate_momentum(self) -> float:
        """Calculate price momentum as percentage change"""
        if len(self.price_history) < 2:
            return 0.0
        
        # Compare current price to average of last 5 prices
        recent_avg = sum(list(self.price_history)[-5:]) / Decimal('5')
        current = self.price_history[-1]
        
        momentum = float((current - recent_avg) / recent_avg * 100)
        return momentum
    
    def _calculate_volume_ratio(self) -> float:
        """Calculate current volume vs average"""
        if len(self.volume_history) < 2 or self.volume_history[-1] == 0:
            return 1.0
        
        avg_volume = sum(list(self.volume_history)[:-1]) / len(list(self.volume_history)[:-1])
        if avg_volume == 0:
            return 1.0
        
        ratio = float(self.volume_history[-1] / avg_volume)
        return ratio
    
    def _check_entry_signals(self, current_price: Decimal, momentum: float, volume_ratio: float) -> Optional[Signal]:
        """Check for entry signals when no position"""
        
        # LONG signal: Positive momentum with volume confirmation
        if momentum > self.momentum_threshold and volume_ratio > self.volume_multiplier:
            stop_loss = self.calculate_stop_loss(current_price, 'long')
            take_profit = self.calculate_take_profit(current_price, 'long')
            
            signal = Signal(
                symbol=self.symbol,
                direction='long',
                strength=min(1.0, (momentum / self.momentum_threshold) * 0.5 + 
                            (volume_ratio / self.volume_multiplier) * 0.5),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Bullish momentum {momentum:.2f}% with {volume_ratio:.1f}x volume"
            )
            
            self.current_position = 'long'
            self.entry_price = current_price
            return signal
        
        # SHORT signal: Negative momentum with volume confirmation
        elif momentum < -self.momentum_threshold and volume_ratio > self.volume_multiplier:
            stop_loss = self.calculate_stop_loss(current_price, 'short')
            take_profit = self.calculate_take_profit(current_price, 'short')
            
            signal = Signal(
                symbol=self.symbol,
                direction='short',
                strength=min(1.0, (abs(momentum) / self.momentum_threshold) * 0.5 + 
                            (volume_ratio / self.volume_multiplier) * 0.5),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Bearish momentum {momentum:.2f}% with {volume_ratio:.1f}x volume"
            )
            
            self.current_position = 'short'
            self.entry_price = current_price
            return signal
        
        return None
    
    def _check_exit_signals(self, current_price: Decimal, momentum: float) -> Optional[Signal]:
        """Check for exit signals when position is open"""
        
        if not self.current_position or not self.entry_price:
            return None
        
        # Calculate P&L percentage
        if self.current_position == 'long':
            pnl_pct = float((current_price - self.entry_price) / self.entry_price * 100)
            reversal = momentum < -self.momentum_threshold  # Price turning down
        else:  # short
            pnl_pct = float((self.entry_price - current_price) / self.entry_price * 100)
            reversal = momentum > self.momentum_threshold  # Price turning up
        
        # Exit conditions
        tp_pct = self.config.get('take_profit_pct', 1.5)
        sl_pct = self.config.get('stop_loss_pct', 0.7)
        
        should_exit = False
        exit_reason = ""
        
        # Take profit hit
        if pnl_pct >= tp_pct:
            should_exit = True
            exit_reason = f"Take profit hit: {pnl_pct:.2f}% gain"
        
        # Stop loss hit
        elif pnl_pct <= -sl_pct:
            should_exit = True
            exit_reason = f"Stop loss hit: {pnl_pct:.2f}% loss"
        
        # Reversal detected
        elif reversal:
            should_exit = True
            exit_reason = f"Momentum reversal detected ({momentum:.2f}%)"
        
        if should_exit:
            signal = Signal(
                symbol=self.symbol,
                direction='close',
                strength=1.0,
                entry_price=current_price,
                reason=exit_reason
            )
            
            # Reset position tracking
            self.current_position = None
            self.entry_price = None
            
            return signal
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current strategy status"""
        momentum = self._calculate_momentum() if len(self.price_history) >= 2 else 0.0
        volume_ratio = self._calculate_volume_ratio() if len(self.volume_history) >= 2 else 1.0
        
        return {
            'name': self.get_name(),
            'symbol': self.symbol,
            'position': self.current_position,
            'entry_price': float(self.entry_price) if self.entry_price else None,
            'current_price': float(self.price_history[-1]) if self.price_history else None,
            'momentum': round(momentum, 3),
            'volume_ratio': round(volume_ratio, 2),
            'data_points': len(self.price_history),
            'last_signal': self.last_signal.direction if self.last_signal else None,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
