"""
HyperLiquid Client - Ultra-Lean SDK Passthrough
Direct SDK methods with minimal wrapper overhead.
Target: Maximum speed, minimum code.
"""
import os
import asyncio
from functools import lru_cache
from typing import Optional, Dict, Any, List
from decimal import Decimal
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from eth_account import Account
from app.utils.trading_logger import TradingLogger

logger = TradingLogger("hl_client")


class HyperLiquidClient:
    """Ultra-lean SDK passthrough - exposes all SDK methods directly."""
    
    def __init__(self, account_address: str, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize HyperLiquid client.
        
        Args:
            account_address: Wallet address
            api_key: API key (same as api_secret for HyperLiquid)
            api_secret: Private key or API secret
            testnet: Use testnet if True
        """
        self.wallet = Account.from_key(api_secret)
        self.address = account_address or self.wallet.address
        
        # Get RPC URL from env or use SDK defaults
        if testnet:
            base_url = os.getenv('TESTNET_RPC_URL', constants.TESTNET_API_URL)
        else:
            base_url = os.getenv('MAINNET_RPC_URL', constants.MAINNET_API_URL)
        
        # Direct SDK instances - use these for all operations
        self.exchange = Exchange(self.wallet, base_url)
        self.info = Info(base_url, skip_ws=True)
        
        # WebSocket reference (set by bot.py after initialization)
        self.websocket = None
        
        self._meta_cache: Optional[Dict] = None
        self._loop = asyncio.get_event_loop()
        
        logger.info(f"HyperLiquidClient initialized for {self.address[:10]}...")
    
    # ==================== METADATA ====================
    @lru_cache(maxsize=1)
    def get_meta(self) -> Dict:
        """Cached perpetuals metadata."""
        if not self._meta_cache:
            self._meta_cache = self.info.meta()
        return self._meta_cache
    
    def get_asset_id(self, symbol: str) -> int:
        """Get asset index from symbol."""
        meta = self.get_meta()
        for i, asset in enumerate(meta.get("universe", [])):
            if asset["name"] == symbol:
                return i
        raise ValueError(f"Unknown symbol: {symbol}")
    
    def get_sz_decimals(self, symbol: str) -> int:
        """Get size decimals for proper rounding."""
        meta = self.get_meta()
        for asset in meta.get("universe", []):
            if asset["name"] == symbol:
                return asset.get("szDecimals", 3)
        return 3
    
    def get_price_decimals(self, symbol: str) -> int:
        """
        Get price decimals (tick size) for proper price rounding.
        
        HyperLiquid uses: 6 - szDecimals for perps, 8 - szDecimals for spot.
        This matches the SDK's _slippage_price() rounding logic.
        """
        try:
            # Get szDecimals from metadata
            meta = self.get_meta()
            for asset in meta.get("universe", []):
                if asset.get("name") == symbol:
                    sz_decimals = asset.get("szDecimals", 3)
                    # HyperLiquid formula: 6 - szDecimals for perps
                    return max(0, 6 - sz_decimals)
        except Exception:
            pass
        
        # Fallback: assume szDecimals=3, so 6-3=3 decimals
        return 3
    
    def round_price(self, symbol: str, price: float) -> float:
        """Round price to valid tick size for the asset."""
        decimals = self.get_price_decimals(symbol)
        return round(price, decimals)
    
    # ==================== DIRECT SDK PASSTHROUGH ====================
    # Exchange methods - use exchange.method() directly for:
    #   order(), bulk_orders(), market_open(), market_close()
    #   modify_order(), bulk_modify_orders_new()
    #   cancel(), cancel_by_cloid(), bulk_cancel(), bulk_cancel_by_cloid()
    #   schedule_cancel(), update_leverage(), update_isolated_margin()
    #   approve_agent(), set_referrer(), usd_transfer(), spot_transfer()
    
    # Info methods - use info.method() directly for:
    #   user_state(), spot_user_state(), open_orders(), frontend_open_orders()
    #   all_mids(), l2_snapshot(), candles_snapshot(), meta(), spot_meta()
    #   user_fills(), user_fills_by_time(), user_funding_history()
    #   query_order_by_oid(), query_order_by_cloid()
    #   user_fees(), user_rate_limit(), historical_orders()
    
    # ==================== CONVENIENCE WRAPPERS ====================
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for symbol."""
        state = self.info.user_state(self.address)
        for pos in state.get("assetPositions", []):
            if pos["position"]["coin"] == symbol:
                return pos["position"]
        return None
    
    def get_all_positions(self) -> List[Dict]:
        """Get all open positions."""
        state = self.info.user_state(self.address)
        return [p["position"] for p in state.get("assetPositions", []) 
                if float(p["position"].get("szi", 0)) != 0]
    
    def get_open_positions(self) -> List[Dict]:
        """
        Get all open positions with parsed fields for telegram bot compatibility.
        Returns positions with: symbol, size, side, entry_price, unrealized_pnl, position_value, leverage, mark_price
        """
        raw_positions = self.get_all_positions()
        
        # Get current mid prices for mark price
        try:
            mids = self.info.all_mids()
        except:
            mids = {}
        
        parsed = []
        for p in raw_positions:
            size = float(p.get("szi", 0))
            if size != 0:
                leverage = p.get("leverage", {})
                leverage_val = float(leverage.get("value", 1)) if isinstance(leverage, dict) else float(leverage or 1)
                symbol = p.get("coin")
                entry_price = float(p.get("entryPx", 0))
                mark_price = float(mids.get(symbol, entry_price))  # Use mid price or fallback to entry
                
                parsed.append({
                    'symbol': symbol,
                    'size': size,
                    'side': 'long' if size > 0 else 'short',
                    'entry_price': entry_price,
                    'mark_price': mark_price,
                    'unrealized_pnl': float(p.get("unrealizedPnl", 0)),
                    'position_value': float(p.get("positionValue", 0)),
                    'leverage': leverage_val,
                    'liquidation_price': float(p.get("liquidationPx", 0)) if p.get("liquidationPx") else None,
                })
        return parsed
    
    def get_balance(self) -> float:
        """Get available balance."""
        state = self.info.user_state(self.address)
        return float(state.get("withdrawable", 0))
    
    def get_equity(self) -> float:
        """Get account equity."""
        state = self.info.user_state(self.address)
        margin = state.get("marginSummary", {})
        return float(margin.get("accountValue", 0))
    
    def get_mid_price(self, symbol: str) -> float:
        """Get current mid price."""
        mids = self.info.all_mids()
        return float(mids.get(symbol, 0))
    
    async def get_market_price(self, symbol: str) -> float:
        """
        Async get current mid price for telegram bot compatibility.
        Returns the mid price (average of best bid/ask).
        """
        mids = await self._loop.run_in_executor(None, self.info.all_mids)
        return float(mids.get(symbol, 0))
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders, optionally filtered by symbol."""
        orders = self.info.open_orders(self.address)
        if symbol:
            return [o for o in orders if o.get("coin") == symbol]
        return orders
    
    def get_frontend_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open orders with detailed frontend info including TP/SL flags.
        
        Returns orders with:
        - isPositionTpsl: bool - True if this is a position TP/SL
        - isTrigger: bool - True if trigger order
        - triggerPx: trigger price
        - triggerCondition: "gt" or "lt"
        """
        orders = self.info.frontend_open_orders(self.address)
        if symbol:
            return [o for o in orders if o.get("coin") == symbol]
        return orders
    
    def get_candles(self, symbol: str, interval: str = "1m", limit: int = 100) -> List[Dict]:
        """
        Get historical candles from API.
        
        Args:
            symbol: Trading pair symbol
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch
        
        Returns:
            List of candle dicts with open, high, low, close, volume, time
        """
        import time as time_module
        try:
            # Calculate time range based on interval and limit
            now_ms = int(time_module.time() * 1000)
            
            # Parse interval to get milliseconds per candle
            interval_map = {
                '1m': 60 * 1000,
                '5m': 5 * 60 * 1000,
                '15m': 15 * 60 * 1000,
                '30m': 30 * 60 * 1000,
                '1h': 60 * 60 * 1000,
                '4h': 4 * 60 * 60 * 1000,
                '1d': 24 * 60 * 60 * 1000,
            }
            interval_ms = interval_map.get(interval, 60 * 1000)
            start_time = now_ms - (limit * interval_ms)
            
            # SDK candles_snapshot requires startTime and endTime
            raw_candles = self.info.candles_snapshot(symbol, interval, start_time, now_ms)
            
            # Transform to standard format
            candles = []
            for c in raw_candles:
                if isinstance(c, dict):
                    candles.append({
                        'open': float(c.get('o', c.get('open', 0))),
                        'high': float(c.get('h', c.get('high', 0))),
                        'low': float(c.get('l', c.get('low', 0))),
                        'close': float(c.get('c', c.get('close', 0))),
                        'volume': float(c.get('v', c.get('volume', 0))),
                        'time': c.get('t', c.get('time', 0))
                    })
                elif isinstance(c, (list, tuple)) and len(c) >= 5:
                    # Handle array format [time, open, high, low, close, volume]
                    candles.append({
                        'time': c[0],
                        'open': float(c[1]),
                        'high': float(c[2]),
                        'low': float(c[3]),
                        'close': float(c[4]),
                        'volume': float(c[5]) if len(c) > 5 else 0
                    })
            return candles
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
            return []
    
    # ==================== ASYNC WRAPPERS ====================
    async def async_user_state(self) -> Dict:
        return await self._loop.run_in_executor(None, self.info.user_state, self.address)
    
    async def async_all_mids(self) -> Dict:
        return await self._loop.run_in_executor(None, self.info.all_mids)
    
    async def async_open_orders(self) -> List[Dict]:
        return await self._loop.run_in_executor(None, self.info.open_orders, self.address)
    
    async def async_l2_snapshot(self, symbol: str) -> Dict:
        return await self._loop.run_in_executor(None, self.info.l2_snapshot, symbol)
    
    async def get_account_state(self) -> Dict[str, Any]:
        """
        Get comprehensive account state for bot.py and telegram_bot.py compatibility.
        Returns dict with account_value, margin_used, positions, etc.
        """
        # Try WebSocket cache first for speed
        if self.websocket and hasattr(self.websocket, 'get_cached_state'):
            cached = self.websocket.get_cached_state()
            if cached:
                return cached
        
        # Fallback to API
        state = await self._loop.run_in_executor(None, self.info.user_state, self.address)
        margin = state.get("marginSummary", {})
        
        # Parse positions with all fields needed by telegram_bot.py
        positions = []
        for pos in state.get("assetPositions", []):
            p = pos.get("position", {})
            size = float(p.get("szi", 0))
            if size != 0:
                position_value = float(p.get("positionValue", 0))
                leverage = p.get("leverage", {})
                leverage_val = float(leverage.get("value", 1)) if isinstance(leverage, dict) else float(leverage or 1)
                
                positions.append({
                    'symbol': p.get("coin"),
                    'size': size,
                    'side': 'long' if size > 0 else 'short',  # Added for telegram_bot
                    'entry_price': float(p.get("entryPx", 0)),
                    'mark_price': position_value / abs(size) if size else 0,
                    'unrealized_pnl': float(p.get("unrealizedPnl", 0)),
                    'position_value': position_value,  # Added for telegram_bot
                    'leverage': leverage_val,
                    'liquidation_price': float(p.get("liquidationPx", 0)) if p.get("liquidationPx") else None,
                })
        
        return {
            'account_value': float(margin.get("accountValue", 0)),
            'margin_used': float(margin.get("totalMarginUsed", 0)),
            'available_margin': float(state.get("withdrawable", 0)),
            'positions': positions,
        }


def create_client(account_address: str, api_key: str, api_secret: str, testnet: bool = False) -> 'HyperLiquidClient':
    """Create HyperLiquidClient instance."""
    return HyperLiquidClient(account_address, api_key, api_secret, testnet)
