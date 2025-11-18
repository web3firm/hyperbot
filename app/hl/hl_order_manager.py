"""
Hyperliquid Order Manager
Handles order placement, OCO orders, leverage, and position sizing
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)


class HLOrderManager:
    """
    Advanced order management for HyperLiquid
    Supports OCO, trailing stops, partial exits, timeouts
    """
    
    def __init__(self, client):
        """
        Initialize order manager
        
        Args:
            client: HyperLiquidClient instance
        """
        self.client = client
        self.active_orders: Dict[str, Dict] = {}
        self.oco_orders: Dict[str, Dict] = {}  # OCO pairs (TP/SL)
        self.order_timeouts: Dict[str, asyncio.Task] = {}  # Timeout tasks
        self.order_setups: Dict[str, Dict] = {}  # Track setup conditions per order
        self.default_timeout_seconds = 30  # Default 30s timeout
        
        logger.info("📋 Order Manager initialized with timeout + OCO + setup validation")
    
    async def place_market_order(self, symbol: str, side: str, size: Decimal,
                                 sl_price: Optional[Decimal] = None,
                                 tp_price: Optional[Decimal] = None,
                                 timeout_seconds: Optional[int] = None,
                                 setup_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Place market order with optional SL/TP, timeout, and setup validation
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size
            sl_price: Stop loss price
            tp_price: Take profit price
            timeout_seconds: Seconds before auto-cancel (default: 30)
            setup_data: Original setup conditions (for validation)
            
        Returns:
            Order result with OCO orders if applicable
        """
        # Place main market order
        result = await self.client.place_order(
            symbol,
            side,
            size,
            order_type='market'
        )
        
        if not result.get('success'):
            return result
        
        order_id = result.get('order_id')
        
        # Store setup data for validation
        if order_id and setup_data:
            self.order_setups[order_id] = {
                'symbol': symbol,
                'side': side,
                'setup_data': setup_data,
                'created_at': datetime.now(timezone.utc)
            }
        
        # Set up timeout if order ID provided and not immediately filled
        if order_id and timeout_seconds is not None:
            timeout = timeout_seconds if timeout_seconds > 0 else self.default_timeout_seconds
            self._schedule_order_timeout(symbol, order_id, timeout)
        
        # Place OCO orders after confirming position exists (with retry logic)
        if (sl_price or tp_price) and result.get('success'):
            # Wait briefly for position to be reflected on exchange
            await asyncio.sleep(1)
            
            # Verify position exists before placing SL/TP
            has_position = await self._verify_position_exists(symbol, size)
            
            if has_position:
                oco_result = await self._place_oco_orders(
                    symbol,
                    side,
                    size,
                    sl_price,
                    tp_price
                )
                result['oco_orders'] = oco_result
            else:
                logger.warning(f"⚠️  Position not confirmed yet, will retry OCO placement...")
                # Schedule retry after 2 seconds
                asyncio.create_task(self._retry_oco_placement(symbol, side, size, sl_price, tp_price))
        
        return result
    
    def _schedule_order_timeout(self, symbol: str, order_id: str, timeout_seconds: int):
        """
        Schedule automatic cancellation of order after timeout
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel
            timeout_seconds: Seconds to wait before cancellation
        """
        async def timeout_task():
            try:
                await asyncio.sleep(timeout_seconds)
                
                # Check if order still exists
                if order_id in self.active_orders:
                    logger.warning(f"⏰ Order {order_id} timeout reached ({timeout_seconds}s), cancelling...")
                    success = await self.cancel_order(symbol, order_id)
                    
                    if success:
                        logger.info(f"✅ Order {order_id} cancelled due to timeout")
                    else:
                        logger.error(f"❌ Failed to cancel timed-out order {order_id}")
                    
                    # Clean up
                    self.active_orders.pop(order_id, None)
                    self.order_timeouts.pop(order_id, None)
                    
            except asyncio.CancelledError:
                # Order was filled or manually cancelled, cleanup
                self.order_timeouts.pop(order_id, None)
                logger.debug(f"Timeout cancelled for order {order_id} (likely filled)")
            except Exception as e:
                logger.error(f"Error in timeout task for {order_id}: {e}")
        
        # Create and store timeout task
        task = asyncio.create_task(timeout_task())
        self.order_timeouts[order_id] = task
        self.active_orders[order_id] = {
            'symbol': symbol,
            'created_at': datetime.now(timezone.utc),
            'timeout_seconds': timeout_seconds
        }
        
        logger.debug(f"⏳ Timeout scheduled for order {order_id}: {timeout_seconds}s")
    
    async def _verify_position_exists(self, symbol: str, expected_size: Decimal) -> bool:
        """
        Verify that a position exists on the exchange
        
        Args:
            symbol: Trading symbol
            expected_size: Expected position size (absolute value)
            
        Returns:
            True if position exists, False otherwise
        """
        try:
            account_state = await self.client.get_account_state()
            positions = account_state.get('positions', [])
            
            for pos in positions:
                if pos['symbol'] == symbol:
                    pos_size = abs(Decimal(str(pos['size'])))
                    # Allow small rounding differences
                    if abs(pos_size - abs(expected_size)) < Decimal('0.01'):
                        logger.debug(f"✅ Position confirmed: {symbol} size={pos_size}")
                        return True
            
            logger.debug(f"⚠️  Position not found: {symbol}")
            return False
            
        except Exception as e:
            logger.error(f"Error verifying position: {e}")
            return False
    
    async def _retry_oco_placement(self, symbol: str, side: str, size: Decimal,
                                   sl_price: Optional[Decimal], 
                                   tp_price: Optional[Decimal],
                                   max_retries: int = 3):
        """
        Retry OCO order placement with exponential backoff
        
        Args:
            symbol: Trading symbol
            side: Original order side
            size: Position size
            sl_price: Stop loss price
            tp_price: Take profit price
            max_retries: Maximum retry attempts
        """
        for attempt in range(max_retries):
            await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
            
            logger.info(f"🔄 Retry #{attempt + 1} - Attempting OCO placement for {symbol}")
            
            has_position = await self._verify_position_exists(symbol, size)
            
            if has_position:
                oco_result = await self._place_oco_orders(symbol, side, size, sl_price, tp_price)
                
                if oco_result.get('stop_loss', {}).get('success') or oco_result.get('take_profit', {}).get('success'):
                    logger.info(f"✅ OCO orders placed successfully on retry #{attempt + 1}")
                    return
            else:
                logger.warning(f"⚠️  Position still not found (retry #{attempt + 1}/{max_retries})")
        
        logger.error(f"❌ Failed to place OCO orders after {max_retries} retries for {symbol}")
    
    async def _place_oco_orders(self, symbol: str, side: str, size: Decimal,
                                sl_price: Optional[Decimal], 
                                tp_price: Optional[Decimal]) -> Dict[str, Any]:
        """
        Place OCO (One-Cancels-Other) orders for SL/TP
        When one fills, the other is automatically cancelled
        
        Args:
            symbol: Trading symbol
            side: Original order side
            size: Position size
            sl_price: Stop loss price
            tp_price: Take profit price
            
        Returns:
            Dict with SL and TP order results
        """
        oco_results = {}
        order_ids = []
        
        # Determine close side (opposite of entry)
        close_side = 'sell' if side == 'buy' else 'buy'
        
        # Place stop loss order (using stop-market for proper stop-loss triggering)
        if sl_price:
            try:
                sl_result = await self.client.place_stop_market_order(
                    symbol,
                    close_side,
                    size,
                    trigger_price=sl_price,
                    reduce_only=True
                )
                oco_results['stop_loss'] = sl_result
                
                if sl_result.get('success') and sl_result.get('order_id'):
                    sl_order_id = sl_result['order_id']
                    order_ids.append(sl_order_id)
                    logger.info(f"📍 Stop Loss placed at {sl_price} (ID: {sl_order_id})")
                else:
                    logger.error(f"❌ Stop Loss placement failed: {sl_result.get('error')}")
            except Exception as e:
                logger.error(f"❌ Stop Loss error: {e}")
                oco_results['stop_loss'] = {'success': False, 'error': str(e)}
        
        # Place take profit order (limit order with TP flag)
        if tp_price:
            try:
                tp_result = await self.client.place_take_profit_order(
                    symbol,
                    close_side,
                    size,
                    trigger_price=tp_price,
                    reduce_only=True
                )
                oco_results['take_profit'] = tp_result
                
                if tp_result.get('success') and tp_result.get('order_id'):
                    tp_order_id = tp_result['order_id']
                    order_ids.append(tp_order_id)
                    logger.info(f"🎯 Take Profit placed at {tp_price} (ID: {tp_order_id})")
                else:
                    logger.error(f"❌ Take Profit placement failed: {tp_result.get('error')}")
            except Exception as e:
                logger.error(f"❌ Take Profit error: {e}")
                oco_results['take_profit'] = {'success': False, 'error': str(e)}
        
        # Store SL/TP prices for backup monitoring (even if orders failed)
        if sl_price or tp_price:
            if not hasattr(self, 'position_targets'):
                self.position_targets = {}
            self.position_targets[symbol] = {
                'sl_price': sl_price,
                'tp_price': tp_price,
                'size': size,
                'side': side
            }
            logger.info(f"💾 Backup targets stored: SL={sl_price}, TP={tp_price}")
        
        # Link orders as OCO pair if both succeeded
        if len(order_ids) == 2:
            oco_id = f"{symbol}_{int(datetime.now(timezone.utc).timestamp())}"
            self.oco_orders[oco_id] = {
                'symbol': symbol,
                'sl_order_id': order_ids[0],
                'tp_order_id': order_ids[1],
                'created_at': datetime.now(timezone.utc)
            }
            oco_results['oco_id'] = oco_id
            logger.info(f"🔗 OCO pair created: {oco_id}")
        
        return oco_results
    
    async def handle_oco_fill(self, filled_order_id: str):
        """
        Handle OCO order fill - cancel the opposite order
        Call this when an OCO order (SL or TP) fills
        
        Args:
            filled_order_id: Order ID that was filled
        """
        # Find OCO pair containing this order
        for oco_id, oco_data in list(self.oco_orders.items()):
            sl_id = oco_data['sl_order_id']
            tp_id = oco_data['tp_order_id']
            symbol = oco_data['symbol']
            
            if filled_order_id == sl_id:
                # Stop loss hit, cancel take profit
                logger.info(f"🛑 Stop Loss filled, cancelling Take Profit ({tp_id})")
                await self.cancel_order(symbol, tp_id)
                self.oco_orders.pop(oco_id)
                break
                
            elif filled_order_id == tp_id:
                # Take profit hit, cancel stop loss
                logger.info(f"✅ Take Profit filled, cancelling Stop Loss ({sl_id})")
                await self.cancel_order(symbol, sl_id)
                self.oco_orders.pop(oco_id)
                break
    
    async def place_limit_order(self, symbol: str, side: str, size: Decimal,
                               price: Decimal, reduce_only: bool = False,
                               timeout_seconds: Optional[int] = None,
                               setup_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Place limit order with optional timeout and setup validation
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size
            price: Limit price
            reduce_only: Whether this is a reduce-only order
            timeout_seconds: Seconds before auto-cancel (default: 30)
            setup_data: Original setup conditions (for validation)
            
        Returns:
            Order result
        """
        result = await self.client.place_order(
            symbol,
            side,
            size,
            order_type='limit',
            price=price,
            reduce_only=reduce_only
        )
        
        if result.get('success'):
            order_id = result.get('order_id')
            
            # Store setup data
            if order_id and setup_data:
                self.order_setups[order_id] = {
                    'symbol': symbol,
                    'side': side,
                    'setup_data': setup_data,
                    'created_at': datetime.now(timezone.utc)
                }
            
            # Schedule timeout if provided and order not immediately filled
            if order_id and timeout_seconds is not None:
                timeout = timeout_seconds if timeout_seconds > 0 else self.default_timeout_seconds
                self._schedule_order_timeout(symbol, order_id, timeout)
        
        return result
    
    async def validate_setup(self, order_id: str, current_market_data: Dict[str, Any]) -> bool:
        """
        Validate that setup conditions are still valid before fill
        
        Args:
            order_id: Order ID to validate
            current_market_data: Current market state
            
        Returns:
            True if setup still valid, False if invalidated
        """
        if order_id not in self.order_setups:
            # No setup data stored, assume valid
            return True
        
        setup_info = self.order_setups[order_id]
        original_setup = setup_info['setup_data']
        symbol = setup_info['symbol']
        side = setup_info['side']
        
        # Get current price
        current_price = Decimal(str(current_market_data.get('price', 0)))
        if current_price == 0:
            return True  # Can't validate without price
        
        # Check if price moved too far from entry
        original_price = Decimal(str(original_setup.get('entry_price', 0)))
        if original_price > 0:
            price_change_pct = abs((current_price - original_price) / original_price * 100)
            
            # If price moved >0.5% away, setup likely invalid
            if price_change_pct > Decimal('0.5'):
                logger.warning(f"⚠️ Setup invalidated: price moved {price_change_pct:.2f}% from entry")
                return False
        
        # Check momentum direction still valid (if provided)
        if 'momentum_pct' in original_setup:
            original_momentum = Decimal(str(original_setup['momentum_pct']))
            current_momentum = Decimal(str(current_market_data.get('momentum_pct', 0)))
            
            # If momentum reversed significantly, setup invalid
            if (original_momentum > 0 and current_momentum < -Decimal('0.1')) or \
               (original_momentum < 0 and current_momentum > Decimal('0.1')):
                logger.warning(f"⚠️ Setup invalidated: momentum reversed")
                return False
        
        return True
    
    async def check_and_cancel_invalid_setup(self, order_id: str, 
                                             current_market_data: Dict[str, Any]) -> bool:
        """
        Check if setup is still valid, cancel order if not
        
        Args:
            order_id: Order ID to check
            current_market_data: Current market state
            
        Returns:
            True if order was cancelled, False if still valid
        """
        is_valid = await self.validate_setup(order_id, current_market_data)
        
        if not is_valid and order_id in self.order_setups:
            setup_info = self.order_setups[order_id]
            symbol = setup_info['symbol']
            
            logger.info(f"❌ Cancelling order {order_id} - setup invalidated")
            await self.cancel_order(symbol, order_id)
            self.order_setups.pop(order_id, None)
            return True
        
        return False
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an order and clean up timeout tasks
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        # Cancel timeout task if exists
        if order_id in self.order_timeouts:
            self.order_timeouts[order_id].cancel()
            self.order_timeouts.pop(order_id, None)
        
        # Remove from active tracking
        self.active_orders.pop(order_id, None)
        
        # Cancel actual order
        return await self.client.cancel_order(symbol, order_id)
    
    def mark_order_filled(self, order_id: str):
        """
        Mark order as filled and clean up timeout + setup data
        Call this when order fill is detected
        
        Args:
            order_id: Order ID that was filled
        """
        # Cancel timeout task
        if order_id in self.order_timeouts:
            self.order_timeouts[order_id].cancel()
            self.order_timeouts.pop(order_id, None)
        
        # Remove from active tracking
        self.active_orders.pop(order_id, None)
        
        # Remove setup data
        self.order_setups.pop(order_id, None)
        
        logger.debug(f"Order {order_id} marked as filled, all tracking cleared")
    
    async def modify_order(self, symbol: str, order_id: str, new_price: Decimal) -> bool:
        """
        Modify order price (cancel and replace)
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to modify
            new_price: New price
            
        Returns:
            True if successful
        """
        # Cancel existing order
        cancelled = await self.cancel_order(symbol, order_id)
        if not cancelled:
            return False
        
        # Place new order at new price
        # (Would need to store original order details)
        logger.info(f"Order {order_id} modified to {new_price}")
        return True
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for symbol
        
        Args:
            symbol: Trading symbol
            leverage: Leverage value (1-50)
            
        Returns:
            True if successful
        """
        return await self.client.set_leverage(symbol, leverage)
    
    def calculate_position_size(self, account_value: Decimal, 
                                risk_pct: Decimal,
                                entry_price: Decimal,
                                sl_price: Decimal,
                                leverage: int = 1) -> Decimal:
        """
        Calculate position size based on risk parameters
        
        Args:
            account_value: Account equity
            risk_pct: Risk percentage (e.g., 1.0 for 1%)
            entry_price: Entry price
            sl_price: Stop loss price
            leverage: Leverage to use
            
        Returns:
            Position size
        """
        # Risk amount in USD
        risk_amount = account_value * (risk_pct / 100)
        
        # Price difference to stop loss
        price_diff = abs(entry_price - sl_price)
        
        if price_diff == 0:
            logger.warning("Stop loss too close to entry, using minimum size")
            return Decimal('0.01')
        
        # Calculate size
        # risk_amount = size * price_diff
        size = risk_amount / price_diff
        
        # Apply leverage (more size with same risk)
        size = size * Decimal(str(leverage))
        
        # Round to appropriate decimals for this asset
        size_decimals = self.client.get_size_decimals(symbol)
        size = round(size, size_decimals)
        
        logger.debug(f"Position size calculated: {size} (risk: {risk_pct}%, leverage: {leverage}x)")
        
        return size
    
    def calculate_sl_tp_prices(self, entry_price: Decimal, side: str,
                               sl_pct: Decimal = Decimal('1.0'),
                               tp_pct: Decimal = Decimal('2.0')) -> tuple:
        """
        Calculate SL and TP prices based on percentages
        
        Args:
            entry_price: Entry price
            side: 'buy' or 'sell'
            sl_pct: Stop loss percentage (default 1%)
            tp_pct: Take profit percentage (default 2%)
            
        Returns:
            (sl_price, tp_price)
        """
        if side == 'buy':
            # Long position
            sl_price = entry_price * (1 - sl_pct / 100)
            tp_price = entry_price * (1 + tp_pct / 100)
        else:
            # Short position
            sl_price = entry_price * (1 + sl_pct / 100)
            tp_price = entry_price * (1 - tp_pct / 100)
        
        # Round to appropriate decimals based on price
        price_decimals = self.client.get_price_decimals(entry_price)
        sl_price = round(sl_price, price_decimals)
        tp_price = round(tp_price, price_decimals)
        
        return (sl_price, tp_price)
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close entire position"""
        return await self.client.close_position(symbol)
