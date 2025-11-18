"""
Rule-Based Signal Engine - Multi-strategy signal coordination
Aggregates signals from multiple strategies with priority and filtering
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types"""
    ENTRY_LONG = "entry_long"
    ENTRY_SHORT = "entry_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    INCREASE_POSITION = "increase_position"
    REDUCE_POSITION = "reduce_position"


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class TradingSignal:
    """Trading signal from a strategy"""
    strategy_name: str
    signal_type: SignalType
    symbol: str
    strength: SignalStrength
    price: Decimal
    size: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_name': self.strategy_name,
            'signal_type': self.signal_type.value,
            'symbol': self.symbol,
            'strength': self.strength.value,
            'price': float(self.price),
            'size': float(self.size) if self.size else None,
            'stop_loss': float(self.stop_loss) if self.stop_loss else None,
            'take_profit': float(self.take_profit) if self.take_profit else None,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class RuleBasedSignalEngine:
    """
    Aggregates and filters signals from multiple strategies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize signal engine
        
        Args:
            config: Configuration
        """
        cfg = config or {}
        
        # Strategy configuration
        self.enabled_strategies: set[str] = set(cfg.get('enabled_strategies', []))
        self.strategy_weights: Dict[str, float] = cfg.get('strategy_weights', {})
        
        # Signal filtering
        self.min_strength = SignalStrength(cfg.get('min_strength', 2))  # MODERATE
        self.require_confirmation = cfg.get('require_confirmation', False)
        self.confirmation_count = cfg.get('confirmation_count', 2)
        
        # Signal aggregation
        self.aggregation_window_seconds = cfg.get('aggregation_window_seconds', 60)
        
        # State
        self.pending_signals: List[TradingSignal] = []
        self.signal_history: List[TradingSignal] = []
        self.max_history = cfg.get('max_history', 1000)
        
        # Statistics
        self.signals_generated = 0
        self.signals_filtered = 0
        self.signals_executed = 0
        
        logger.info("🎯 Rule-Based Signal Engine initialized")
        logger.info(f"   Enabled strategies: {len(self.enabled_strategies)}")
        logger.info(f"   Min strength: {self.min_strength.name}")
        logger.info(f"   Confirmation required: {self.require_confirmation}")
    
    def add_signal(self, signal: TradingSignal) -> bool:
        """
        Add a new signal
        
        Args:
            signal: Trading signal
            
        Returns:
            True if signal was accepted
        """
        self.signals_generated += 1
        
        # Check if strategy is enabled
        if self.enabled_strategies and signal.strategy_name not in self.enabled_strategies:
            logger.debug(f"Signal rejected: strategy {signal.strategy_name} not enabled")
            self.signals_filtered += 1
            return False
        
        # Check minimum strength
        if signal.strength.value < self.min_strength.value:
            logger.debug(f"Signal rejected: strength {signal.strength.name} < {self.min_strength.name}")
            self.signals_filtered += 1
            return False
        
        # Add to pending signals
        self.pending_signals.append(signal)
        
        # Clean old signals
        self._clean_old_signals()
        
        logger.info(f"📊 Signal added: {signal.strategy_name} - {signal.signal_type.value} {signal.symbol} @ {signal.price}")
        
        return True
    
    def get_actionable_signals(self) -> List[TradingSignal]:
        """
        Get signals that should be acted upon
        
        Returns:
            List of actionable signals
        """
        if not self.pending_signals:
            return []
        
        # Clean old signals first
        self._clean_old_signals()
        
        if not self.require_confirmation:
            # Return all pending signals
            return self.pending_signals
        
        # Group signals by symbol and type
        signal_groups: Dict[tuple, List[TradingSignal]] = {}
        
        for signal in self.pending_signals:
            key = (signal.symbol, signal.signal_type)
            if key not in signal_groups:
                signal_groups[key] = []
            signal_groups[key].append(signal)
        
        # Find groups with enough confirmation
        actionable = []
        
        for (symbol, signal_type), signals in signal_groups.items():
            if len(signals) >= self.confirmation_count:
                # Use signal with highest strength
                best_signal = max(signals, key=lambda s: s.strength.value)
                actionable.append(best_signal)
                logger.info(f"✅ Confirmed signal: {symbol} {signal_type.value} ({len(signals)} confirmations)")
        
        return actionable
    
    def mark_executed(self, signal: TradingSignal):
        """
        Mark signal as executed
        
        Args:
            signal: Executed signal
        """
        # Remove from pending
        if signal in self.pending_signals:
            self.pending_signals.remove(signal)
        
        # Add to history
        self.signal_history.append(signal)
        if len(self.signal_history) > self.max_history:
            self.signal_history = self.signal_history[-self.max_history:]
        
        self.signals_executed += 1
        
        logger.info(f"✅ Signal executed: {signal.strategy_name} - {signal.signal_type.value} {signal.symbol}")
    
    def clear_pending_signals(self, symbol: Optional[str] = None):
        """
        Clear pending signals
        
        Args:
            symbol: If provided, only clear signals for this symbol
        """
        if symbol:
            before = len(self.pending_signals)
            self.pending_signals = [s for s in self.pending_signals if s.symbol != symbol]
            after = len(self.pending_signals)
            logger.info(f"Cleared {before - after} pending signals for {symbol}")
        else:
            count = len(self.pending_signals)
            self.pending_signals.clear()
            logger.info(f"Cleared all {count} pending signals")
    
    def _clean_old_signals(self):
        """Remove signals older than aggregation window"""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - self.aggregation_window_seconds
        
        self.pending_signals = [
            s for s in self.pending_signals 
            if s.timestamp.timestamp() >= cutoff
        ]
    
    def enable_strategy(self, strategy_name: str):
        """Enable a strategy"""
        self.enabled_strategies.add(strategy_name)
        logger.info(f"✅ Enabled strategy: {strategy_name}")
    
    def disable_strategy(self, strategy_name: str):
        """Disable a strategy"""
        if strategy_name in self.enabled_strategies:
            self.enabled_strategies.remove(strategy_name)
        logger.info(f"❌ Disabled strategy: {strategy_name}")
    
    def set_strategy_weight(self, strategy_name: str, weight: float):
        """
        Set strategy weight
        
        Args:
            strategy_name: Strategy name
            weight: Weight (0.0-1.0)
        """
        self.strategy_weights[strategy_name] = weight
        logger.info(f"⚖️ Set {strategy_name} weight: {weight}")
    
    def get_weighted_signal_strength(self, signal: TradingSignal) -> float:
        """
        Calculate weighted signal strength
        
        Args:
            signal: Trading signal
            
        Returns:
            Weighted strength (0.0-4.0)
        """
        base_strength = signal.strength.value
        weight = self.strategy_weights.get(signal.strategy_name, 1.0)
        return base_strength * weight
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get signal engine statistics"""
        return {
            'signals_generated': self.signals_generated,
            'signals_filtered': self.signals_filtered,
            'signals_executed': self.signals_executed,
            'pending_signals': len(self.pending_signals),
            'history_size': len(self.signal_history),
            'enabled_strategies': len(self.enabled_strategies),
            'filter_rate': self.signals_filtered / self.signals_generated if self.signals_generated > 0 else 0,
            'execution_rate': self.signals_executed / self.signals_generated if self.signals_generated > 0 else 0
        }
    
    def get_pending_signals_summary(self) -> List[Dict[str, Any]]:
        """Get summary of pending signals"""
        return [s.to_dict() for s in self.pending_signals]
    
    def get_recent_signals(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent executed signals
        
        Args:
            count: Number of signals to return
            
        Returns:
            List of signal dictionaries
        """
        recent = self.signal_history[-count:] if len(self.signal_history) > count else self.signal_history
        return [s.to_dict() for s in reversed(recent)]
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            'enabled_strategies': list(self.enabled_strategies),
            'strategy_weights': self.strategy_weights,
            'min_strength': self.min_strength.name,
            'require_confirmation': self.require_confirmation,
            'confirmation_count': self.confirmation_count,
            'aggregation_window_seconds': self.aggregation_window_seconds
        }
