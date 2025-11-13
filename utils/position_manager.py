from typing import Dict, List, Optional, Tuple
import asyncio
from datetime import datetime
from loguru import logger
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

class PositionManager:
    """Manages trading positions on Hyperliquid"""
    
    def __init__(self, exchange: Exchange, info: Info):
        self.exchange = exchange
        self.info = info
        
    async def place_market_order(self, symbol: str, is_buy: bool, sz: float, 
                               reduce_only: bool = False) -> Optional[Dict]:
        """Place a market order"""
        try:
            # Convert symbol format (ETH-USD -> ETH)
            hl_symbol = symbol.split('-')[0]
            
            # Place order
            order_result = self.exchange.market_order(
                coin=hl_symbol,
                is_buy=is_buy,
                sz=sz,
                reduce_only=reduce_only
            )
            
            if order_result and order_result.get('status') == 'ok':
                logger.info(f"Market order placed: {order_result}")
                return order_result
            else:
                logger.error(f"Failed to place market order: {order_result}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    async def place_limit_order(self, symbol: str, is_buy: bool, sz: float, 
                              limit_px: float, reduce_only: bool = False) -> Optional[Dict]:
        """Place a limit order"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            order_result = self.exchange.order(
                coin=hl_symbol,
                is_buy=is_buy,
                sz=sz,
                limit_px=limit_px,
                reduce_only=reduce_only
            )
            
            if order_result and order_result.get('status') == 'ok':
                logger.info(f"Limit order placed: {order_result}")
                return order_result
            else:
                logger.error(f"Failed to place limit order: {order_result}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    async def cancel_order(self, symbol: str, oid: int) -> bool:
        """Cancel an existing order"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            cancel_result = self.exchange.cancel(
                coin=hl_symbol,
                oid=oid
            )
            
            if cancel_result and cancel_result.get('status') == 'ok':
                logger.info(f"Order cancelled: {cancel_result}")
                return True
            else:
                logger.error(f"Failed to cancel order: {cancel_result}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def cancel_all_orders(self, symbol: str) -> bool:
        """Cancel all orders for a symbol"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            # Get open orders first
            open_orders = await self.get_open_orders(symbol)
            
            if not open_orders:
                return True
            
            # Cancel each order
            success_count = 0
            for order in open_orders:
                if await self.cancel_order(symbol, order.get('oid')):
                    success_count += 1
            
            logger.info(f"Cancelled {success_count}/{len(open_orders)} orders for {symbol}")
            return success_count == len(open_orders)
            
        except Exception as e:
            logger.error(f"Error cancelling all orders for {symbol}: {e}")
            return False
    
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for a symbol"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            # Get user state which includes positions
            user_state = self.info.user_state(self.exchange.wallet.address)
            
            if not user_state or 'assetPositions' not in user_state:
                return None
            
            # Find position for the symbol
            for position in user_state['assetPositions']:
                if position['position']['coin'] == hl_symbol:
                    pos_data = position['position']
                    
                    return {
                        'symbol': symbol,
                        'size': float(pos_data.get('szi', 0)),
                        'entry_px': float(pos_data.get('entryPx', 0)),
                        'unrealized_pnl': float(position.get('unrealizedPnl', 0)),
                        'position_value': float(pos_data.get('positionValue', 0)),
                        'margin_used': float(pos_data.get('marginUsed', 0)),
                        'leverage': float(pos_data.get('leverage', {}).get('value', 1)),
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting position for {symbol}: {e}")
            return None
    
    async def get_all_positions(self) -> List[Dict]:
        """Get all current positions"""
        try:
            user_state = self.info.user_state(self.exchange.wallet.address)
            
            if not user_state or 'assetPositions' not in user_state:
                return []
            
            positions = []
            for position in user_state['assetPositions']:
                pos_data = position['position']
                coin = pos_data.get('coin', '')
                
                # Only include positions with non-zero size
                size = float(pos_data.get('szi', 0))
                if size != 0:
                    positions.append({
                        'symbol': f"{coin}-USD",
                        'size': size,
                        'entry_px': float(pos_data.get('entryPx', 0)),
                        'unrealized_pnl': float(position.get('unrealizedPnl', 0)),
                        'position_value': float(pos_data.get('positionValue', 0)),
                        'margin_used': float(pos_data.get('marginUsed', 0)),
                        'leverage': float(pos_data.get('leverage', {}).get('value', 1)),
                        'timestamp': datetime.now().isoformat()
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting all positions: {e}")
            return []
    
    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get open orders for a symbol or all symbols"""
        try:
            # Get open orders from user state
            user_state = self.info.user_state(self.exchange.wallet.address)
            
            if not user_state or 'openOrders' not in user_state:
                return []
            
            open_orders = []
            for order in user_state['openOrders']:
                order_coin = order.get('coin', '')
                
                # Filter by symbol if specified
                if symbol:
                    hl_symbol = symbol.split('-')[0]
                    if order_coin != hl_symbol:
                        continue
                
                open_orders.append({
                    'symbol': f"{order_coin}-USD",
                    'oid': order.get('oid'),
                    'side': 'buy' if order.get('side') == 'B' else 'sell',
                    'size': float(order.get('sz', 0)),
                    'limit_price': float(order.get('limitPx', 0)),
                    'reduce_only': order.get('reduceOnly', False),
                    'timestamp': datetime.now().isoformat()
                })
            
            return open_orders
            
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
    
    async def close_position(self, symbol: str) -> bool:
        """Close entire position for a symbol"""
        try:
            position = await self.get_position(symbol)
            
            if not position:
                logger.info(f"No position to close for {symbol}")
                return True
            
            size = position['size']
            if size == 0:
                logger.info(f"Position size is zero for {symbol}")
                return True
            
            # Determine side (opposite of current position)
            is_buy = size < 0  # If short, buy to close
            close_size = abs(size)
            
            # Place market order to close
            result = await self.place_market_order(
                symbol=symbol,
                is_buy=is_buy,
                sz=close_size,
                reduce_only=True
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False
    
    async def close_partial_position(self, symbol: str, quantity: float) -> bool:
        """Close partial position"""
        try:
            position = await self.get_position(symbol)
            
            if not position:
                logger.warning(f"No position found for {symbol}")
                return False
            
            current_size = position['size']
            if abs(quantity) > abs(current_size):
                logger.warning(f"Requested quantity {quantity} exceeds position size {current_size}")
                quantity = abs(current_size)
            
            # Determine side (opposite of current position)
            is_buy = current_size < 0  # If short, buy to close
            
            # Place market order to partially close
            result = await self.place_market_order(
                symbol=symbol,
                is_buy=is_buy,
                sz=abs(quantity),
                reduce_only=True
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error closing partial position for {symbol}: {e}")
            return False
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol"""
        try:
            hl_symbol = symbol.split('-')[0]
            
            # Update leverage
            result = self.exchange.update_leverage(
                coin=hl_symbol,
                leverage=leverage
            )
            
            if result and result.get('status') == 'ok':
                logger.info(f"Leverage set to {leverage}x for {symbol}")
                return True
            else:
                logger.error(f"Failed to set leverage for {symbol}: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting leverage for {symbol}: {e}")
            return False
    
    async def get_trade_history(self, symbol: str = None) -> List[Dict]:
        """Get trade history"""
        try:
            # Get user fills (trade history)
            user_fills = self.info.user_fills(self.exchange.wallet.address)
            
            if not user_fills:
                return []
            
            trades = []
            for fill in user_fills:
                fill_coin = fill.get('coin', '')
                
                # Filter by symbol if specified
                if symbol:
                    hl_symbol = symbol.split('-')[0]
                    if fill_coin != hl_symbol:
                        continue
                
                trades.append({
                    'symbol': f"{fill_coin}-USD",
                    'side': 'buy' if fill.get('side') == 'B' else 'sell',
                    'size': float(fill.get('sz', 0)),
                    'price': float(fill.get('px', 0)),
                    'fee': float(fill.get('fee', 0)),
                    'timestamp': fill.get('time', 0),
                    'order_id': fill.get('oid')
                })
            
            return sorted(trades, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    async def get_account_summary(self) -> Dict:
        """Get account summary including balance, positions, etc."""
        try:
            user_state = self.info.user_state(self.exchange.wallet.address)
            
            if not user_state:
                return {}
            
            margin_summary = user_state.get('marginSummary', {})
            
            return {
                'account_value': float(margin_summary.get('accountValue', 0)),
                'total_margin_used': float(margin_summary.get('totalMarginUsed', 0)),
                'total_ntl_pos': float(margin_summary.get('totalNtlPos', 0)),
                'total_raw_usd': float(margin_summary.get('totalRawUsd', 0)),
                'withdrawable': float(user_state.get('withdrawable', 0)),
                'cross_margin_summary': user_state.get('crossMarginSummary', {}),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}