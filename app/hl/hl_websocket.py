"""
Hyperliquid WebSocket Manager
Real-time market data feeds for trading
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
    WebSocket manager for HyperLiquid market data
    Handles real-time orderbook, trades, and candles
    """
    
    def __init__(self, symbols: List[str] = None):
        """
        Initialize websocket manager
        
        Args:
            symbols: List of symbols to track (e.g., ['BTC'], ['ETH'], ['SOL'])
                    If None, defaults to ['SOL']
        """
        self.symbols = symbols if symbols else ['SOL']
        self.running = False
        
        # Data storage
        self.orderbooks: Dict[str, Dict] = {}
        self.recent_trades: Dict[str, deque] = {}
        self.candles: Dict[str, Dict] = {}
        self.prices: Dict[str, Decimal] = {}
        
        # Callbacks
        self.on_orderbook_callbacks: List[Callable] = []
        self.on_trade_callbacks: List[Callable] = []
        self.on_candle_callbacks: List[Callable] = []
        
        # Initialize storage for symbols
        for symbol in self.symbols:
            self.recent_trades[symbol] = deque(maxlen=100)
            self.candles[symbol] = {}
            self.orderbooks[symbol] = {'bids': [], 'asks': []}
        
        logger.info(f"📡 HyperLiquid WebSocket initialized for {self.symbols}")
    
    async def start(self):
        """Start websocket connection"""
        self.running = True
        logger.info("🚀 WebSocket started")
        
        # Note: HyperLiquid SDK handles WebSocket internally
        # We'll use polling as fallback for now
        asyncio.create_task(self._poll_market_data())
    
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
