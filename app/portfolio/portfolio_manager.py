"""
Portfolio Manager
Handles position sizing, tracking, and portfolio-level operations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

from ..exchange.client import Position, Balance

logger = logging.getLogger(__name__)


@dataclass
class PortfolioSnapshot:
    """Portfolio state at a point in time"""
    timestamp: datetime
    total_equity: Decimal
    available_margin: Decimal
    used_margin: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    positions: List[Position]
    position_count: int
    long_exposure: Decimal
    short_exposure: Decimal
    net_exposure: Decimal
    leverage_ratio: Decimal


@dataclass
class PositionSizing:
    """Position sizing calculation result"""
    symbol: str
    side: str
    max_size: Decimal
    recommended_size: Decimal
    risk_amount: Decimal
    max_leverage: Decimal
    account_risk_pct: float
    position_risk_pct: float
    can_open: bool
    reason: str


class PortfolioManager:
    """
    Enterprise portfolio management with position sizing and risk controls
    """
    
    def __init__(self, exchange_client, config: Dict[str, Any]):
        """
        Initialize portfolio manager
        
        Args:
            exchange_client: HyperLiquid exchange client
            config: Portfolio configuration
        """
        self.client = exchange_client
        self.config = config
        
        # Portfolio state
        self.current_balance: Optional[Balance] = None
        self.current_positions: List[Position] = []
        self.portfolio_history: List[PortfolioSnapshot] = []
        
        # Risk limits from config
        self.max_positions = config.get('max_positions', 5)
        self.max_leverage = config.get('max_leverage', 10.0)
        self.max_account_risk_pct = config.get('max_account_risk_pct', 2.0)
        self.position_size_pct = config.get('position_size_pct', 20.0)
        self.max_correlation_exposure = config.get('max_correlation_exposure', 50.0)
        
        # Portfolio tracking
        self.initial_equity = None
        self.peak_equity = None
        self.drawdown = Decimal('0')
        self.max_drawdown = Decimal('0')
        
        # Performance metrics
        self.daily_returns: List[Decimal] = []
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        logger.info("💼 Portfolio Manager initialized")

    async def initialize(self):
        """Initialize portfolio manager"""
        try:
            # Get current portfolio state
            await self.update_portfolio_state()
            
            # Set initial equity
            if self.current_balance:
                self.initial_equity = self.current_balance.equity
                self.peak_equity = self.current_balance.equity
            
            logger.info(f"💰 Initial portfolio equity: ${self.initial_equity or 0:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize portfolio manager: {e}")
            raise

    async def update_portfolio_state(self):
        """Update current portfolio state from exchange"""
        try:
            # Get latest balance and positions
            self.current_balance = await self.client.get_account_state()
            self.current_positions = await self.client.get_positions()
            
            # Update peak equity and drawdown
            if self.current_balance and self.peak_equity:
                if self.current_balance.equity > self.peak_equity:
                    self.peak_equity = self.current_balance.equity
                
                # Calculate current drawdown
                self.drawdown = (self.peak_equity - self.current_balance.equity) / self.peak_equity * 100
                if self.drawdown > self.max_drawdown:
                    self.max_drawdown = self.drawdown
            
            # Create portfolio snapshot
            snapshot = self._create_portfolio_snapshot()
            self.portfolio_history.append(snapshot)
            
            # Keep only last 1000 snapshots
            if len(self.portfolio_history) > 1000:
                self.portfolio_history = self.portfolio_history[-1000:]
            
            logger.debug(f"📊 Portfolio updated - Equity: ${self.current_balance.equity:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update portfolio state: {e}")

    def _create_portfolio_snapshot(self) -> PortfolioSnapshot:
        """Create portfolio snapshot from current state"""
        if not self.current_balance:
            raise ValueError("No current balance data")
        
        # Calculate exposures
        long_exposure = sum(
            pos.size * pos.mark_price 
            for pos in self.current_positions 
            if pos.side == 'long'
        )
        
        short_exposure = sum(
            pos.size * pos.mark_price 
            for pos in self.current_positions 
            if pos.side == 'short'
        )
        
        net_exposure = long_exposure - short_exposure
        total_exposure = long_exposure + short_exposure
        
        # Calculate leverage ratio
        leverage_ratio = total_exposure / self.current_balance.equity if self.current_balance.equity > 0 else Decimal('0')
        
        return PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_equity=self.current_balance.equity,
            available_margin=self.current_balance.available_margin,
            used_margin=self.current_balance.margin_used,
            unrealized_pnl=self.current_balance.unrealized_pnl,
            realized_pnl=Decimal('0'),  # TODO: Track realized PNL
            positions=self.current_positions.copy(),
            position_count=len(self.current_positions),
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            net_exposure=net_exposure,
            leverage_ratio=leverage_ratio
        )

    async def calculate_position_size(
        self,
        symbol: str,
        side: str,
        entry_price: Decimal,
        stop_loss_price: Optional[Decimal] = None,
        risk_amount: Optional[Decimal] = None
    ) -> PositionSizing:
        """
        Calculate optimal position size based on risk parameters
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            entry_price: Expected entry price
            stop_loss_price: Stop loss price for risk calculation
            risk_amount: Fixed risk amount (overrides percentage)
            
        Returns:
            PositionSizing object with size calculations
        """
        try:
            await self.update_portfolio_state()
            
            if not self.current_balance:
                return PositionSizing(
                    symbol=symbol, side=side, max_size=Decimal('0'),
                    recommended_size=Decimal('0'), risk_amount=Decimal('0'),
                    max_leverage=Decimal('0'), account_risk_pct=0.0,
                    position_risk_pct=0.0, can_open=False,
                    reason="No balance data available"
                )
            
            # Check position limits
            if len(self.current_positions) >= self.max_positions:
                return PositionSizing(
                    symbol=symbol, side=side, max_size=Decimal('0'),
                    recommended_size=Decimal('0'), risk_amount=Decimal('0'),
                    max_leverage=Decimal('0'), account_risk_pct=0.0,
                    position_risk_pct=0.0, can_open=False,
                    reason=f"Maximum positions limit ({self.max_positions}) reached"
                )
            
            # Check if position already exists
            existing_position = self._get_position(symbol)
            if existing_position:
                return PositionSizing(
                    symbol=symbol, side=side, max_size=Decimal('0'),
                    recommended_size=Decimal('0'), risk_amount=Decimal('0'),
                    max_leverage=Decimal('0'), account_risk_pct=0.0,
                    position_risk_pct=0.0, can_open=False,
                    reason=f"Position already exists for {symbol}"
                )
            
            # Calculate risk amount
            if risk_amount is None:
                risk_amount = self.current_balance.equity * Decimal(self.max_account_risk_pct) / 100
            
            # Calculate position size based on available margin
            available_equity = self.current_balance.available_margin
            max_position_value = available_equity * Decimal(self.position_size_pct) / 100
            
            # Apply leverage limit
            max_leveraged_value = available_equity * Decimal(self.max_leverage)
            max_position_value = min(max_position_value, max_leveraged_value)
            
            # Calculate size based on risk (if stop loss provided)
            if stop_loss_price:
                price_diff = abs(entry_price - stop_loss_price)
                risk_per_unit = price_diff
                max_size_by_risk = risk_amount / risk_per_unit if risk_per_unit > 0 else Decimal('0')
            else:
                # Use default 2% risk per position
                risk_per_unit = entry_price * Decimal('0.02')
                max_size_by_risk = risk_amount / risk_per_unit
            
            # Calculate size based on position value limit
            max_size_by_value = max_position_value / entry_price
            
            # Take the smaller of the two
            max_size = min(max_size_by_risk, max_size_by_value)
            
            # Recommended size is 80% of max size for safety
            recommended_size = max_size * Decimal('0.8')
            
            # Round down to avoid precision issues
            max_size = max_size.quantize(Decimal('0.000001'), rounding=ROUND_DOWN)
            recommended_size = recommended_size.quantize(Decimal('0.000001'), rounding=ROUND_DOWN)
            
            # Calculate effective leverage for this position
            position_value = recommended_size * entry_price
            effective_leverage = position_value / available_equity if available_equity > 0 else Decimal('0')
            
            # Calculate risk percentages
            actual_risk = recommended_size * (entry_price * Decimal('0.02'))  # Assume 2% risk
            account_risk_pct = float((actual_risk / self.current_balance.equity) * 100)
            position_risk_pct = 2.0  # Default 2% per position
            
            # Check if we can open position
            can_open = (
                recommended_size > 0 and
                effective_leverage <= self.max_leverage and
                account_risk_pct <= self.max_account_risk_pct
            )
            
            reason = "OK" if can_open else "Risk limits exceeded"
            
            return PositionSizing(
                symbol=symbol,
                side=side,
                max_size=max_size,
                recommended_size=recommended_size,
                risk_amount=actual_risk,
                max_leverage=effective_leverage,
                account_risk_pct=account_risk_pct,
                position_risk_pct=position_risk_pct,
                can_open=can_open,
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return PositionSizing(
                symbol=symbol, side=side, max_size=Decimal('0'),
                recommended_size=Decimal('0'), risk_amount=Decimal('0'),
                max_leverage=Decimal('0'), account_risk_pct=0.0,
                position_risk_pct=0.0, can_open=False,
                reason=f"Calculation error: {e}"
            )

    def _get_position(self, symbol: str) -> Optional[Position]:
        """Get existing position for symbol"""
        for position in self.current_positions:
            if position.symbol == symbol:
                return position
        return None

    async def can_open_position(
        self,
        symbol: str,
        side: str,
        size: Decimal,
        price: Decimal
    ) -> Tuple[bool, str]:
        """
        Check if we can open a position with given parameters
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Position size
            price: Entry price
            
        Returns:
            Tuple of (can_open, reason)
        """
        try:
            await self.update_portfolio_state()
            
            # Check position count limit
            if len(self.current_positions) >= self.max_positions:
                return False, f"Maximum positions limit ({self.max_positions}) reached"
            
            # Check if position already exists
            if self._get_position(symbol):
                return False, f"Position already exists for {symbol}"
            
            if not self.current_balance:
                return False, "No balance data available"
            
            # Calculate position value and required margin
            position_value = size * price
            required_margin = position_value / Decimal(self.max_leverage)  # Conservative estimate
            
            # Check available margin
            if required_margin > self.current_balance.available_margin:
                return False, f"Insufficient margin: need ${required_margin:.2f}, have ${self.current_balance.available_margin:.2f}"
            
            # Check leverage limit
            current_exposure = sum(
                pos.size * pos.mark_price for pos in self.current_positions
            )
            new_total_exposure = current_exposure + position_value
            new_leverage = new_total_exposure / self.current_balance.equity if self.current_balance.equity > 0 else Decimal('999')
            
            if new_leverage > self.max_leverage:
                return False, f"Leverage limit exceeded: {new_leverage:.1f}x > {self.max_leverage}x"
            
            # Check risk limit (assume 2% risk per position)
            risk_amount = position_value * Decimal('0.02')
            risk_pct = (risk_amount / self.current_balance.equity) * 100
            
            if risk_pct > self.max_account_risk_pct:
                return False, f"Account risk limit exceeded: {risk_pct:.1f}% > {self.max_account_risk_pct}%"
            
            return True, "OK"
            
        except Exception as e:
            logger.error(f"❌ Error checking position feasibility: {e}")
            return False, f"Error: {e}"

    async def close_all_positions(self, reason: str = "Manual close"):
        """
        Close all open positions
        
        Args:
            reason: Reason for closing positions
        """
        if not self.current_positions:
            logger.info("No positions to close")
            return
        
        logger.warning(f"🚨 Closing all {len(self.current_positions)} positions - Reason: {reason}")
        
        close_tasks = []
        for position in self.current_positions:
            # Determine close side (opposite of position side)
            close_side = 'sell' if position.side == 'long' else 'buy'
            
            # Create close order task
            task = self.client.place_order(
                symbol=position.symbol,
                side=close_side,
                size=position.size,
                order_type='market',
                reduce_only=True
            )
            close_tasks.append(task)
        
        # Execute all close orders concurrently
        results = await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Log results
        successful_closes = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to close {self.current_positions[i].symbol}: {result}")
            elif result.get('success', False):
                successful_closes += 1
                logger.info(f"✅ Closed position: {self.current_positions[i].symbol}")
            else:
                logger.error(f"❌ Failed to close {self.current_positions[i].symbol}: {result.get('error', 'Unknown')}")
        
        logger.info(f"📊 Closed {successful_closes}/{len(self.current_positions)} positions")

    async def reduce_exposure(self, target_leverage: float = 5.0):
        """
        Reduce portfolio exposure to target leverage
        
        Args:
            target_leverage: Target leverage ratio
        """
        await self.update_portfolio_state()
        
        if not self.current_balance or not self.current_positions:
            return
        
        # Calculate current leverage
        total_exposure = sum(
            pos.size * pos.mark_price for pos in self.current_positions
        )
        current_leverage = float(total_exposure / self.current_balance.equity)
        
        if current_leverage <= target_leverage:
            logger.info(f"✅ Leverage {current_leverage:.1f}x is within target {target_leverage:.1f}x")
            return
        
        logger.warning(f"🔄 Reducing leverage from {current_leverage:.1f}x to {target_leverage:.1f}x")
        
        # Calculate how much exposure to reduce
        target_exposure = self.current_balance.equity * Decimal(target_leverage)
        excess_exposure = total_exposure - target_exposure
        reduction_ratio = excess_exposure / total_exposure
        
        # Reduce each position proportionally
        for position in self.current_positions:
            reduction_size = position.size * reduction_ratio
            close_side = 'sell' if position.side == 'long' else 'buy'
            
            try:
                result = await self.client.place_order(
                    symbol=position.symbol,
                    side=close_side,
                    size=reduction_size,
                    order_type='market',
                    reduce_only=True
                )
                
                if result.get('success', False):
                    logger.info(f"✅ Reduced {position.symbol} by {reduction_size}")
                else:
                    logger.error(f"❌ Failed to reduce {position.symbol}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ Error reducing {position.symbol}: {e}")

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        if not self.current_balance:
            return {"error": "No portfolio data available"}
        
        # Calculate performance metrics
        total_return_pct = 0.0
        if self.initial_equity and self.initial_equity > 0:
            total_return_pct = float(
                (self.current_balance.equity - self.initial_equity) / self.initial_equity * 100
            )
        
        # Calculate win rate
        total_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # Calculate current leverage
        total_exposure = sum(
            pos.size * pos.mark_price for pos in self.current_positions
        )
        current_leverage = float(total_exposure / self.current_balance.equity) if self.current_balance.equity > 0 else 0.0
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'account': {
                'total_equity': float(self.current_balance.equity),
                'available_margin': float(self.current_balance.available_margin),
                'used_margin': float(self.current_balance.margin_used),
                'unrealized_pnl': float(self.current_balance.unrealized_pnl)
            },
            'performance': {
                'initial_equity': float(self.initial_equity or 0),
                'peak_equity': float(self.peak_equity or 0),
                'current_drawdown_pct': float(self.drawdown),
                'max_drawdown_pct': float(self.max_drawdown),
                'total_return_pct': total_return_pct
            },
            'positions': {
                'count': len(self.current_positions),
                'max_allowed': self.max_positions,
                'symbols': [pos.symbol for pos in self.current_positions],
                'total_exposure': float(total_exposure),
                'current_leverage': current_leverage,
                'max_leverage': self.max_leverage
            },
            'trading': {
                'total_trades': total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate_pct': win_rate
            },
            'risk': {
                'max_account_risk_pct': self.max_account_risk_pct,
                'position_size_pct': self.position_size_pct,
                'max_correlation_exposure': self.max_correlation_exposure
            }
        }

    def get_position_summary(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get detailed position summary"""
        positions = self.current_positions
        if symbol:
            positions = [pos for pos in positions if pos.symbol == symbol]
        
        summary = []
        for pos in positions:
            # Calculate PNL percentage
            pnl_pct = 0.0
            if pos.entry_price > 0:
                if pos.side == 'long':
                    pnl_pct = float((pos.mark_price - pos.entry_price) / pos.entry_price * 100)
                else:
                    pnl_pct = float((pos.entry_price - pos.mark_price) / pos.entry_price * 100)
            
            summary.append({
                'symbol': pos.symbol,
                'side': pos.side,
                'size': float(pos.size),
                'entry_price': float(pos.entry_price),
                'mark_price': float(pos.mark_price),
                'unrealized_pnl': float(pos.unrealized_pnl),
                'unrealized_pnl_pct': pnl_pct,
                'margin_used': float(pos.margin_used),
                'leverage': float(pos.leverage),
                'timestamp': pos.timestamp.isoformat()
            })
        
        return summary

    async def emergency_shutdown(self, reason: str):
        """
        Emergency portfolio shutdown
        
        Args:
            reason: Reason for emergency shutdown
        """
        logger.critical(f"🚨 EMERGENCY PORTFOLIO SHUTDOWN: {reason}")
        
        try:
            # Cancel all open orders first
            await self.client.cancel_all_orders()
            
            # Close all positions
            await self.close_all_positions(f"Emergency shutdown: {reason}")
            
            logger.critical("🚨 Emergency shutdown completed")
            
        except Exception as e:
            logger.critical(f"🚨 CRITICAL: Emergency shutdown failed: {e}")

    def update_trade_statistics(self, pnl: Decimal):
        """
        Update trading statistics
        
        Args:
            pnl: Trade P&L (positive for profit, negative for loss)
        """
        self.trade_count += 1
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        logger.debug(f"📊 Trade #{self.trade_count}: PNL ${pnl:.2f}")

    def get_risk_metrics(self) -> Dict[str, Any]:
        """Calculate and return risk metrics"""
        if not self.current_balance:
            return {"error": "No portfolio data available"}
        
        # Calculate value at risk (simplified)
        total_exposure = sum(
            pos.size * pos.mark_price for pos in self.current_positions
        )
        
        # Assume 2% daily volatility for VaR calculation
        daily_var_95 = total_exposure * Decimal('0.02') * Decimal('1.645')  # 95% confidence
        
        # Calculate maximum potential loss (if all positions hit stop loss)
        max_potential_loss = total_exposure * Decimal('0.02')  # Assume 2% stop loss
        
        # Risk ratios
        var_ratio = float(daily_var_95 / self.current_balance.equity * 100) if self.current_balance.equity > 0 else 0.0
        max_loss_ratio = float(max_potential_loss / self.current_balance.equity * 100) if self.current_balance.equity > 0 else 0.0
        
        return {
            'total_exposure': float(total_exposure),
            'daily_var_95': float(daily_var_95),
            'var_ratio_pct': var_ratio,
            'max_potential_loss': float(max_potential_loss),
            'max_loss_ratio_pct': max_loss_ratio,
            'leverage': float(total_exposure / self.current_balance.equity) if self.current_balance.equity > 0 else 0.0,
            'margin_usage_pct': float(self.current_balance.margin_used / self.current_balance.equity * 100) if self.current_balance.equity > 0 else 0.0
        }