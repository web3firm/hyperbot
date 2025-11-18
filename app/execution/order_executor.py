"""
Order Executor - Handles actual order placement and management
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone

from app.hl.hl_client import HyperLiquidClient
from app.strategies.legacy.base_strategy import Signal

logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    Executes trading orders on HyperLiquid
    """
    
    def __init__(self, client: HyperLiquidClient, dry_run: bool = True):
        """
        Initialize order executor
        
        Args:
            client: HyperLiquid client
            dry_run: If True, simulates orders without executing
        """
        self.client = client
        self.dry_run = dry_run
        self.order_history = []
        
        logger.info(f"OrderExecutor initialized (dry_run={dry_run})")
    
    async def execute_signal(self, signal: Signal, position_size: Decimal) -> Dict[str, Any]:
        """
        Execute a trading signal
        
        Args:
            signal: Signal to execute
            position_size: Size of position in base currency
            
        Returns:
            Dictionary with execution results
        """
        try:
            logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}Executing {signal.direction} signal for {signal.symbol}")
            logger.info(f"  Entry: ${signal.entry_price}, Size: {position_size}")
            
            if signal.direction == 'long':
                result = await self._execute_long(signal, position_size)
            elif signal.direction == 'short':
                result = await self._execute_short(signal, position_size)
            elif signal.direction == 'close':
                result = await self._execute_close(signal)
            else:
                return {
                    'success': False,
                    'error': f"Unknown signal direction: {signal.direction}"
                }
            
            # Record order
            order_record = {
                'signal': signal,
                'result': result,
                'timestamp': datetime.now(timezone.utc),
                'dry_run': self.dry_run
            }
            self.order_history.append(order_record)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _execute_long(self, signal: Signal, size: Decimal) -> Dict[str, Any]:
        """Execute a long (buy) order"""
        
        # Round size to appropriate decimals for the asset
        # SOL requires 2 decimal places per szDecimals
        rounded_size = round(float(size), 2)  # Use 2 decimals for SOL
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would open LONG {rounded_size} {signal.symbol} @ ${signal.entry_price}")
            logger.info(f"[DRY RUN] Stop Loss: ${signal.stop_loss}, Take Profit: ${signal.take_profit}")
            
            return {
                'success': True,
                'order_type': 'long',
                'symbol': signal.symbol,
                'size': rounded_size,
                'entry_price': float(signal.entry_price),
                'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                'take_profit': float(signal.take_profit) if signal.take_profit else None,
                'order_id': f"dry_run_{int(datetime.now().timestamp())}",
                'dry_run': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        else:
            # LIVE TRADING - Place actual order
            try:
                # Get current orderbook for slippage calculation
                orderbook = await self.client.get_orderbook(signal.symbol, 5)
                best_ask = orderbook.asks[0].price
                
                # Use limit order slightly above best ask to ensure fill
                limit_price = best_ask * Decimal('1.001')  # 0.1% slippage tolerance
                
                logger.info(f"🔥 LIVE: Placing LONG order {rounded_size} {signal.symbol} @ ${limit_price}")
                
                # Place order via SDK
                # Note: This requires the order method to be implemented in client
                order_result = await self.client.place_order(
                    symbol=signal.symbol,
                    side='buy',
                    size=Decimal(str(rounded_size)),
                    price=Decimal(str(limit_price)),
                    order_type='limit',
                    reduce_only=False
                )
                
                # Check if order was successful
                if order_result.get('success'):
                    logger.info(f"✅ LONG order placed successfully")
                    return {
                        'success': True,
                        'order_type': 'long',
                        'symbol': signal.symbol,
                        'size': rounded_size,
                        'entry_price': float(limit_price),
                        'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                        'take_profit': float(signal.take_profit) if signal.take_profit else None,
                        'order_id': order_result.get('order_id'),
                        'order_result': order_result,
                        'dry_run': False,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    logger.error(f"❌ LONG order failed: {order_result.get('error')}")
                    return {
                        'success': False,
                        'error': order_result.get('error', 'Unknown error'),
                        'order_type': 'long'
                    }
                
            except Exception as e:
                logger.error(f"Failed to place LONG order: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'order_type': 'long'
                }
    
    async def _execute_short(self, signal: Signal, size: Decimal) -> Dict[str, Any]:
        """Execute a short (sell) order"""
        
        # Round size to appropriate decimals - SOL requires 2 decimals
        rounded_size = round(float(size), 2)
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would open SHORT {rounded_size} {signal.symbol} @ ${signal.entry_price}")
            logger.info(f"[DRY RUN] Stop Loss: ${signal.stop_loss}, Take Profit: ${signal.take_profit}")
            
            return {
                'success': True,
                'order_type': 'short',
                'symbol': signal.symbol,
                'size': rounded_size,
                'entry_price': float(signal.entry_price),
                'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                'take_profit': float(signal.take_profit) if signal.take_profit else None,
                'order_id': f"dry_run_{int(datetime.now().timestamp())}",
                'dry_run': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        else:
            # LIVE TRADING - Place actual short order
            try:
                orderbook = await self.client.get_orderbook(signal.symbol, 5)
                best_bid = orderbook.bids[0].price
                
                limit_price = best_bid * Decimal('0.999')  # 0.1% slippage tolerance
                
                logger.info(f"🔥 LIVE: Placing SHORT order {rounded_size} {signal.symbol} @ ${limit_price}")
                
                order_result = await self.client.place_order(
                    symbol=signal.symbol,
                    side='sell',
                    size=Decimal(str(rounded_size)),
                    price=Decimal(str(limit_price)),
                    order_type='limit',
                    reduce_only=False
                )
                
                # Check if order was successful
                if order_result.get('success'):
                    logger.info(f"✅ SHORT order placed successfully")
                    return {
                        'success': True,
                        'order_type': 'short',
                        'symbol': signal.symbol,
                        'size': rounded_size,
                        'entry_price': float(limit_price),
                        'stop_loss': float(signal.stop_loss) if signal.stop_loss else None,
                        'take_profit': float(signal.take_profit) if signal.take_profit else None,
                        'order_id': order_result.get('order_id'),
                        'order_result': order_result,
                        'dry_run': False,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    logger.error(f"❌ SHORT order failed: {order_result.get('error')}")
                    return {
                        'success': False,
                        'error': order_result.get('error', 'Unknown error'),
                        'order_type': 'short'
                    }
                
            except Exception as e:
                logger.error(f"Failed to place SHORT order: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'order_type': 'short'
                }
    
    async def _execute_close(self, signal: Signal) -> Dict[str, Any]:
        """Close existing position"""
        
        try:
            # Get current positions
            positions = await self.client.get_positions()
            
            # Find position for this symbol
            target_position = None
            for pos in positions:
                if pos.symbol == signal.symbol:
                    target_position = pos
                    break
            
            if not target_position:
                # No position exists - this is not an error, just skip silently
                logger.debug(f"No open position found for {signal.symbol} - skipping close signal")
                return {
                    'success': True,  # Changed from False - this is normal behavior
                    'skipped': True,
                    'reason': f"No open position for {signal.symbol}"
                }
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would close {target_position.side} position: {target_position.size} {signal.symbol} @ ${signal.entry_price}")
                
                # Calculate simulated P&L
                if target_position.side == 'long':
                    pnl = (signal.entry_price - target_position.entry_price) * target_position.size
                else:
                    pnl = (target_position.entry_price - signal.entry_price) * target_position.size
                
                return {
                    'success': True,
                    'order_type': 'close',
                    'symbol': signal.symbol,
                    'side': target_position.side,
                    'size': float(target_position.size),
                    'entry_price': float(target_position.entry_price),
                    'exit_price': float(signal.entry_price),
                    'pnl': float(pnl),
                    'order_id': f"dry_run_close_{int(datetime.now().timestamp())}",
                    'dry_run': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            else:
                # LIVE TRADING - Close position
                logger.info(f"🔥 LIVE: Closing {target_position.side} position {target_position.size} {signal.symbol}")
                
                # Determine order side (opposite of position)
                close_side = 'sell' if target_position.side == 'long' else 'buy'
                
                orderbook = await self.client.get_orderbook(signal.symbol, 5)
                if close_side == 'sell':
                    limit_price = orderbook.bids[0].price * Decimal('0.999')
                else:
                    limit_price = orderbook.asks[0].price * Decimal('1.001')
                
                order_result = await self.client.place_order(
                    symbol=signal.symbol,
                    side=close_side,
                    size=Decimal(str(float(target_position.size))),
                    price=Decimal(str(limit_price)),
                    order_type='limit',
                    reduce_only=True  # Ensures we only close, not open opposite
                )
                
                return {
                    'success': True,
                    'order_type': 'close',
                    'symbol': signal.symbol,
                    'side': target_position.side,
                    'size': float(target_position.size),
                    'entry_price': float(target_position.entry_price),
                    'exit_price': float(limit_price),
                    'order_id': order_result.get('oid'),
                    'order_result': order_result,
                    'dry_run': False,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_type': 'close'
            }
    
    def get_order_history(self, limit: int = 10) -> list:
        """Get recent order history"""
        return self.order_history[-limit:]
