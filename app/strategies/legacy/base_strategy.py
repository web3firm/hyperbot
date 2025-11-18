"""
Base Strategy Interface
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Signal:
    """Trading signal"""
    symbol: str
    direction: str  # 'long', 'short', 'close'
    strength: float  # 0.0 to 1.0
    entry_price: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    reason: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, symbol: str, config: Dict[str, Any]):
        self.symbol = symbol
        self.config = config
        self.last_signal = None
        self.last_update = None
    
    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Analyze market data and generate signal
        
        Args:
            market_data: Dictionary containing price, volume, orderbook, etc.
            
        Returns:
            Signal object or None if no signal
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return strategy name"""
        pass
    
    def calculate_stop_loss(self, entry_price: Decimal, direction: str) -> Decimal:
        """Calculate stop loss price"""
        stop_pct = Decimal(str(self.config.get('stop_loss_pct', 0.7))) / Decimal('100')
        
        if direction == 'long':
            return entry_price * (Decimal('1') - stop_pct)
        else:  # short
            return entry_price * (Decimal('1') + stop_pct)
    
    def calculate_take_profit(self, entry_price: Decimal, direction: str) -> Decimal:
        """Calculate take profit price"""
        tp_pct = Decimal(str(self.config.get('take_profit_pct', 1.5))) / Decimal('100')
        
        if direction == 'long':
            return entry_price * (Decimal('1') + tp_pct)
        else:  # short
            return entry_price * (Decimal('1') - tp_pct)
