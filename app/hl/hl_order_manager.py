"""
HyperLiquid Order Manager - Atomic OCO Orders
Implements proper One-Cancels-Other orders with TP/SL grouping.
Bypasses SDK limitation that hardcodes grouping to "na".
"""
import asyncio
import uuid
import time
from typing import Optional, Dict, Any, Callable, List, Literal
from hyperliquid.utils.types import Cloid
from hyperliquid.utils.signing import (
    sign_l1_action, 
    get_timestamp_ms,
    order_request_to_order_wire,
    float_to_wire,
    order_type_to_wire,
)
from hyperliquid.utils.constants import MAINNET_API_URL
from app.hl.hl_client import HyperLiquidClient
from app.utils.trading_logger import TradingLogger

logger = TradingLogger("hl_order_manager")

# Grouping types for HyperLiquid orders
Grouping = Literal["na", "normalTpsl", "positionTpsl"]


class HLOrderManager:
    """Ultra-lean order manager using direct SDK calls."""
    
    def __init__(self, client: HyperLiquidClient, on_fill: Optional[Callable] = None):
        self.client = client
        self.exchange = client.exchange
        self.info = client.info
        self.address = client.address
        self.on_fill = on_fill
        self._loop = asyncio.get_event_loop()
        
        # Position tracking for trailing stops
        self.position_orders: Dict[str, Dict[str, Any]] = {}
    
    def _gen_cloid(self) -> Cloid:
        """Generate unique client order ID (0x + 32 hex chars)."""
        hex_id = f"0x{uuid.uuid4().hex}"
        return Cloid.from_str(hex_id)
    
    def _order_request_to_wire(self, order: Dict, asset: int) -> Dict:
        """Convert order request to wire format for API submission."""
        order_wire = {
            "a": asset,
            "b": order["is_buy"],
            "p": float_to_wire(order["limit_px"]),
            "s": float_to_wire(order["sz"]),
            "r": order.get("reduce_only", False),
            "t": order_type_to_wire(order["order_type"]),
        }
        if "cloid" in order and order["cloid"] is not None:
            order_wire["c"] = order["cloid"].to_raw()
        return order_wire
    
    def _build_order_action(self, order_wires: List[Dict], grouping: Grouping = "na", 
                            builder: Optional[Dict] = None) -> Dict:
        """
        Build order action with custom grouping.
        This bypasses the SDK's hardcoded "na" grouping.
        
        Grouping Types:
        - "na": No grouping (default SDK behavior)
        - "normalTpsl": Parent order with TP/SL children (OCO)
        - "positionTpsl": TP/SL tied to entire position
        """
        action = {
            "type": "order",
            "orders": order_wires,
            "grouping": grouping,
        }
        if builder:
            action["builder"] = builder
        return action
    
    def bulk_orders_with_grouping(self, order_requests: List[Dict], 
                                   grouping: Grouping = "na",
                                   max_retries: int = 3) -> Dict:
        """
        Submit multiple orders with custom grouping for atomic execution.
        
        For OCO orders (entry + TP + SL), use grouping="normalTpsl":
        - Order 0: Entry order (market/limit)
        - Order 1: Take Profit trigger
        - Order 2: Stop Loss trigger
        
        When entry fills, TP/SL are automatically placed.
        When either TP or SL triggers, the other is cancelled.
        
        Args:
            order_requests: List of order dicts with coin, is_buy, sz, limit_px, order_type
            grouping: "na" (independent), "normalTpsl" (OCO), "positionTpsl" (position-based)
            max_retries: Retry count for transient errors (502, etc.)
            
        Returns:
            API response with order statuses
        """
        for attempt in range(max_retries):
            try:
                # Convert orders to wire format
                order_wires = []
                for order in order_requests:
                    coin = order["coin"]
                    asset = self.info.name_to_asset(coin)
                    wire = self._order_request_to_wire(order, asset)
                    order_wires.append(wire)
                
                # Build action with custom grouping
                timestamp = get_timestamp_ms()
                action = self._build_order_action(order_wires, grouping)
                
                # Sign and submit
                is_mainnet = self.exchange.base_url == MAINNET_API_URL
                signature = sign_l1_action(
                    self.exchange.wallet,
                    action,
                    self.exchange.vault_address,
                    timestamp,
                    self.exchange.expires_after,
                    is_mainnet,
                )
                
                result = self.exchange._post_action(action, signature, timestamp)
                
                logger.info(f"bulk_orders_with_grouping({grouping}): {len(order_requests)} orders -> {result}")
                return result
                
            except Exception as e:
                error_msg = str(e)
                if "502" in error_msg or "Bad Gateway" in error_msg:
                    wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                    logger.warning(f"502 error, retry {attempt+1}/{max_retries} in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"bulk_orders_with_grouping failed: {e}")
                    return {"status": "error", "error": str(e)}
        
        return {"status": "error", "error": "Max retries exceeded (502 errors)"}
    
    def atomic_market_entry_with_tpsl(self, symbol: str, is_buy: bool, size: float,
                                       tp_price: Optional[float] = None,
                                       sl_price: Optional[float] = None,
                                       slippage: float = 0.01) -> Dict:
        """
        ATOMIC OCO Entry: Market entry + TP + SL in single request.
        
        All three orders are submitted together with normalTpsl grouping:
        - When entry fills, TP/SL become active
        - When TP triggers, SL is cancelled (and vice versa)
        
        This is the proper OCO implementation for HyperLiquid.
        """
        sz_decimals = self.client.get_sz_decimals(symbol)
        rounded_size = round(size, sz_decimals)
        
        # Get mid price
        mid = float(self.info.all_mids().get(symbol, 0))
        if mid <= 0:
            logger.error(f"Invalid mid price for {symbol}: {mid}")
            return {'status': 'error', 'message': 'Invalid mid price'}
        
        # Calculate entry limit price with slippage
        entry_px = round(mid * (1 + slippage) if is_buy else mid * (1 - slippage), 2)
        
        orders = []
        
        # Order 0: Market entry (IOC with aggressive price = market-like)
        entry_order = {
            "coin": symbol,
            "is_buy": is_buy,
            "sz": rounded_size,
            "limit_px": entry_px,
            "order_type": {"limit": {"tif": "Ioc"}},  # IOC for immediate fill
            "reduce_only": False,
            "cloid": self._gen_cloid(),
        }
        orders.append(entry_order)
        
        # Order 1: Take Profit (reduce-only, opposite side)
        if tp_price:
            tp_order = {
                "coin": symbol,
                "is_buy": not is_buy,  # Opposite side to close
                "sz": rounded_size,
                "limit_px": round(tp_price, 6),
                "order_type": {"trigger": {
                    "triggerPx": round(tp_price, 6),
                    "isMarket": True,
                    "tpsl": "tp"
                }},
                "reduce_only": True,
                "cloid": self._gen_cloid(),
            }
            orders.append(tp_order)
        
        # Order 2: Stop Loss (reduce-only, opposite side)
        if sl_price:
            sl_order = {
                "coin": symbol,
                "is_buy": not is_buy,  # Opposite side to close
                "sz": rounded_size,
                "limit_px": round(sl_price, 6),
                "order_type": {"trigger": {
                    "triggerPx": round(sl_price, 6),
                    "isMarket": True,
                    "tpsl": "sl"
                }},
                "reduce_only": True,
                "cloid": self._gen_cloid(),
            }
            orders.append(sl_order)
        
        logger.info(f"🎯 ATOMIC OCO: {symbol} {'LONG' if is_buy else 'SHORT'} {rounded_size}")
        logger.info(f"   Entry: ${entry_px} | TP: ${tp_price} | SL: ${sl_price}")
        
        # Submit with normalTpsl grouping for OCO behavior
        grouping = "normalTpsl" if (tp_price or sl_price) else "na"
        result = self.bulk_orders_with_grouping(orders, grouping=grouping)
        
        # Track position
        if result.get('status') == 'ok' or 'response' in result:
            self.position_orders[symbol] = {
                'size': rounded_size,
                'is_buy': is_buy,
                'entry_price': entry_px,
                'tp_price': tp_price,
                'sl_price': sl_price,
            }
        
        return result
    
    # ==================== MARKET ORDERS ====================
    def market_open(self, symbol: str, is_buy: bool, size: float, 
                    slippage: float = 0.01) -> Dict:
        """
        Open position with SDK market_open().
        Explicitly calculates limit price to avoid SDK caching issues.
        """
        sz_decimals = self.client.get_sz_decimals(symbol)
        rounded_size = round(size, sz_decimals)
        
        # Get current mid price and calculate limit with slippage
        mid = float(self.info.all_mids().get(symbol, 0))
        if mid <= 0:
            logger.error(f"Invalid mid price for {symbol}: {mid}")
            return {'status': 'error', 'message': 'Invalid mid price'}
        
        # Calculate limit price with slippage
        limit_px = round(mid * (1 + slippage) if is_buy else mid * (1 - slippage), 2)
        
        # Use market_open with explicit px
        result = self.exchange.market_open(symbol, is_buy, rounded_size, px=limit_px)
        logger.info(f"market_open {symbol} {'BUY' if is_buy else 'SELL'} {rounded_size} @ ${limit_px}: {result}")
        return result
    
    def market_close(self, symbol: str, slippage: float = 0.01) -> Dict:
        """Close entire position with explicit price calculation."""
        # Get current position size
        user_state = self.info.user_state(self.address)
        positions = user_state.get('assetPositions', [])
        
        position_size = 0.0
        is_long = True
        for p in positions:
            pos = p.get('position', {})
            if pos.get('coin') == symbol:
                position_size = abs(float(pos.get('szi', 0)))
                is_long = float(pos.get('szi', 0)) > 0
                break
        
        if position_size <= 0:
            logger.warning(f"No position to close for {symbol}")
            return {'status': 'ok', 'message': 'No position'}
        
        # Get mid and calculate close price (opposite side)
        mid = float(self.info.all_mids().get(symbol, 0))
        # For long position, we sell (so price below mid is ok)
        # For short position, we buy (so price above mid is ok)
        limit_px = round(mid * (0.99 if is_long else 1.01), 2)
        
        # Use order() directly with reduce_only
        sz_decimals = self.client.get_sz_decimals(symbol)
        rounded_size = round(position_size, sz_decimals)
        
        result = self.exchange.order(
            name=symbol,
            is_buy=not is_long,
            sz=rounded_size,
            limit_px=limit_px,
            order_type={"limit": {"tif": "Ioc"}},
            reduce_only=True,
        )
        logger.info(f"market_close {symbol} {rounded_size} @ ${limit_px}: {result}")
        return result
    
    # ==================== TP/SL ORDERS ====================
    def set_tp_sl(self, symbol: str, size: float, is_long: bool,
                  tp_price: Optional[float] = None,
                  sl_price: Optional[float] = None,
                  use_position_grouping: bool = True) -> List[Dict]:
        """
        Set TP/SL trigger orders for an existing position.
        Uses positionTpsl grouping when both TP and SL are provided.
        
        Args:
            symbol: Trading pair
            size: Position size
            is_long: True if long position
            tp_price: Take profit trigger price
            sl_price: Stop loss trigger price
            use_position_grouping: Use positionTpsl grouping (OCO behavior)
        """
        sz_decimals = self.client.get_sz_decimals(symbol)
        rounded_size = round(size, sz_decimals)
        
        # If both TP and SL, use grouped submission
        if tp_price and sl_price and use_position_grouping:
            orders = []
            
            # Take Profit
            tp_order = {
                "coin": symbol,
                "is_buy": not is_long,
                "sz": rounded_size,
                "limit_px": round(tp_price, 6),
                "order_type": {"trigger": {
                    "triggerPx": round(tp_price, 6),
                    "isMarket": True,
                    "tpsl": "tp"
                }},
                "reduce_only": True,
                "cloid": self._gen_cloid(),
            }
            orders.append(tp_order)
            
            # Stop Loss
            sl_order = {
                "coin": symbol,
                "is_buy": not is_long,
                "sz": rounded_size,
                "limit_px": round(sl_price, 6),
                "order_type": {"trigger": {
                    "triggerPx": round(sl_price, 6),
                    "isMarket": True,
                    "tpsl": "sl"
                }},
                "reduce_only": True,
                "cloid": self._gen_cloid(),
            }
            orders.append(sl_order)
            
            # Submit with positionTpsl grouping (TP/SL for existing position)
            result = self.bulk_orders_with_grouping(orders, grouping="positionTpsl")
            logger.info(f"set_tp_sl (grouped) {symbol} TP@{tp_price} SL@{sl_price}: {result}")
            return [{'type': 'tpsl_grouped', 'result': result}]
        
        # Otherwise, submit individually (fallback)
        results = []
        
        # Take Profit (reduce only, opposite side)
        if tp_price:
            tp_result = self.exchange.order(
                name=symbol,
                is_buy=not is_long,  # Opposite side to close
                sz=rounded_size,
                limit_px=round(tp_price, 6),
                order_type={"trigger": {
                    "triggerPx": round(tp_price, 6),
                    "isMarket": True,
                    "tpsl": "tp"
                }},
                reduce_only=True,
                cloid=self._gen_cloid(),
            )
            logger.info(f"set_tp {symbol} @ {tp_price}: {tp_result}")
            results.append({'type': 'tp', 'result': tp_result})
        
        # Stop Loss (reduce only, opposite side)
        if sl_price:
            sl_result = self.exchange.order(
                name=symbol,
                is_buy=not is_long,  # Opposite side to close
                sz=rounded_size,
                limit_px=round(sl_price, 6),
                order_type={"trigger": {
                    "triggerPx": round(sl_price, 6),
                    "isMarket": True,
                    "tpsl": "sl"
                }},
                reduce_only=True,
                cloid=self._gen_cloid(),
            )
            logger.info(f"set_sl {symbol} @ {sl_price}: {sl_result}")
            results.append({'type': 'sl', 'result': sl_result})
        
        return results
    
    def set_position_tpsl(self, symbol: str, 
                          tp_price: Optional[float] = None,
                          sl_price: Optional[float] = None) -> Dict:
        """
        Set TP/SL for current position (auto-detects size and direction).
        
        Convenience method that:
        1. Fetches current position
        2. Determines size and direction
        3. Sets TP/SL with proper grouping
        
        Args:
            symbol: Trading pair
            tp_price: Take profit trigger price  
            sl_price: Stop loss trigger price
            
        Returns:
            TP/SL order results
        """
        # Get current position
        user_state = self.info.user_state(self.address)
        positions = user_state.get('assetPositions', [])
        
        position_size = 0.0
        is_long = True
        entry_price = 0.0
        
        for p in positions:
            pos = p.get('position', {})
            if pos.get('coin') == symbol:
                position_size = abs(float(pos.get('szi', 0)))
                is_long = float(pos.get('szi', 0)) > 0
                entry_price = float(pos.get('entryPx', 0))
                break
        
        if position_size <= 0:
            logger.warning(f"No position to set TP/SL for {symbol}")
            return {'status': 'error', 'message': 'No position found'}
        
        logger.info(f"🎯 Setting TP/SL for {symbol} {'LONG' if is_long else 'SHORT'} {position_size}")
        logger.info(f"   Entry: ${entry_price} | TP: ${tp_price} | SL: ${sl_price}")
        
        # Set TP/SL with proper grouping
        results = self.set_tp_sl(symbol, position_size, is_long, tp_price, sl_price)
        
        # Track position
        self.position_orders[symbol] = {
            'size': position_size,
            'is_buy': is_long,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
        }
        
        return {
            'status': 'ok',
            'position_size': position_size,
            'is_long': is_long,
            'entry_price': entry_price,
            'tp_price': tp_price, 
            'sl_price': sl_price,
            'results': results
        }
    
    def market_open_with_stops(self, symbol: str, is_buy: bool, size: float,
                                tp_price: Optional[float] = None,
                                sl_price: Optional[float] = None,
                                slippage: float = 0.01,
                                use_atomic: bool = True) -> Dict:
        """
        Open position with market order and set TP/SL.
        
        Args:
            symbol: Trading pair
            is_buy: True for long, False for short
            size: Position size
            tp_price: Take profit trigger price
            sl_price: Stop loss trigger price
            slippage: Max slippage for entry (default 1%)
            use_atomic: If True, use atomic OCO (all orders in one request)
                        If False, use two-step (entry first, then TP/SL)
        """
        if use_atomic and (tp_price or sl_price):
            # PREFERRED: Atomic OCO - entry + TP + SL in single request
            return self.atomic_market_entry_with_tpsl(
                symbol, is_buy, size, tp_price, sl_price, slippage
            )
        
        # Fallback: Two-step process (entry first, then TP/SL)
        # Used when no TP/SL specified
        
        # Step 1: Market entry
        entry_result = self.market_open(symbol, is_buy, size, slippage)
        
        # Check if entry succeeded
        entry_ok = entry_result.get('status') == 'ok' or 'response' in entry_result
        if not entry_ok:
            logger.error(f"Entry failed: {entry_result}")
            return entry_result
        
        # Get actual filled size from response
        filled_size = size  # Default to requested
        statuses = entry_result.get('response', {}).get('data', {}).get('statuses', [])
        if statuses and 'filled' in statuses[0]:
            filled_info = statuses[0]['filled']
            filled_size = float(filled_info.get('totalSz', size))
        
        logger.info(f"Entry filled: {filled_size} {symbol}")
        
        # Step 2: Set TP/SL if entry succeeded and we have prices
        tpsl_results = []
        if filled_size > 0 and (tp_price or sl_price):
            tpsl_results = self.set_tp_sl(symbol, filled_size, is_buy, tp_price, sl_price)
        
        # Track position
        self.position_orders[symbol] = {
            'size': filled_size,
            'is_buy': is_buy,
            'tp_price': tp_price,
            'sl_price': sl_price,
        }
        
        return {
            'status': 'ok',
            'entry': entry_result,
            'tpsl': tpsl_results,
            'filled_size': filled_size,
        }
    
    async def place_market_order_with_stops(self, symbol: str, side: str, size, 
                                            sl_price=None, tp_price=None) -> Dict:
        """
        Async wrapper for market_open_with_stops (bot.py compatible).
        Returns dict with 'success' key for bot.py compatibility.
        """
        is_buy = side.lower() == 'buy'
        size_float = float(size)
        sl_float = float(sl_price) if sl_price else None
        tp_float = float(tp_price) if tp_price else None
        
        result = await self._loop.run_in_executor(
            None, 
            lambda: self.market_open_with_stops(symbol, is_buy, size_float, tp_float, sl_float)
        )
        
        # Convert to bot.py expected format
        success = result.get('status') == 'ok'
        return {
            'success': success,
            'result': result,
            'error': result.get('error') if not success else None
        }
    
    # ==================== LIMIT ORDERS ====================
    def limit_order(self, symbol: str, is_buy: bool, size: float, 
                    price: float, reduce_only: bool = False,
                    tif: str = "Gtc") -> Dict:
        """Place limit order using SDK order()."""
        sz_decimals = self.client.get_sz_decimals(symbol)
        rounded_size = round(size, sz_decimals)
        cloid = self._gen_cloid()
        
        result = self.exchange.order(
            name=symbol,
            is_buy=is_buy,
            sz=rounded_size,
            limit_px=round(price, 6),
            order_type={"limit": {"tif": tif}},
            reduce_only=reduce_only,
            cloid=cloid,
        )
        logger.info(f"limit_order {symbol} {'BUY' if is_buy else 'SELL'} {rounded_size}@{price}: {result}")
        return result
    
    # ==================== ORDER MANAGEMENT ====================
    def modify_order(self, oid: int, symbol: str, is_buy: bool, 
                     size: float, price: float) -> Dict:
        """Modify existing order using SDK modify_order()."""
        result = self.exchange.modify_order(oid, symbol, is_buy, size, price)
        logger.info(f"modify_order {oid}: {result}")
        return result
    
    def cancel_order(self, symbol: str, oid: int) -> Dict:
        """Cancel order by OID using SDK cancel()."""
        result = self.exchange.cancel(symbol, oid)
        logger.info(f"cancel {symbol} oid={oid}: {result}")
        return result
    
    def cancel_by_cloid(self, symbol: str, cloid: Cloid) -> Dict:
        """Cancel order by CLOID using SDK cancel_by_cloid()."""
        result = self.exchange.cancel_by_cloid(symbol, cloid)
        logger.info(f"cancel_by_cloid {symbol} cloid={cloid}: {result}")
        return result
    
    def cancel_all(self, symbol: Optional[str] = None) -> Dict:
        """Cancel all open orders, optionally for specific symbol."""
        orders = self.client.get_open_orders(symbol)
        if not orders:
            return {"status": "ok", "cancelled": 0}
        
        cancels = [{"coin": o["coin"], "oid": o["oid"]} for o in orders]
        result = self.exchange.bulk_cancel(cancels)
        logger.info(f"bulk_cancel {len(cancels)} orders: {result}")
        return result
    
    # ==================== DEAD MAN'S SWITCH ====================
    def schedule_cancel(self, seconds: int) -> Dict:
        """
        Dead man's switch - cancel all orders after N seconds.
        Use 0 to disable. Maximum 86400 (24h).
        """
        result = self.exchange.schedule_cancel(seconds)
        logger.info(f"schedule_cancel in {seconds}s: {result}")
        return result
    
    # ==================== LEVERAGE ====================
    def set_leverage(self, symbol: str, leverage: int, is_cross: bool = True) -> Dict:
        """Set leverage for symbol."""
        result = self.exchange.update_leverage(leverage, symbol, is_cross)
        logger.info(f"set_leverage {symbol} {leverage}x {'cross' if is_cross else 'isolated'}: {result}")
        return result
    
    # ==================== QUERY ====================
    def query_order(self, symbol: str, oid: int) -> Optional[Dict]:
        """Query order status by OID."""
        return self.info.query_order_by_oid(self.address, oid)
    
    def query_order_by_cloid(self, symbol: str, cloid: Cloid) -> Optional[Dict]:
        """Query order status by CLOID."""
        return self.info.query_order_by_cloid(self.address, cloid)
    
    def get_rate_limit(self) -> Dict:
        """Get current rate limit status."""
        return self.info.user_rate_limit(self.address)
    
    # ==================== TRAILING STOP ====================
    def update_trailing_stop(self, symbol: str, current_price: float, 
                             trail_pct: float = 0.15) -> Optional[Dict]:
        """
        Update trailing stop for an existing position.
        
        Trail Logic:
        - LONG: If price > entry, move SL up to (current_price * (1 - trail_pct/100))
        - SHORT: If price < entry, move SL down to (current_price * (1 + trail_pct/100))
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            trail_pct: Trail distance as percentage (default 0.15%)
        
        Returns:
            Updated SL order result or None
        """
        if symbol not in self.position_orders:
            return None
        
        pos = self.position_orders[symbol]
        is_long = pos.get('is_buy', True)
        entry_price = pos.get('entry_price', current_price)
        current_sl = pos.get('sl_price')
        size = pos.get('size', 0)
        
        if size <= 0:
            return None
        
        # Calculate new trailing SL
        if is_long:
            # For longs: trail below current price
            new_sl = current_price * (1 - trail_pct / 100)
            
            # Only update if:
            # 1. Price is above entry (in profit)
            # 2. New SL is higher than current SL (tightening)
            if current_price <= entry_price:
                return None  # Not in profit yet
            if current_sl and new_sl <= current_sl:
                return None  # Would loosen the stop
                
        else:
            # For shorts: trail above current price
            new_sl = current_price * (1 + trail_pct / 100)
            
            # Only update if:
            # 1. Price is below entry (in profit)
            # 2. New SL is lower than current SL (tightening)
            if current_price >= entry_price:
                return None  # Not in profit yet
            if current_sl and new_sl >= current_sl:
                return None  # Would loosen the stop
        
        # Cancel old SL and place new one
        try:
            # Cancel all open orders for this symbol (including old SL)
            self.cancel_all(symbol)
            
            # Place new trailing SL
            sl_result = self.exchange.order(
                name=symbol,
                is_buy=not is_long,
                sz=size,
                limit_px=round(new_sl, 6),
                order_type={"trigger": {
                    "triggerPx": round(new_sl, 6),
                    "isMarket": True,
                    "tpsl": "sl"
                }},
                reduce_only=True,
                cloid=self._gen_cloid(),
            )
            
            # Update tracked SL
            self.position_orders[symbol]['sl_price'] = new_sl
            
            profit_pct = abs(current_price - entry_price) / entry_price * 100
            locked_pct = abs(new_sl - entry_price) / entry_price * 100
            
            logger.info(f"🎯 TRAILING SL: {symbol} {'LONG' if is_long else 'SHORT'}")
            logger.info(f"   Entry: ${entry_price:.4f} | Current: ${current_price:.4f}")
            logger.info(f"   Old SL: ${current_sl:.4f} → New SL: ${new_sl:.4f}")
            logger.info(f"   Profit: {profit_pct:.2f}% | Locked: {locked_pct:.2f}%")
            
            return sl_result
            
        except Exception as e:
            logger.error(f"Failed to update trailing stop: {e}")
            return None
    
    def set_entry_price(self, symbol: str, entry_price: float):
        """Set entry price for trailing stop calculation."""
        if symbol in self.position_orders:
            self.position_orders[symbol]['entry_price'] = entry_price


# Factory function
def create_order_manager(client: HyperLiquidClient, on_fill: Optional[Callable] = None) -> HLOrderManager:
    """Create HLOrderManager instance."""
    return HLOrderManager(client, on_fill)
