"""
Hyperliquid Client - Official SDK Wrapper
Provides normalized interface for HyperLiquid exchange operations
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
import eth_account

logger = logging.getLogger(__name__)


class HyperLiquidClient:
    """
    Wrapper for HyperLiquid SDK with normalized interface
    """
    
    def __init__(self, account_address: str, api_key: str, api_secret: str, 
                 testnet: bool = False):
        """
        Initialize HyperLiquid client
        
        Args:
            account_address: Main trading account (0x...)
            api_key: API wallet public key
            api_secret: API wallet private key
            testnet: Use testnet (default: False for mainnet)
        """
        self.account_address = account_address
        self.api_key = api_key
        self.testnet = testnet
        
        # Initialize SDK components
        base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
        
        # Create wallet from private key
        self.wallet = eth_account.Account.from_key(api_secret)
        
        # Initialize Exchange for trading
        self.exchange = Exchange(
            self.wallet,
            base_url,
            account_address=account_address
        )
        
        # Initialize Info for market data
        self.info = Info(base_url, skip_ws=True)
        
        # Cache asset metadata for decimal precision
        self._asset_metadata = {}
        self._load_asset_metadata()
        
        logger.info(f"🔗 HyperLiquid client initialized")
        logger.info(f"   Account: {account_address}")
        logger.info(f"   API Wallet: {self.wallet.address}")
        logger.info(f"   Network: {'Testnet' if testnet else 'Mainnet'}")
    
    def _load_asset_metadata(self):
        """Load asset metadata from HyperLiquid API"""
        try:
            meta = self.info.meta()
            universe = meta.get('universe', [])
            for asset in universe:
                name = asset.get('name')
                self._asset_metadata[name] = {
                    'szDecimals': asset.get('szDecimals', 2),
                    'maxLeverage': asset.get('maxLeverage', 50)
                }
            logger.info(f"📊 Loaded metadata for {len(self._asset_metadata)} assets")
        except Exception as e:
            logger.warning(f"Failed to load asset metadata: {e}. Using defaults.")
    
    def get_size_decimals(self, symbol: str) -> int:
        """Get the number of decimal places for position size for a given symbol"""
        return self._asset_metadata.get(symbol, {}).get('szDecimals', 2)
    
    def get_price_decimals(self, price: float) -> int:
        """Get appropriate decimal places for price based on price magnitude"""
        if price >= 100:
            return 2
        elif price >= 10:
            return 3
        else:
            return 4
    
    async def get_account_state(self) -> Dict[str, Any]:
        """
        Get account balance and positions
        
        Returns:
            Account state with balance, positions, margin
        """
        try:
            user_state = self.info.user_state(self.account_address)
            
            # Extract balance info
            margin_summary = user_state.get('marginSummary', {})
            account_value = Decimal(str(margin_summary.get('accountValue', '0')))
            total_margin_used = Decimal(str(margin_summary.get('totalMarginUsed', '0')))
            total_ntl_pos = Decimal(str(margin_summary.get('totalNtlPos', '0')))
            total_raw_usd = Decimal(str(margin_summary.get('totalRawUsd', '0')))
            
            # Extract positions
            positions = []
            asset_positions = user_state.get('assetPositions', [])
            
            for pos in asset_positions:
                position_data = pos.get('position', {})
                
                # Skip empty positions
                if not position_data.get('szi') or float(position_data.get('szi', 0)) == 0:
                    continue
                
                coin = position_data.get('coin', '')
                size = Decimal(str(position_data.get('szi', '0')))
                entry_px = Decimal(str(position_data.get('entryPx', '0')))
                
                # Get position value and leverage
                position_value = abs(size * entry_px)
                leverage_data = position_data.get('leverage', {})
                if isinstance(leverage_data, dict):
                    leverage = Decimal(str(leverage_data.get('value', '1')))
                else:
                    leverage = Decimal(str(leverage_data))
                
                # Calculate unrealized PnL
                unrealized_pnl = Decimal(str(position_data.get('unrealizedPnl', '0')))
                
                positions.append({
                    'symbol': coin,
                    'size': float(size),
                    'side': 'long' if size > 0 else 'short',
                    'entry_price': float(entry_px),
                    'position_value': float(position_value),
                    'leverage': float(leverage),
                    'unrealized_pnl': float(unrealized_pnl),
                    'liquidation_px': position_data.get('liquidationPx'),
                    'margin_used': position_data.get('marginUsed', '0')
                })
            
            return {
                'account_value': float(account_value),
                'balance': float(total_raw_usd),
                'equity': float(account_value),
                'margin_used': float(total_margin_used),
                'margin_available': float(account_value - total_margin_used),
                'total_position_value': float(total_ntl_pos),
                'positions': positions,
                'withdrawable': margin_summary.get('withdrawable', '0')
            }
            
        except Exception as e:
            logger.error(f"Error getting account state: {e}")
            return {
                'account_value': 0,
                'balance': 0,
                'equity': 0,
                'margin_used': 0,
                'margin_available': 0,
                'total_position_value': 0,
                'positions': [],
                'error': str(e)
            }
    
    def get_candles(self, symbol: str, interval: str = '1h', limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get historical candle data for symbol
        
        Args:
            symbol: Trading symbol (e.g., 'HYPE', 'SOL')
            interval: Candle interval ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of candle dicts with keys: time, open, high, low, close, volume
        """
        try:
            # HyperLiquid API candles endpoint
            candles_data = self.info.candles_snapshot(symbol, interval, limit)
            
            if not candles_data:
                logger.warning(f"No candle data received for {symbol}")
                return []
            
            # Convert to standard format
            candles = []
            for candle in candles_data:
                candles.append({
                    'time': int(candle['t']),  # timestamp in ms
                    'open': float(candle['o']),
                    'high': float(candle['h']),
                    'low': float(candle['l']),
                    'close': float(candle['c']),
                    'volume': float(candle['v'])
                })
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return []
    
    async def get_market_price(self, symbol: str) -> Optional[Decimal]:
        """
        Get current market price for symbol
        
        Args:
            symbol: Trading symbol (e.g., 'SOL')
            
        Returns:
            Current price or None
        """
        try:
            all_mids = self.info.all_mids()
            price_str = all_mids.get(symbol)
            
            if price_str:
                return Decimal(str(price_str))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market price for {symbol}: {e}")
            return None
    
    async def place_order(self, symbol: str, side: str, size: Decimal, 
                         order_type: str = 'market', price: Optional[Decimal] = None,
                         reduce_only: bool = False, sl_price: Optional[Decimal] = None,
                         tp_price: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Place order on HyperLiquid
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size
            order_type: 'market' or 'limit'
            price: Limit price (required for limit orders)
            reduce_only: Reduce only flag
            sl_price: Stop loss price (for OCO)
            tp_price: Take profit price (for OCO)
            
        Returns:
            Order result
        """
        try:
            # Determine if it's a buy or sell
            is_buy = side.lower() == 'buy'
            
            # Format size with proper sign
            size_float = float(size)
            if not is_buy:
                size_float = -abs(size_float)
            else:
                size_float = abs(size_float)
            
            # Round size to 2 decimals for SOL
            size_float = round(size_float, 2)
            
            # Prepare order parameters
            if order_type == 'market':
                # Market order
                order_result = self.exchange.market_open(
                    symbol,
                    is_buy,
                    abs(size_float),
                    None  # No slippage (will use default)
                )
            else:
                # Limit order
                if price is None:
                    raise ValueError("Price required for limit order")
                
                # Round price to 2 decimals for prices > $100
                price_float = float(price)
                if price_float >= 100:
                    price_float = round(price_float, 2)
                elif price_float >= 10:
                    price_float = round(price_float, 3)
                else:
                    price_float = round(price_float, 4)
                
                order_result = self.exchange.order(
                    symbol,
                    is_buy,
                    abs(size_float),
                    price_float,
                    {'limit': {'tif': 'Gtc'}},
                    reduce_only=reduce_only
                )
            
            # Check if order was successful
            if order_result and 'status' in order_result:
                if order_result['status'] == 'ok':
                    # Check for errors in response
                    response = order_result.get('response', {})
                    if isinstance(response, dict):
                        data = response.get('data', {})
                        if isinstance(data, dict):
                            statuses = data.get('statuses', [])
                            if statuses and isinstance(statuses[0], dict):
                                if 'error' in statuses[0]:
                                    logger.error(f"Order error: {statuses[0]['error']}")
                                    return {
                                        'success': False,
                                        'error': statuses[0]['error'],
                                        'raw': order_result
                                    }
                    
                    logger.info(f"✅ Order placed: {side} {size_float} {symbol}")
                    return {
                        'success': True,
                        'order_id': str(response.get('data', {}).get('statuses', [{}])[0].get('resting', {}).get('oid', 'unknown')),
                        'symbol': symbol,
                        'side': side,
                        'size': abs(size_float),
                        'type': order_type,
                        'price': price_float if order_type == 'limit' else None,
                        'raw': order_result
                    }
                else:
                    logger.error(f"Order failed: {order_result}")
                    return {
                        'success': False,
                        'error': order_result.get('response', 'Unknown error'),
                        'raw': order_result
                    }
            
            logger.error(f"Invalid order response: {order_result}")
            return {
                'success': False,
                'error': 'Invalid response format',
                'raw': order_result
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    async def place_stop_market_order(self, symbol: str, side: str, size: Decimal,
                                     trigger_price: Decimal, reduce_only: bool = False) -> Dict[str, Any]:
        """
        Place stop-market order on HyperLiquid
        This triggers a market order when price hits the trigger level
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size
            trigger_price: Price at which to trigger the market order
            reduce_only: Reduce only flag
            
        Returns:
            Order result
        """
        try:
            # Determine if it's a buy or sell
            is_buy = side.lower() == 'buy'
            
            # Format size with proper sign
            size_float = float(size)
            if not is_buy:
                size_float = -abs(size_float)
            else:
                size_float = abs(size_float)
            
            # Round size to 2 decimals
            size_float = round(size_float, 2)
            
            # Round trigger price
            trigger_float = float(trigger_price)
            if trigger_float >= 100:
                trigger_float = round(trigger_float, 2)
            elif trigger_float >= 10:
                trigger_float = round(trigger_float, 3)
            else:
                trigger_float = round(trigger_float, 4)
            
            # Place stop-market order (trigger order that executes as market)
            order_result = self.exchange.order(
                symbol,
                is_buy,
                abs(size_float),
                trigger_float,
                {
                    'trigger': {
                        'triggerPx': trigger_float,
                        'isMarket': True,  # Execute as market order when triggered
                        'tpsl': 'sl'  # Mark as stop-loss
                    }
                },
                reduce_only=reduce_only
            )
            
            # Check if order was successful
            if order_result and 'status' in order_result:
                if order_result['status'] == 'ok':
                    # Check for errors in response
                    response = order_result.get('response', {})
                    if isinstance(response, dict):
                        data = response.get('data', {})
                        if isinstance(data, dict):
                            statuses = data.get('statuses', [])
                            if statuses and isinstance(statuses[0], dict):
                                if 'error' in statuses[0]:
                                    logger.error(f"Stop order error: {statuses[0]['error']}")
                                    return {
                                        'success': False,
                                        'error': statuses[0]['error'],
                                        'raw': order_result
                                    }
                    
                    logger.info(f"✅ Stop-market order placed: {side} {size_float} {symbol} @ trigger {trigger_float}")
                    return {
                        'success': True,
                        'order_id': str(response.get('data', {}).get('statuses', [{}])[0].get('resting', {}).get('oid', 'unknown')),
                        'symbol': symbol,
                        'side': side,
                        'size': abs(size_float),
                        'type': 'stop-market',
                        'trigger_price': trigger_float,
                        'raw': order_result
                    }
                else:
                    logger.error(f"Stop order failed: {order_result}")
                    return {
                        'success': False,
                        'error': order_result.get('response', 'Unknown error'),
                        'raw': order_result
                    }
            
            logger.error(f"Invalid stop order result: {order_result}")
            return {
                'success': False,
                'error': 'Invalid order result',
                'raw': order_result
            }
                
        except Exception as e:
            logger.error(f"Error placing stop order: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    async def place_take_profit_order(self, symbol: str, side: str, size: Decimal,
                                      trigger_price: Decimal, reduce_only: bool = False) -> Dict[str, Any]:
        """
        Place take-profit order on HyperLiquid
        This is a limit order marked as TP type
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size
            trigger_price: Price at which to take profit
            reduce_only: Reduce only flag
            
        Returns:
            Order result
        """
        try:
            # Determine if it's a buy or sell
            is_buy = side.lower() == 'buy'
            
            # Format size with proper sign
            size_float = float(size)
            if not is_buy:
                size_float = -abs(size_float)
            else:
                size_float = abs(size_float)
            
            # Round size to 2 decimals
            size_float = round(size_float, 2)
            
            # Round trigger price
            trigger_float = float(trigger_price)
            if trigger_float >= 100:
                trigger_float = round(trigger_float, 2)
            elif trigger_float >= 10:
                trigger_float = round(trigger_float, 3)
            else:
                trigger_float = round(trigger_float, 4)
            
            # Place TP order (Take Market - executes at market price when trigger hit)
            # For Take Market: pass trigger_float as limit_px, but isMarket=True executes at market
            order_result = self.exchange.order(
                symbol,
                is_buy,
                abs(size_float),
                trigger_float,  # limit_px = trigger price (required by SDK)
                {
                    'trigger': {
                        'triggerPx': trigger_float,
                        'isMarket': True,  # ✅ Execute as MARKET order when triggered
                        'tpsl': 'tp'  # Mark as take-profit
                    }
                },
                reduce_only=reduce_only
            )
            
            # Log raw response for debugging
            logger.debug(f"TP order raw response: {order_result}")
            
            # Check if order was successful
            if order_result and 'status' in order_result:
                if order_result['status'] == 'ok':
                    # Check for errors in response
                    response = order_result.get('response', {})
                    if isinstance(response, dict):
                        data = response.get('data', {})
                        if isinstance(data, dict):
                            statuses = data.get('statuses', [])
                            if statuses and isinstance(statuses[0], dict):
                                if 'error' in statuses[0]:
                                    logger.error(f"TP order error: {statuses[0]['error']}")
                                    return {
                                        'success': False,
                                        'error': statuses[0]['error'],
                                        'raw': order_result
                                    }
                    
                    logger.info(f"✅ Take-profit order placed: {side} {size_float} {symbol} @ {trigger_float}")
                    return {
                        'success': True,
                        'order_id': str(response.get('data', {}).get('statuses', [{}])[0].get('resting', {}).get('oid', 'unknown')),
                        'symbol': symbol,
                        'side': side,
                        'size': abs(size_float),
                        'type': 'take-profit',
                        'trigger_price': trigger_float,
                        'raw': order_result
                    }
                else:
                    logger.error(f"TP order failed: {order_result}")
                    return {
                        'success': False,
                        'error': order_result.get('response', 'Unknown error'),
                        'raw': order_result
                    }
            
            logger.error(f"Invalid TP order result: {order_result}")
            return {
                'success': False,
                'error': 'Invalid order result',
                'raw': order_result
            }
                
        except Exception as e:
            logger.error(f"Error placing TP order: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            result = self.exchange.cancel(symbol, int(order_id))
            return result.get('status') == 'ok'
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            return False
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol in cross-margin mode
        
        Args:
            symbol: Trading symbol
            leverage: Leverage value (1-50)
            
        Returns:
            True if successful
        """
        try:
            # Use is_cross=True for cross-margin mode (default on HyperLiquid)
            result = self.exchange.update_leverage(leverage, symbol, is_cross=True)
            success = result.get('status') == 'ok'
            
            if success:
                logger.info(f"✅ Leverage set to {leverage}x for {symbol} (cross-margin)")
            else:
                logger.error(f"❌ Failed to set leverage: {result}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error setting leverage: {e}")
            return False
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close entire position for symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Close result
        """
        try:
            # Get current position
            account_state = await self.get_account_state()
            position = next((p for p in account_state['positions'] if p['symbol'] == symbol), None)
            
            if not position:
                return {'success': False, 'error': 'No position found'}
            
            # Determine close side (opposite of position)
            close_side = 'sell' if position['side'] == 'long' else 'buy'
            close_size = abs(Decimal(str(position['size'])))
            
            # Place market order to close
            result = await self.place_order(
                symbol,
                close_side,
                close_size,
                order_type='market',
                reduce_only=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_meta_info(self) -> Dict[str, Any]:
        """Get exchange metadata (symbols, tick sizes, etc.)"""
        try:
            return self.info.meta()
        except Exception as e:
            logger.error(f"Error getting meta info: {e}")
            return {}
