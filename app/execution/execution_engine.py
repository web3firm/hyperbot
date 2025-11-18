"""
Execution Engine
Order routing, trade management, and position lifecycle handling
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from ..signals.signal_generators import TradingSignal, SignalType
from ..exchange.client import Position

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status types"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


@dataclass
class Order:
    """Order data structure"""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    size: Decimal
    order_type: OrderType
    status: OrderStatus
    
    # Prices
    price: Optional[Decimal] = None  # Limit price
    stop_price: Optional[Decimal] = None  # Stop trigger price
    
    # Execution details
    filled_size: Decimal = Decimal('0')
    average_fill_price: Optional[Decimal] = None
    commission: Decimal = Decimal('0')
    
    # Metadata
    strategy_name: str = ""
    signal_id: Optional[str] = None
    parent_order_id: Optional[str] = None  # For bracket orders
    reduce_only: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Risk management
    time_in_force: str = "GTC"  # GTC, IOC, FOK
    expiry_time: Optional[datetime] = None


@dataclass
class Trade:
    """Individual trade/fill data"""
    trade_id: str
    order_id: str
    symbol: str
    side: str
    size: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime
    
    # P&L calculation
    pnl: Optional[Decimal] = None
    pnl_pct: Optional[float] = None


@dataclass
class PositionManager:
    """Manages individual position lifecycle"""
    symbol: str
    position: Optional[Position] = None
    entry_orders: List[Order] = field(default_factory=list)
    exit_orders: List[Order] = field(default_factory=list)
    stop_loss_order: Optional[Order] = None
    take_profit_order: Optional[Order] = None
    
    # Position state
    is_active: bool = False
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    
    # Risk management
    max_loss: Optional[Decimal] = None
    target_profit: Optional[Decimal] = None
    
    # Performance tracking
    realized_pnl: Decimal = Decimal('0')
    max_favorable: Decimal = Decimal('0')
    max_adverse: Decimal = Decimal('0')


class ExecutionEngine:
    """
    Enterprise execution engine with advanced order management
    """
    
    def __init__(
        self, 
        exchange_client, 
        portfolio_manager, 
        risk_manager, 
        config: Dict[str, Any]
    ):
        """
        Initialize execution engine
        
        Args:
            exchange_client: Exchange client instance
            portfolio_manager: Portfolio manager instance
            risk_manager: Risk manager instance
            config: Execution configuration
        """
        self.client = exchange_client
        self.portfolio_manager = portfolio_manager
        self.risk_manager = risk_manager
        self.config = config
        
        # Order management
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.trade_history: List[Trade] = []
        
        # Position management
        self.position_managers: Dict[str, PositionManager] = {}
        
        # Execution parameters
        self.max_slippage_pct = config.get('max_slippage_pct', 1.0)
        self.order_timeout_seconds = config.get('order_timeout_seconds', 30)
        self.enable_bracket_orders = config.get('enable_bracket_orders', True)
        self.default_time_in_force = config.get('default_time_in_force', 'GTC')
        
        # Market data for execution
        self.latest_prices: Dict[str, Decimal] = {}
        self.orderbook_data: Dict[str, Any] = {}
        
        # Background tasks
        self.order_monitor_task: Optional[asyncio.Task] = None
        self.position_monitor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.orders_submitted = 0
        self.orders_filled = 0
        self.orders_cancelled = 0
        self.total_commission = Decimal('0')
        
        logger.info("⚡ Execution Engine initialized")

    async def initialize(self):
        """Initialize the execution engine"""
        try:
            # Start monitoring tasks
            self.order_monitor_task = asyncio.create_task(self._order_monitor_loop())
            self.position_monitor_task = asyncio.create_task(self._position_monitor_loop())
            
            logger.info("✅ Execution engine started")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize execution engine: {e}")
            raise

    async def shutdown(self):
        """Shutdown the execution engine"""
        logger.info("🛑 Shutting down execution engine...")
        
        try:
            # Cancel all active orders
            await self._cancel_all_orders("Engine shutdown")
            
            # Cancel monitoring tasks
            if self.order_monitor_task:
                self.order_monitor_task.cancel()
            if self.position_monitor_task:
                self.position_monitor_task.cancel()
            
            logger.info("✅ Execution engine shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

    async def execute_signal(self, signal: TradingSignal) -> Optional[str]:
        """
        Execute a trading signal
        
        Args:
            signal: Trading signal to execute
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            logger.info(f"⚡ Executing signal: {signal.signal_type.value} {signal.symbol} @ {signal.price}")
            
            # Validate signal
            if not await self._validate_signal(signal):
                return None
            
            # Determine order parameters
            order_params = await self._prepare_order_from_signal(signal)
            if not order_params:
                return None
            
            # Execute the order
            order_id = await self._submit_order(**order_params)
            
            if order_id and self.enable_bracket_orders:
                # Submit stop loss and take profit orders
                await self._submit_bracket_orders(signal, order_id)
            
            return order_id
            
        except Exception as e:
            logger.error(f"❌ Error executing signal: {e}")
            return None

    async def _validate_signal(self, signal: TradingSignal) -> bool:
        """Validate signal before execution"""
        # Check if signal is expired
        if signal.expiry_time and signal.expiry_time < datetime.now(timezone.utc):
            logger.warning(f"⚠️ Signal expired: {signal.symbol}")
            return False
        
        # Risk validation
        side = 'buy' if signal.signal_type in [SignalType.ENTRY_LONG] else 'sell'
        
        is_valid, reason = await self.risk_manager.validate_order(
            symbol=signal.symbol,
            side=side,
            size=signal.position_size or Decimal('1'),
            price=signal.price
        )
        
        if not is_valid:
            logger.warning(f"⚠️ Risk check failed for {signal.symbol}: {reason}")
            return False
        
        return True

    async def _prepare_order_from_signal(self, signal: TradingSignal) -> Optional[Dict[str, Any]]:
        """Prepare order parameters from signal"""
        try:
            # Determine side
            if signal.signal_type in [SignalType.ENTRY_LONG]:
                side = 'buy'
            elif signal.signal_type in [SignalType.ENTRY_SHORT]:
                side = 'sell'
            else:
                logger.warning(f"⚠️ Unsupported signal type: {signal.signal_type}")
                return None
            
            # Calculate position size if not provided
            if not signal.position_size:
                sizing = await self.portfolio_manager.calculate_position_size(
                    symbol=signal.symbol,
                    side=side,
                    entry_price=signal.price,
                    stop_loss_price=signal.stop_loss
                )
                
                if not sizing.can_open:
                    logger.warning(f"⚠️ Cannot open position: {sizing.reason}")
                    return None
                
                position_size = sizing.recommended_size
            else:
                position_size = signal.position_size
            
            # Get current market price for slippage check
            current_price = await self._get_current_price(signal.symbol)
            if current_price:
                slippage_pct = abs(float(signal.price - current_price) / float(current_price)) * 100
                if slippage_pct > self.max_slippage_pct:
                    logger.warning(f"⚠️ Slippage too high: {slippage_pct:.2f}%")
                    # Use market order instead
                    order_type = OrderType.MARKET
                    price = None
                else:
                    order_type = OrderType.LIMIT
                    price = signal.price
            else:
                # No current price data, use limit order
                order_type = OrderType.LIMIT
                price = signal.price
            
            return {
                'symbol': signal.symbol,
                'side': side,
                'size': position_size,
                'order_type': order_type,
                'price': price,
                'strategy_name': signal.strategy_name,
                'signal_id': getattr(signal, 'id', None)
            }
            
        except Exception as e:
            logger.error(f"❌ Error preparing order from signal: {e}")
            return None

    async def _submit_order(
        self,
        symbol: str,
        side: str,
        size: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        reduce_only: bool = False,
        strategy_name: str = "",
        signal_id: Optional[str] = None,
        time_in_force: str = "GTC"
    ) -> Optional[str]:
        """
        Submit order to exchange
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size
            order_type: Order type
            price: Limit price (if applicable)
            stop_price: Stop price (if applicable)
            reduce_only: Whether this is a reduce-only order
            strategy_name: Name of strategy placing order
            signal_id: Associated signal ID
            time_in_force: Time in force
            
        Returns:
            Order ID if successful
        """
        try:
            # Generate unique order ID
            order_id = str(uuid.uuid4())
            
            # Create order object
            order = Order(
                order_id=order_id,
                symbol=symbol,
                side=side,
                size=size,
                order_type=order_type,
                status=OrderStatus.PENDING,
                price=price,
                stop_price=stop_price,
                reduce_only=reduce_only,
                strategy_name=strategy_name,
                signal_id=signal_id,
                time_in_force=time_in_force
            )
            
            # Set expiry time if not GTC
            if time_in_force == "IOC":
                order.expiry_time = datetime.now(timezone.utc) + timedelta(seconds=30)
            elif time_in_force == "FOK":
                order.expiry_time = datetime.now(timezone.utc) + timedelta(seconds=10)
            
            # Add to active orders
            self.active_orders[order_id] = order
            
            # Submit to exchange
            result = await self.client.place_order(
                symbol=symbol,
                side=side,
                size=size,
                order_type=order_type.value,
                price=price,
                reduce_only=reduce_only,
                time_in_force=time_in_force.lower(),
                client_order_id=order_id
            )
            
            if result.get('success', False):
                # Update order status
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = datetime.now(timezone.utc)
                
                self.orders_submitted += 1
                
                logger.info(f"✅ Order submitted: {order_id} - {side} {size} {symbol}")
                
                return order_id
            else:
                # Order rejected
                order.status = OrderStatus.REJECTED
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Order rejected: {error_msg}")
                
                # Remove from active orders
                del self.active_orders[order_id]
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error submitting order: {e}")
            
            # Clean up failed order
            if order_id in self.active_orders:
                del self.active_orders[order_id]
            
            return None

    async def _submit_bracket_orders(self, signal: TradingSignal, parent_order_id: str):
        """Submit stop loss and take profit orders for position"""
        try:
            if not signal.stop_loss and not signal.take_profit:
                return
            
            parent_order = self.active_orders.get(parent_order_id)
            if not parent_order:
                return
            
            # Determine position side
            will_be_long = parent_order.side == 'buy'
            
            # Submit stop loss order
            if signal.stop_loss:
                sl_side = 'sell' if will_be_long else 'buy'
                
                await self._submit_order(
                    symbol=signal.symbol,
                    side=sl_side,
                    size=parent_order.size,
                    order_type=OrderType.STOP_MARKET,
                    stop_price=signal.stop_loss,
                    reduce_only=True,
                    strategy_name=signal.strategy_name,
                    signal_id=signal.signal_id
                )
            
            # Submit take profit order
            if signal.take_profit:
                tp_side = 'sell' if will_be_long else 'buy'
                
                await self._submit_order(
                    symbol=signal.symbol,
                    side=tp_side,
                    size=parent_order.size,
                    order_type=OrderType.LIMIT,
                    price=signal.take_profit,
                    reduce_only=True,
                    strategy_name=signal.strategy_name,
                    signal_id=signal.signal_id
                )
                
        except Exception as e:
            logger.error(f"❌ Error submitting bracket orders: {e}")

    async def cancel_order(self, order_id: str, reason: str = "Manual cancel") -> bool:
        """
        Cancel an active order
        
        Args:
            order_id: Order ID to cancel
            reason: Reason for cancellation
            
        Returns:
            True if successful
        """
        try:
            order = self.active_orders.get(order_id)
            if not order:
                logger.warning(f"⚠️ Order not found: {order_id}")
                return False
            
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                logger.warning(f"⚠️ Cannot cancel order in status: {order.status.value}")
                return False
            
            # Cancel on exchange
            success = await self.client.cancel_order(order.symbol, order_id)
            
            if success:
                order.status = OrderStatus.CANCELLED
                self.orders_cancelled += 1
                logger.info(f"✅ Order cancelled: {order_id} - {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error cancelling order {order_id}: {e}")
            return False

    async def _cancel_all_orders(self, reason: str = "Cancel all"):
        """Cancel all active orders"""
        order_ids = list(self.active_orders.keys())
        
        if not order_ids:
            return
        
        logger.warning(f"🚨 Cancelling all {len(order_ids)} active orders: {reason}")
        
        # Cancel all orders concurrently
        cancel_tasks = [self.cancel_order(order_id, reason) for order_id in order_ids]
        results = await asyncio.gather(*cancel_tasks, return_exceptions=True)
        
        cancelled_count = sum(1 for result in results if result is True)
        logger.info(f"📊 Cancelled {cancelled_count}/{len(order_ids)} orders")

    async def _order_monitor_loop(self):
        """Background task to monitor order status"""
        try:
            while True:
                await self._update_order_statuses()
                await self._check_order_timeouts()
                await asyncio.sleep(5)  # Check every 5 seconds
                
        except asyncio.CancelledError:
            logger.info("Order monitor loop cancelled")
        except Exception as e:
            logger.error(f"❌ Order monitor error: {e}")

    async def _update_order_statuses(self):
        """Update status of active orders"""
        if not self.active_orders:
            return
        
        try:
            # Get open orders from exchange
            open_orders = await self.client.get_open_orders()
            open_order_ids = {order.get('cloid', order.get('oid')) for order in open_orders}
            
            # Update orders that are no longer open
            for order_id, order in list(self.active_orders.items()):
                if order.status == OrderStatus.SUBMITTED and order_id not in open_order_ids:
                    # Order is no longer open, it might be filled
                    await self._check_order_fill(order)
                    
        except Exception as e:
            logger.error(f"❌ Error updating order statuses: {e}")

    async def _check_order_fill(self, order: Order):
        """Check if an order has been filled"""
        try:
            # Get recent trades to find fills
            trades = await self.client.get_trade_history(order.symbol, limit=10)
            
            # Look for trades matching our order
            for trade in trades:
                # Check if trade matches order (simplified - in reality would need better matching)
                if (abs(trade.size - order.size) < Decimal('0.001') and
                    trade.side.lower() == order.side.lower() and
                    (trade.timestamp - order.submitted_at).total_seconds() < 300):  # Within 5 minutes
                    
                    # Mark as filled
                    order.status = OrderStatus.FILLED
                    order.filled_size = trade.size
                    order.average_fill_price = trade.price
                    order.commission = trade.commission
                    order.filled_at = trade.timestamp
                    
                    self.orders_filled += 1
                    self.total_commission += trade.commission
                    
                    logger.info(f"✅ Order filled: {order.order_id} - {order.size} @ {order.average_fill_price}")
                    
                    # Remove from active orders
                    if order.order_id in self.active_orders:
                        del self.active_orders[order.order_id]
                    
                    # Move to history
                    self.order_history.append(order)
                    
                    # Create trade record
                    trade_record = Trade(
                        trade_id=trade.id,
                        order_id=order.order_id,
                        symbol=order.symbol,
                        side=order.side,
                        size=trade.size,
                        price=trade.price,
                        commission=trade.commission,
                        timestamp=trade.timestamp
                    )
                    self.trade_history.append(trade_record)
                    
                    # Update position manager
                    await self._update_position_manager(order, trade_record)
                    
                    break
                    
        except Exception as e:
            logger.error(f"❌ Error checking order fill: {e}")

    async def _check_order_timeouts(self):
        """Check for expired orders"""
        now = datetime.now(timezone.utc)
        expired_orders = []
        
        for order_id, order in self.active_orders.items():
            if order.expiry_time and order.expiry_time < now:
                expired_orders.append(order_id)
            elif order.status == OrderStatus.SUBMITTED:
                # Check if order has been pending too long
                time_since_submit = (now - order.submitted_at).total_seconds()
                if time_since_submit > self.order_timeout_seconds:
                    expired_orders.append(order_id)
        
        # Cancel expired orders
        for order_id in expired_orders:
            await self.cancel_order(order_id, "Order timeout")

    async def _position_monitor_loop(self):
        """Background task to monitor position status"""
        try:
            while True:
                await self._update_position_managers()
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info("Position monitor loop cancelled")
        except Exception as e:
            logger.error(f"❌ Position monitor error: {e}")

    async def _update_position_managers(self):
        """Update all position managers with current data"""
        try:
            # Get current positions from portfolio manager
            positions = await self.portfolio_manager.get_positions()
            position_dict = {pos.symbol: pos for pos in positions}
            
            # Update existing position managers
            for symbol, pm in self.position_managers.items():
                current_position = position_dict.get(symbol)
                
                if current_position:
                    pm.position = current_position
                    pm.is_active = True
                    
                    # Calculate unrealized P&L extremes
                    if pm.position and pm.position.entry_price > 0:
                        unrealized_pnl = pm.position.unrealized_pnl
                        
                        if unrealized_pnl > pm.max_favorable:
                            pm.max_favorable = unrealized_pnl
                        elif unrealized_pnl < pm.max_adverse:
                            pm.max_adverse = unrealized_pnl
                else:
                    # Position closed
                    if pm.is_active:
                        pm.is_active = False
                        pm.exit_time = datetime.now(timezone.utc)
                        logger.info(f"📊 Position closed: {symbol}")
            
            # Create position managers for new positions
            for symbol, position in position_dict.items():
                if symbol not in self.position_managers:
                    pm = PositionManager(
                        symbol=symbol,
                        position=position,
                        is_active=True,
                        entry_time=position.timestamp
                    )
                    self.position_managers[symbol] = pm
                    logger.info(f"📊 New position tracked: {symbol}")
                    
        except Exception as e:
            logger.error(f"❌ Error updating position managers: {e}")

    async def _update_position_manager(self, order: Order, trade: Trade):
        """Update position manager with new trade"""
        try:
            symbol = order.symbol
            
            if symbol not in self.position_managers:
                self.position_managers[symbol] = PositionManager(symbol=symbol)
            
            pm = self.position_managers[symbol]
            
            # Add order to appropriate list
            if order.reduce_only:
                pm.exit_orders.append(order)
            else:
                pm.entry_orders.append(order)
                if not pm.entry_time:
                    pm.entry_time = trade.timestamp
            
            # Calculate realized P&L if position is closed
            if order.reduce_only and pm.position:
                # Simple P&L calculation (would need more sophisticated logic for partial closes)
                if pm.position.side == 'long':
                    pnl = (trade.price - pm.position.entry_price) * trade.size
                else:
                    pnl = (pm.position.entry_price - trade.price) * trade.size
                
                pm.realized_pnl += pnl
                trade.pnl = pnl
                trade.pnl_pct = float(pnl / (pm.position.entry_price * trade.size) * 100)
                
                logger.info(f"💰 Trade P&L: {symbol} ${pnl:.2f} ({trade.pnl_pct:.2f}%)")
                
                # Update portfolio manager statistics
                self.portfolio_manager.update_trade_statistics(pnl)
                
        except Exception as e:
            logger.error(f"❌ Error updating position manager: {e}")

    async def _get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current market price for symbol"""
        try:
            orderbook = await self.client.get_orderbook(symbol, depth=1)
            
            best_bid = orderbook.get_best_bid()
            best_ask = orderbook.get_best_ask()
            
            if best_bid and best_ask:
                return (best_bid.price + best_ask.price) / 2
            elif best_bid:
                return best_bid.price
            elif best_ask:
                return best_ask.price
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting current price for {symbol}: {e}")
            return None

    async def close_position(
        self, 
        symbol: str, 
        reason: str = "Manual close",
        percentage: float = 100.0
    ) -> bool:
        """
        Close a position (partially or fully)
        
        Args:
            symbol: Symbol to close
            reason: Reason for closing
            percentage: Percentage of position to close (100.0 = full close)
            
        Returns:
            True if successful
        """
        try:
            # Get current position
            positions = await self.portfolio_manager.get_positions()
            position = next((p for p in positions if p.symbol == symbol), None)
            
            if not position:
                logger.warning(f"⚠️ No position found for {symbol}")
                return False
            
            # Calculate close size
            close_size = position.size * Decimal(percentage / 100)
            
            # Determine close side
            close_side = 'sell' if position.side == 'long' else 'buy'
            
            # Submit close order
            order_id = await self._submit_order(
                symbol=symbol,
                side=close_side,
                size=close_size,
                order_type=OrderType.MARKET,
                reduce_only=True,
                strategy_name=f"Manual_Close_{reason}"
            )
            
            if order_id:
                logger.info(f"✅ Position close order submitted: {symbol} - {percentage}%")
                return True
            else:
                logger.error(f"❌ Failed to submit close order for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error closing position {symbol}: {e}")
            return False

    async def close_all_positions(self, reason: str = "Close all"):
        """Close all open positions"""
        try:
            positions = await self.portfolio_manager.get_positions()
            
            if not positions:
                logger.info("No positions to close")
                return
            
            logger.warning(f"🚨 Closing all {len(positions)} positions: {reason}")
            
            # Create close tasks
            close_tasks = [
                self.close_position(pos.symbol, reason)
                for pos in positions
            ]
            
            # Execute all closes concurrently
            results = await asyncio.gather(*close_tasks, return_exceptions=True)
            
            successful_closes = sum(1 for result in results if result is True)
            logger.info(f"📊 Submitted {successful_closes}/{len(positions)} close orders")
            
        except Exception as e:
            logger.error(f"❌ Error closing all positions: {e}")

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary"""
        # Calculate fill rate
        fill_rate = (self.orders_filled / self.orders_submitted * 100) if self.orders_submitted > 0 else 0.0
        
        # Active position count
        active_positions = sum(1 for pm in self.position_managers.values() if pm.is_active)
        
        # Calculate total P&L
        total_realized_pnl = sum(pm.realized_pnl for pm in self.position_managers.values())
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'orders': {
                'submitted': self.orders_submitted,
                'filled': self.orders_filled,
                'cancelled': self.orders_cancelled,
                'active': len(self.active_orders),
                'fill_rate_pct': fill_rate
            },
            'positions': {
                'active': active_positions,
                'total_managed': len(self.position_managers),
                'symbols': [pm.symbol for pm in self.position_managers.values() if pm.is_active]
            },
            'trading': {
                'total_commission': float(self.total_commission),
                'total_realized_pnl': float(total_realized_pnl),
                'total_trades': len(self.trade_history)
            },
            'settings': {
                'max_slippage_pct': self.max_slippage_pct,
                'order_timeout_seconds': self.order_timeout_seconds,
                'bracket_orders_enabled': self.enable_bracket_orders
            }
        }

    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get list of active orders"""
        return [
            {
                'order_id': order.order_id,
                'symbol': order.symbol,
                'side': order.side,
                'size': float(order.size),
                'order_type': order.order_type.value,
                'status': order.status.value,
                'price': float(order.price) if order.price else None,
                'strategy': order.strategy_name,
                'created_at': order.created_at.isoformat(),
                'time_in_force': order.time_in_force
            }
            for order in self.active_orders.values()
        ]

    def get_position_details(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get detailed position information"""
        managers = [self.position_managers[symbol]] if symbol and symbol in self.position_managers else self.position_managers.values()
        
        details = []
        for pm in managers:
            if pm.is_active and pm.position:
                details.append({
                    'symbol': pm.symbol,
                    'side': pm.position.side,
                    'size': float(pm.position.size),
                    'entry_price': float(pm.position.entry_price),
                    'mark_price': float(pm.position.mark_price),
                    'unrealized_pnl': float(pm.position.unrealized_pnl),
                    'realized_pnl': float(pm.realized_pnl),
                    'max_favorable': float(pm.max_favorable),
                    'max_adverse': float(pm.max_adverse),
                    'entry_time': pm.entry_time.isoformat() if pm.entry_time else None,
                    'entry_orders': len(pm.entry_orders),
                    'exit_orders': len(pm.exit_orders)
                })
        
        return details

    async def emergency_stop(self, reason: str):
        """Emergency stop - cancel all orders and close all positions"""
        logger.critical(f"🚨 EMERGENCY EXECUTION STOP: {reason}")
        
        try:
            # Cancel all orders first
            await self._cancel_all_orders(f"Emergency stop: {reason}")
            
            # Close all positions
            await self.close_all_positions(f"Emergency stop: {reason}")
            
            logger.critical("🚨 Emergency stop completed")
            
        except Exception as e:
            logger.critical(f"🚨 CRITICAL: Emergency stop failed: {e}")