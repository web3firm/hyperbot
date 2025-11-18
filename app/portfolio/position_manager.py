"""
Position Manager - Advanced position tracking and management
Enterprise-grade position lifecycle management with P&L tracking
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ManagedPosition:
    """Managed position with full lifecycle tracking"""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: Decimal
    size: Decimal
    entry_time: datetime
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    trailing_stop: Optional[Decimal] = None
    position_id: str = ""
    strategy: str = "unknown"
    
    # P&L tracking
    current_price: Decimal = Decimal('0')
    unrealized_pnl: Decimal = Decimal('0')
    unrealized_pnl_pct: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    fees: Decimal = Decimal('0')
    
    # Risk tracking
    max_pnl: Decimal = Decimal('0')
    max_pnl_pct: Decimal = Decimal('0')
    min_pnl: Decimal = Decimal('0')
    min_pnl_pct: Decimal = Decimal('0')
    
    # State
    is_open: bool = True
    exit_price: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    
    # History
    price_updates: List[Dict[str, Any]] = field(default_factory=list)
    
    def update_price(self, new_price: Decimal):
        """Update position with new market price"""
        self.current_price = new_price
        
        # Calculate P&L
        if self.side == 'long':
            self.unrealized_pnl = (new_price - self.entry_price) * self.size
        else:  # short
            self.unrealized_pnl = (self.entry_price - new_price) * self.size
        
        self.unrealized_pnl_pct = (self.unrealized_pnl / (self.entry_price * self.size)) * 100
        
        # Track max/min P&L
        if self.unrealized_pnl > self.max_pnl:
            self.max_pnl = self.unrealized_pnl
            self.max_pnl_pct = self.unrealized_pnl_pct
        
        if self.unrealized_pnl < self.min_pnl:
            self.min_pnl = self.unrealized_pnl
            self.min_pnl_pct = self.unrealized_pnl_pct
        
        # Store price update
        self.price_updates.append({
            'time': datetime.now(timezone.utc),
            'price': float(new_price),
            'pnl': float(self.unrealized_pnl),
            'pnl_pct': float(self.unrealized_pnl_pct)
        })
        
        # Limit history
        if len(self.price_updates) > 1000:
            self.price_updates.pop(0)
    
    def close(self, exit_price: Decimal, reason: str = "manual"):
        """Close the position"""
        self.is_open = False
        self.exit_price = exit_price
        self.exit_time = datetime.now(timezone.utc)
        self.exit_reason = reason
        
        # Final P&L calculation
        if self.side == 'long':
            self.realized_pnl = (exit_price - self.entry_price) * self.size - self.fees
        else:
            self.realized_pnl = (self.entry_price - exit_price) * self.size - self.fees


class PositionManager:
    """
    Enterprise position manager for tracking and managing all positions
    """
    
    def __init__(self, client, account_manager):
        """
        Initialize position manager
        
        Args:
            client: HyperLiquidClient instance
            account_manager: AccountManager instance
        """
        self.client = client
        self.account_manager = account_manager
        
        # Position tracking
        self.open_positions: Dict[str, ManagedPosition] = {}
        self.closed_positions: List[ManagedPosition] = []
        self.max_closed_history = 1000
        
        # Statistics
        self.total_positions_opened = 0
        self.total_positions_closed = 0
        self.winning_positions = 0
        self.losing_positions = 0
        self.total_realized_pnl = Decimal('0')
        self.total_fees = Decimal('0')
        
        # Position limits
        self.max_positions = 10
        self.max_position_size_pct = Decimal('50')  # % of equity
        self.max_leverage = Decimal('5')
        
        logger.info("📊 Position Manager initialized")
    
    async def open_position(self, symbol: str, side: str, entry_price: Decimal,
                           size: Decimal, strategy: str = "unknown",
                           stop_loss: Optional[Decimal] = None,
                           take_profit: Optional[Decimal] = None) -> Optional[ManagedPosition]:
        """
        Open a new position
        
        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            entry_price: Entry price
            size: Position size
            strategy: Strategy name
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            ManagedPosition object or None if failed
        """
        try:
            # Check position limits
            if len(self.open_positions) >= self.max_positions:
                logger.warning(f"⚠️ Max positions limit reached ({self.max_positions})")
                return None
            
            # Check if position already exists for symbol
            if symbol in self.open_positions:
                logger.warning(f"⚠️ Position already exists for {symbol}")
                return None
            
            # Create position
            position_id = f"pos_{symbol}_{int(datetime.now().timestamp())}"
            
            position = ManagedPosition(
                position_id=position_id,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                size=size,
                entry_time=datetime.now(timezone.utc),
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy=strategy,
                current_price=entry_price
            )
            
            # Add to open positions
            self.open_positions[symbol] = position
            self.total_positions_opened += 1
            
            logger.info(f"📈 Position opened: {side.upper()} {size} {symbol} @ ${entry_price}")
            
            return position
            
        except Exception as e:
            logger.error(f"❌ Failed to open position: {e}")
            return None
    
    async def close_position(self, symbol: str, exit_price: Decimal,
                            reason: str = "manual") -> Optional[ManagedPosition]:
        """
        Close an open position
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            reason: Reason for closing
            
        Returns:
            Closed ManagedPosition or None
        """
        try:
            position = self.open_positions.get(symbol)
            
            if not position:
                logger.warning(f"⚠️ No open position found for {symbol}")
                return None
            
            # Close the position
            position.close(exit_price, reason)
            
            # Update statistics
            self.total_positions_closed += 1
            self.total_realized_pnl += position.realized_pnl
            self.total_fees += position.fees
            
            if position.realized_pnl > 0:
                self.winning_positions += 1
            else:
                self.losing_positions += 1
            
            # Record in account manager
            self.account_manager.record_trade(position.realized_pnl, position.fees)
            
            # Move to closed positions
            del self.open_positions[symbol]
            self.closed_positions.append(position)
            
            # Limit closed history
            if len(self.closed_positions) > self.max_closed_history:
                self.closed_positions.pop(0)
            
            logger.info(f"📉 Position closed: {symbol} - P&L: ${position.realized_pnl:.2f} ({reason})")
            
            return position
            
        except Exception as e:
            logger.error(f"❌ Failed to close position: {e}")
            return None
    
    async def update_positions(self):
        """Update all open positions with current prices"""
        try:
            if not self.open_positions:
                return
            
            # Get all positions from exchange
            exchange_positions = await self.client.get_positions()
            
            # Create a map of exchange positions
            exchange_map = {pos.symbol: pos for pos in exchange_positions}
            
            # Update our tracked positions
            for symbol, position in list(self.open_positions.items()):
                if symbol in exchange_map:
                    exchange_pos = exchange_map[symbol]
                    position.update_price(exchange_pos.mark_price)
                    position.unrealized_pnl = exchange_pos.unrealized_pnl
                    
                    # Check if position was closed externally
                    if exchange_pos.size == 0:
                        logger.warning(f"⚠️ Position {symbol} closed externally")
                        await self.close_position(symbol, exchange_pos.mark_price, "external_close")
                else:
                    # Position not found on exchange - might be closed
                    logger.warning(f"⚠️ Position {symbol} not found on exchange")
            
        except Exception as e:
            logger.error(f"❌ Failed to update positions: {e}")
    
    async def check_stop_loss_take_profit(self):
        """Check all positions for stop loss and take profit triggers"""
        for symbol, position in list(self.open_positions.items()):
            if not position.current_price or position.current_price == 0:
                continue
            
            # Check stop loss
            if position.stop_loss:
                if position.side == 'long' and position.current_price <= position.stop_loss:
                    logger.info(f"🛑 Stop loss triggered for {symbol}")
                    await self.close_position(symbol, position.stop_loss, "stop_loss")
                elif position.side == 'short' and position.current_price >= position.stop_loss:
                    logger.info(f"🛑 Stop loss triggered for {symbol}")
                    await self.close_position(symbol, position.stop_loss, "stop_loss")
            
            # Check take profit
            if position.take_profit:
                if position.side == 'long' and position.current_price >= position.take_profit:
                    logger.info(f"💰 Take profit triggered for {symbol}")
                    await self.close_position(symbol, position.take_profit, "take_profit")
                elif position.side == 'short' and position.current_price <= position.take_profit:
                    logger.info(f"💰 Take profit triggered for {symbol}")
                    await self.close_position(symbol, position.take_profit, "take_profit")
    
    def get_position(self, symbol: str) -> Optional[ManagedPosition]:
        """Get position by symbol"""
        return self.open_positions.get(symbol)
    
    def get_all_positions(self) -> List[ManagedPosition]:
        """Get all open positions"""
        return list(self.open_positions.values())
    
    def get_total_exposure(self) -> Decimal:
        """Calculate total position exposure"""
        total = Decimal('0')
        for position in self.open_positions.values():
            total += position.entry_price * position.size
        return total
    
    def get_total_unrealized_pnl(self) -> Decimal:
        """Calculate total unrealized P&L"""
        total = Decimal('0')
        for position in self.open_positions.values():
            total += position.unrealized_pnl
        return total
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get position statistics"""
        win_rate = (self.winning_positions / self.total_positions_closed * 100) if self.total_positions_closed > 0 else 0
        
        avg_win = Decimal('0')
        avg_loss = Decimal('0')
        
        if self.winning_positions > 0:
            wins = [p.realized_pnl for p in self.closed_positions if p.realized_pnl > 0]
            avg_win = sum(wins) / len(wins) if wins else Decimal('0')
        
        if self.losing_positions > 0:
            losses = [abs(p.realized_pnl) for p in self.closed_positions if p.realized_pnl < 0]
            avg_loss = sum(losses) / len(losses) if losses else Decimal('0')
        
        profit_factor = abs(avg_win / avg_loss) if avg_loss > 0 else Decimal('0')
        
        return {
            'open_positions': len(self.open_positions),
            'total_opened': self.total_positions_opened,
            'total_closed': self.total_positions_closed,
            'winning_positions': self.winning_positions,
            'losing_positions': self.losing_positions,
            'win_rate': float(win_rate),
            'total_realized_pnl': float(self.total_realized_pnl),
            'total_unrealized_pnl': float(self.get_total_unrealized_pnl()),
            'total_fees': float(self.total_fees),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'total_exposure': float(self.get_total_exposure()),
            'largest_win': float(max((p.realized_pnl for p in self.closed_positions), default=0)),
            'largest_loss': float(min((p.realized_pnl for p in self.closed_positions), default=0))
        }
    
    def get_position_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all open positions"""
        return [
            {
                'symbol': p.symbol,
                'side': p.side,
                'size': float(p.size),
                'entry_price': float(p.entry_price),
                'current_price': float(p.current_price),
                'unrealized_pnl': float(p.unrealized_pnl),
                'unrealized_pnl_pct': float(p.unrealized_pnl_pct),
                'duration': str(datetime.now(timezone.utc) - p.entry_time),
                'strategy': p.strategy
            }
            for p in self.open_positions.values()
        ]
