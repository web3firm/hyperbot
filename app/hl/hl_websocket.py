"""
Hyperliquid WebSocket Manager V2
Real-time market data + account updates using official SDK WebSocket
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from decimal import Decimal
from collections import deque
import json

logger = logging.getLogger(__name__)


class HLWebSocket:
    """
    WebSocket manager for HyperLiquid using official SDK
    - Market data: orderbook, trades, candles
    - Account data: positions, fills, orders (eliminates polling!)
    """
    
    def __init__(self, symbols: List[str] = None, account_address: Optional[str] = None):
        """
        Initialize websocket manager
        
        Args:
            symbols: List of symbols to track (e.g., ['BTC'], ['ETH'], ['SOL'])
            account_address: User address for account updates (optional)
        """
        self.symbols = symbols if symbols else ['SOL']
        self.account_address = account_address
        self.running = False
        
        # Market data storage
        self.orderbooks: Dict[str, Dict] = {}
        self.recent_trades: Dict[str, deque] = {}
        self.candles: Dict[str, Dict] = {}
        self._max_candles = 100  # PHASE 4: Memory optimization
        self._max_trades = 100   # PHASE 4: Memory optimization
        self.prices: Dict[str, Decimal] = {}
        
        # Account data storage (replaces polling!)
        self.positions: List[Dict] = []
        self.account_value: Decimal = Decimal('0')
        self.margin_used: Decimal = Decimal('0')
        self.open_orders: List[Dict] = []
        self.recent_fills: deque = deque(maxlen=100)
        
        # Callbacks
        self.on_orderbook_callbacks: List[Callable] = []
        self.on_trade_callbacks: List[Callable] = []
        self.on_candle_callbacks: List[Callable] = []
        self.on_position_callbacks: List[Callable] = []  # NEW
        self.on_fill_callbacks: List[Callable] = []      # NEW
        self.on_order_update_callbacks: List[Callable] = []  # PHASE 4: Real-time order updates
        
        # Initialize storage for symbols
        for symbol in self.symbols:
            self.recent_trades[symbol] = deque(maxlen=self._max_trades)
            self.candles[symbol] = {}
            self.orderbooks[symbol] = {'bids': [], 'asks': []}
        
        logger.info(f"📡 HyperLiquid WebSocket V2 initialized for {self.symbols}")
        if account_address:
            logger.info(f"📊 Account updates enabled for {account_address[:10]}...")
            logger.info(f"🚀 PHASE 4: Real-time order updates enabled")
    
    async def start(self, info_client=None):
        """
        Start websocket connection with SDK subscriptions
        
        Args:
            info_client: hyperliquid.info.Info instance for WebSocket subscriptions
        """
        self.running = True
        self.info_client = info_client
        logger.info("🚀 WebSocket V2 started")
        
        # Subscribe to user events if account provided
        if self.account_address and info_client:
            try:
                # Subscribe to user state updates (positions, balance, fills)
                info_client.subscribe(
                    {"type": "userEvents", "user": self.account_address},
                    self._handle_user_event
                )
                
                # PHASE 4: Subscribe to order updates (fills, cancels, triggers)
                info_client.subscribe(
                    {"type": "orderUpdates", "user": self.account_address},
                    self._handle_order_update
                )
                
                logger.info(f"✅ Subscribed to account + order updates for {self.account_address[:10]}...")
            except Exception as e:
                logger.warning(f"⚠️ Could not subscribe to user events: {e}")
                logger.info("📊 Falling back to polling for account data")
        
        # Subscribe to market data for each symbol
        for symbol in self.symbols:
            try:
                if info_client:
                    # Subscribe to trades
                    info_client.subscribe(
                        {"type": "trades", "coin": symbol},
                        lambda data, s=symbol: self._handle_trade(s, data)
                    )
                    
                    # Subscribe to L2 book updates
                    info_client.subscribe(
                        {"type": "l2Book", "coin": symbol},
                        lambda data, s=symbol: self._handle_orderbook(s, data)
                    )
                    
                    # Subscribe to 1-minute candles (Phase 3 optimization)
                    info_client.subscribe(
                        {"type": "candle", "coin": symbol, "interval": "1m"},
                        lambda data, s=symbol: self._handle_candle(s, data)
                    )
                    
                    logger.info(f"✅ Subscribed to {symbol} market data + candles")
            except Exception as e:
                logger.warning(f"⚠️ Could not subscribe to {symbol}: {e}")
    
    def _handle_user_event(self, event: Dict[str, Any]):
        """Handle user event updates (positions, fills, orders)"""
        try:
            event_type = event.get('type')
            
            if event_type == 'fill':
                # New fill received
                self.recent_fills.append(event)
                logger.info(f"📥 Fill: {event.get('coin')} {event.get('side')} {event.get('sz')} @ {event.get('px')}")
                
                # Notify callbacks
                for callback in self.on_fill_callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Fill callback error: {e}")
            
            elif event_type == 'position':
                # Position update
                self._update_positions(event)
                
                # Notify callbacks
                for callback in self.on_position_callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Position callback error: {e}")
            
            elif event_type == 'liquidation':
                logger.error(f"🚨 LIQUIDATION: {event}")
            
        except Exception as e:
            logger.error(f"Error handling user event: {e}")
    
    def _handle_order_update(self, update: Dict[str, Any]):
        """
        Handle real-time order updates (PHASE 4)
        
        Triggers on:
        - Order filled (partial or full)
        - Order cancelled
        - Stop loss/take profit triggered
        - Order rejected
        
        Provides instant notifications vs waiting for next loop iteration
        """
        try:
            status = update.get('status')
            order = update.get('order', {})
            
            coin = order.get('coin', 'UNKNOWN')
            side = order.get('side', 'unknown')
            size = order.get('sz', 0)
            price = order.get('limitPx') or order.get('triggerPx', 0)
            
            # Log different order events
            if status == 'filled':
                logger.info(f"✅ ORDER FILLED: {coin} {side} {size} @ {price}")
            elif status == 'canceled':
                logger.info(f"🚫 ORDER CANCELLED: {coin} {side} {size} @ {price}")
            elif status == 'triggered':
                logger.info(f"⚡ STOP TRIGGERED: {coin} {side} {size} @ {price}")
            elif status == 'rejected':
                logger.error(f"❌ ORDER REJECTED: {coin} {side} {size} @ {price}")
            else:
                logger.debug(f"🔄 Order update: {status} - {coin} {side}")
            
            # Notify callbacks for immediate action (e.g., Telegram alerts)
            for callback in self.on_order_update_callbacks:
                try:
                    callback(update)
                except Exception as e:
                    logger.error(f"Order update callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling order update: {e}")
    
    def _update_positions(self, event: Dict[str, Any]):
        """Update internal positions cache from WebSocket data"""
        # This replaces the need to poll user_state()
        positions_data = event.get('positions', [])
        self.positions = []
        
        for pos in positions_data:
            if float(pos.get('szi', 0)) != 0:
                self.positions.append({
                    'symbol': pos.get('coin'),
                    'size': float(pos.get('szi', 0)),
                    'side': 'long' if float(pos.get('szi', 0)) > 0 else 'short',
                    'entry_price': float(pos.get('entryPx', 0)),
                    'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                    'leverage': float(pos.get('leverage', {}).get('value', 1) if isinstance(pos.get('leverage'), dict) else pos.get('leverage', 1))
                })
        
        # Update account value
        if 'marginSummary' in event:
            summary = event['marginSummary']
            self.account_value = Decimal(str(summary.get('accountValue', '0')))
            self.margin_used = Decimal(str(summary.get('totalMarginUsed', '0')))
    
    def _handle_trade(self, symbol: str, trade: Dict[str, Any]):
        """Handle trade update"""
        self.recent_trades[symbol].append(trade)
        
        # Update price
        if 'px' in trade:
            self.prices[symbol] = Decimal(str(trade['px']))
        
        # Notify callbacks
        for callback in self.on_trade_callbacks:
            try:
                callback(symbol, trade)
            except Exception as e:
                logger.error(f"Trade callback error: {e}")
    
    def _handle_orderbook(self, symbol: str, book: Dict[str, Any]):
        """Handle orderbook update"""
        self.orderbooks[symbol] = {
            'bids': book.get('levels', [[]])[0],
            'asks': book.get('levels', [[]])[1] if len(book.get('levels', [])) > 1 else [],
            'mid': (float(book.get('levels', [[0]])[0][0][0]) + float(book.get('levels', [[0, 0]])[1][0][0])) / 2 if book.get('levels') else 0
        }
        
        # Update price from mid
        if self.orderbooks[symbol]['mid']:
            self.prices[symbol] = Decimal(str(self.orderbooks[symbol]['mid']))
        
        # Notify callbacks
        for callback in self.on_orderbook_callbacks:
            try:
                callback(symbol, book)
            except Exception as e:
                logger.error(f"Orderbook callback error: {e}")
    
    def _handle_candle(self, symbol: str, candle: Dict[str, Any]):
        """
        Handle real-time candle update (Phase 3 optimization)
        Replaces polling get_candles() every 10 minutes
        """
        try:
            # Store latest candle
            timestamp = candle.get('t', 0)
            self.candles[symbol][timestamp] = {
                'time': timestamp,
                'open': float(candle.get('o', 0)),
                'high': float(candle.get('h', 0)),
                'low': float(candle.get('l', 0)),
                'close': float(candle.get('c', 0)),
                'volume': float(candle.get('v', 0))
            }
            # PHASE 4: Limit candle history to last 100
            if len(self.candles[symbol]) > self._max_candles:
                # Remove oldest candle(s)
                for old_ts in sorted(self.candles[symbol])[:-self._max_candles]:
                    del self.candles[symbol][old_ts]
            
            logger.debug(f"📊 Candle update: {symbol} close=${candle.get('c')}")
            
            # Notify callbacks (for indicator recalculation)
            for callback in self.on_candle_callbacks:
                try:
                    callback(symbol, candle)
                except Exception as e:
                    logger.error(f"Candle callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling candle: {e}")
    
    def get_account_state(self) -> Dict[str, Any]:
        """
        Get current account state from WebSocket cache
        
        Replaces polling client.get_account_state()!
        Returns instantly from cache instead of API call.
        """
        return {
            'account_value': float(self.account_value),
            'margin_used': float(self.margin_used),
            'positions': self.positions,
            'open_orders': self.open_orders
        }
    
    async def stop(self):
        """Stop websocket connection"""
        self.running = False
        logger.info("🛑 WebSocket stopped")
    
    async def _poll_market_data(self):
        """Poll market data as fallback (HyperLiquid SDK doesn't expose WS directly)"""
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        while self.running:
            try:
                # Get latest prices
                all_mids = info.all_mids()
                
                for symbol in self.symbols:
                    if symbol in all_mids:
                        price = Decimal(str(all_mids[symbol]))
                        self.prices[symbol] = price
                        
                        # Update orderbook mid price
                        self.orderbooks[symbol]['mid'] = float(price)
                
                # Get L2 orderbook snapshot periodically
                for symbol in self.symbols:
                    try:
                        l2_data = info.l2_snapshot(symbol)
                        if l2_data:
                            self.orderbooks[symbol] = {
                                'bids': [[float(p[0]['px']), float(p[0]['sz'])] for p in l2_data.get('levels', [[]])[0][:10]],
                                'asks': [[float(p[0]['px']), float(p[0]['sz'])] for p in l2_data.get('levels', [[]])[1][:10]],
                                'mid': float(self.prices.get(symbol, 0))
                            }
                    except Exception as e:
                        logger.debug(f"Error getting L2 for {symbol}: {e}")
                
                await asyncio.sleep(0.5)  # Poll every 500ms
                
            except Exception as e:
                logger.error(f"Error polling market data: {e}")
                await asyncio.sleep(1)
    
    def get_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest price for symbol"""
        return self.prices.get(symbol)
    
    def get_orderbook(self, symbol: str) -> Dict[str, Any]:
        """Get orderbook for symbol"""
        return self.orderbooks.get(symbol, {'bids': [], 'asks': [], 'mid': 0})
    
    def get_recent_trades(self, symbol: str, count: int = 10) -> List[Dict]:
        """Get recent trades for symbol"""
        trades = list(self.recent_trades.get(symbol, []))
        return trades[-count:]
    
    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete market data for symbol
        
        Returns:
            Dict with price, orderbook, trades
        """
        return {
            'symbol': symbol,
            'price': float(self.prices.get(symbol, 0)),
            'orderbook': self.get_orderbook(symbol),
            'recent_trades': self.get_recent_trades(symbol, 10)
        }
    
    def add_orderbook_callback(self, callback: Callable):
        """Add callback for orderbook updates"""
        self.on_orderbook_callbacks.append(callback)
    
    def add_trade_callback(self, callback: Callable):
        """Add callback for trade updates"""
        self.on_trade_callbacks.append(callback)
    
    def add_candle_callback(self, callback: Callable):
        """Add callback for candle updates"""
        self.on_candle_callbacks.append(callback)
