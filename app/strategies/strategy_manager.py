"""
Strategy Manager
Coordinates multiple trading strategies and resolves conflicts
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio

# Import all strategies
from app.strategies.rule_based.scalping_2pct import ScalpingStrategy2Pct
from app.strategies.rule_based.mean_reversion import MeanReversionStrategy
from app.strategies.rule_based.breakout import BreakoutStrategy
from app.strategies.rule_based.volume_spike import VolumeSpikeStrategy
from app.strategies.rule_based.swing_trader import SwingTradingStrategy

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    Manages multiple strategies in parallel
    - Runs all strategies simultaneously
    - Returns first valid signal
    - Prevents conflicts (max 1 position)
    - Tracks performance per strategy
    """
    
    def __init__(self, symbol: str, config: Dict[str, Any] = None):
        """
        Initialize strategy manager
        
        Args:
            symbol: Trading symbol
            config: Strategy configuration
        """
        self.symbol = symbol
        self.config = config if config is not None else {}
        
        # Initialize all strategies
        # ENTERPRISE MODE: Only professional-grade strategies with proven filters
        self.strategies = {
            'swing': SwingTradingStrategy(symbol, config),  # Primary: 70% win rate target
            'momentum': ScalpingStrategy2Pct(symbol, config),  # Secondary: Confirmed scalps only
            # DISABLED: Low win rate strategies
            # 'mean_reversion': MeanReversionStrategy(symbol, config),  # 37.5% win rate
            # 'breakout': BreakoutStrategy(symbol, config),  # No filters
            # 'volume_spike': VolumeSpikeStrategy(symbol, config)  # Overtrading
        }
        
        # Performance tracking
        self.strategy_stats = {
            'swing': {'signals': 0, 'trades': 0},
            'momentum': {'signals': 0, 'trades': 0}
        }
        
        # Execution mode
        self.execution_mode = self.config.get('strategy_mode', 'first_signal')  # or 'round_robin', 'priority'
        self.last_strategy_used = None
        
        logger.info(f"🎯 ENTERPRISE Strategy Manager initialized for {symbol}")
        logger.info(f"   Active Strategies: {len(self.strategies)} (Professional Grade Only)")
        logger.info(f"   • Swing Trading: 70% win rate target, 5/8 signal score, ADX>25")
        logger.info(f"   • Momentum/Scalping: 0.3% threshold, trend filter, 2-bar confirmation")
        logger.info(f"   Execution Mode: {self.execution_mode}")
        logger.info(f"   🚫 DISABLED: Mean Reversion, Breakout, Volume Spike (low win rate)")
    
    async def generate_signal(self, market_data: Dict[str, Any],
                             account_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate signal from all strategies
        Returns first valid signal found
        
        Args:
            market_data: Current market state
            account_state: Current account state
            
        Returns:
            Trading signal or None
        """
        # Check if already in position
        positions = account_state.get('positions', [])
        if any(p['symbol'] == self.symbol for p in positions):
            return None  # Already in position, don't generate new signals
        
        # Run all strategies in parallel
        signals = await self._run_all_strategies(market_data, account_state)
        
        # Filter valid signals
        valid_signals = [s for s in signals if s is not None]
        
        if not valid_signals:
            return None
        
        # Select signal based on execution mode
        if self.execution_mode == 'first_signal':
            # Return first valid signal (fastest)
            selected_signal = valid_signals[0]
            
        elif self.execution_mode == 'round_robin':
            # Rotate between strategies
            selected_signal = self._round_robin_select(valid_signals)
            
        elif self.execution_mode == 'priority':
            # Priority order: volume_spike > breakout > momentum > mean_reversion
            selected_signal = self._priority_select(valid_signals)
            
        else:
            selected_signal = valid_signals[0]
        
        # Update statistics
        strategy_name = selected_signal['strategy']
        if strategy_name in self.strategy_stats:
            self.strategy_stats[strategy_name]['signals'] += 1
        
        self.last_strategy_used = strategy_name
        
        logger.info(f"📊 Signal selected: {strategy_name} ({len(valid_signals)} strategies triggered)")
        
        return selected_signal
    
    async def _run_all_strategies(self, market_data: Dict[str, Any],
                                   account_state: Dict[str, Any]) -> List[Optional[Dict[str, Any]]]:
        """
        Run all strategies in parallel
        
        Args:
            market_data: Market data
            account_state: Account state
            
        Returns:
            List of signals (may contain None)
        """
        tasks = []
        strategy_names = []
        
        for name, strategy in self.strategies.items():
            task = strategy.generate_signal(market_data, account_state)
            tasks.append(task)
            strategy_names.append(name)
        
        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        signals = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Strategy {strategy_names[i]} error: {result}")
                signals.append(None)
            else:
                signals.append(result)
        
        return signals
    
    def _round_robin_select(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Round-robin selection between strategies
        
        Args:
            signals: List of valid signals
            
        Returns:
            Selected signal
        """
        if not self.last_strategy_used:
            return signals[0]
        
        # Find next strategy in rotation
        strategy_order = ['momentum', 'mean_reversion', 'breakout', 'volume_spike']
        
        try:
            last_idx = strategy_order.index(self.last_strategy_used)
            next_strategies = strategy_order[last_idx + 1:] + strategy_order[:last_idx + 1]
            
            # Find first signal from next strategies
            for strategy_name in next_strategies:
                for signal in signals:
                    if signal['strategy'] == strategy_name:
                        return signal
        except (ValueError, IndexError):
            pass
        
        return signals[0]
    
    def _priority_select(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Priority-based selection
        Higher conviction setups get priority
        
        Priority order:
        1. volume_spike (highest conviction - unusual activity)
        2. breakout (high conviction - clear momentum)
        3. momentum (medium conviction - standard scalp)
        4. mean_reversion (lower conviction - counter-trend)
        
        Args:
            signals: List of valid signals
            
        Returns:
            Highest priority signal
        """
        priority_order = ['VolumeSpikeStrategy', 'BreakoutStrategy', 
                         'ScalpingStrategy2Pct', 'MeanReversionStrategy']
        
        for priority_strategy in priority_order:
            for signal in signals:
                if signal['strategy'] == priority_strategy:
                    return signal
        
        return signals[0]
    
    def record_trade_execution(self, signal: Dict[str, Any], result: Dict[str, Any]):
        """
        Record trade execution for a strategy
        
        Args:
            signal: Original signal
            result: Execution result
        """
        strategy_name = signal.get('strategy')
        
        if strategy_name in self.strategy_stats:
            self.strategy_stats[strategy_name]['trades'] += 1
        
        # Pass to individual strategy
        strategy_key = self._get_strategy_key(strategy_name)
        if strategy_key and strategy_key in self.strategies:
            self.strategies[strategy_key].record_trade_execution(signal, result)
    
    def _get_strategy_key(self, strategy_class_name: str) -> Optional[str]:
        """
        Map strategy class name to internal key
        
        Args:
            strategy_class_name: Class name (e.g., 'Scalping2PctStrategy')
            
        Returns:
            Internal key (e.g., 'momentum')
        """
        mapping = {
            'ScalpingStrategy2Pct': 'momentum',
            'MeanReversionStrategy': 'mean_reversion',
            'BreakoutStrategy': 'breakout',
            'VolumeSpikeStrategy': 'volume_spike'
        }
        return mapping.get(strategy_class_name)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics for all strategies
        
        Returns:
            Statistics dictionary
        """
        total_signals = sum(s['signals'] for s in self.strategy_stats.values())
        total_trades = sum(s['trades'] for s in self.strategy_stats.values())
        
        stats = {
            'manager': 'StrategyManager',
            'symbol': self.symbol,
            'total_signals': total_signals,
            'total_trades': total_trades,
            'execution_rate': total_trades / total_signals if total_signals > 0 else 0,
            'execution_mode': self.execution_mode,
            'last_strategy_used': self.last_strategy_used,
            'strategy_breakdown': {}
        }
        
        # Add per-strategy stats
        for name, strategy in self.strategies.items():
            strategy_stats = strategy.get_statistics()
            stats['strategy_breakdown'][name] = {
                'signals': self.strategy_stats[name]['signals'],
                'trades': self.strategy_stats[name]['trades'],
                'execution_rate': (self.strategy_stats[name]['trades'] / 
                                  self.strategy_stats[name]['signals'] 
                                  if self.strategy_stats[name]['signals'] > 0 else 0)
            }
        
        return stats
    
    def log_statistics(self):
        """Log current statistics"""
        stats = self.get_statistics()
        
        logger.info(f"📊 Strategy Manager Statistics:")
        logger.info(f"   Total Signals: {stats['total_signals']}")
        logger.info(f"   Total Trades: {stats['total_trades']}")
        logger.info(f"   Execution Rate: {stats['execution_rate']:.1%}")
        logger.info(f"   Last Used: {stats['last_strategy_used']}")
        
        for name, breakdown in stats['strategy_breakdown'].items():
            logger.info(f"   {name}: {breakdown['signals']} signals, "
                       f"{breakdown['trades']} trades ({breakdown['execution_rate']:.1%})")
