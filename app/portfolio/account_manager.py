"""
Account Manager - Real-time account state tracking and management
Enterprise-grade account monitoring with P&L tracking and balance management
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AccountSnapshot:
    """Account state snapshot"""
    timestamp: datetime
    equity: Decimal
    available_balance: Decimal
    margin_used: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    positions_value: Decimal
    leverage: Decimal


class AccountManager:
    """
    Enterprise account manager for real-time balance and P&L tracking
    """
    
    def __init__(self, client):
        """
        Initialize account manager
        
        Args:
            client: HyperLiquidClient instance
        """
        self.client = client
        
        # Current state
        self.current_equity = Decimal('0')
        self.current_balance = Decimal('0')
        self.margin_used = Decimal('0')
        self.unrealized_pnl = Decimal('0')
        self.realized_pnl = Decimal('0')
        
        # Historical tracking
        self.snapshots: List[AccountSnapshot] = []
        self.max_snapshots = 1000
        
        # Peak tracking
        self.peak_equity = Decimal('0')
        self.peak_timestamp = None
        self.initial_equity = Decimal('0')
        
        # Session tracking
        self.session_start_equity = Decimal('0')
        self.session_pnl = Decimal('0')
        self.session_trades = 0
        self.session_fees = Decimal('0')
        
        # Update tracking
        self.last_update = None
        self.update_count = 0
        
        # Auto-update task
        self.update_task = None
        self.is_running = False
        self.update_interval = 5  # seconds
        
        logger.info("💰 Account Manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize account manager with current state"""
        try:
            # Get initial account state
            account_state = await self.client.get_account_state()
            
            self.current_equity = account_state.equity
            self.current_balance = account_state.available_margin
            self.margin_used = account_state.margin_used
            self.unrealized_pnl = account_state.unrealized_pnl
            
            # Set initial values
            self.initial_equity = self.current_equity
            self.session_start_equity = self.current_equity
            self.peak_equity = self.current_equity
            self.peak_timestamp = datetime.now(timezone.utc)
            
            # Create initial snapshot
            await self._create_snapshot()
            
            logger.info(f"✅ Account initialized - Equity: ${self.current_equity:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize account: {e}")
            return False
    
    async def start_auto_update(self):
        """Start automatic account updates"""
        if self.is_running:
            return
        
        self.is_running = True
        self.update_task = asyncio.create_task(self._update_loop())
        logger.info("🔄 Auto-update started")
    
    async def stop_auto_update(self):
        """Stop automatic account updates"""
        self.is_running = False
        if self.update_task:
            self.update_task.cancel()
        logger.info("🛑 Auto-update stopped")
    
    async def _update_loop(self):
        """Background loop for account updates"""
        while self.is_running:
            try:
                await self.update_account()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Update loop error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def update_account(self) -> bool:
        """
        Update account state from exchange
        
        Returns:
            True if update successful
        """
        try:
            # Get current account state
            account_state = await self.client.get_account_state()
            
            # Store previous equity for P&L calculation
            prev_equity = self.current_equity
            
            # Update current state
            self.current_equity = account_state.equity
            self.current_balance = account_state.available_margin
            self.margin_used = account_state.margin_used
            self.unrealized_pnl = account_state.unrealized_pnl
            
            # Calculate session P&L
            self.session_pnl = self.current_equity - self.session_start_equity
            
            # Update peak if new high
            if self.current_equity > self.peak_equity:
                self.peak_equity = self.current_equity
                self.peak_timestamp = datetime.now(timezone.utc)
            
            # Create snapshot
            await self._create_snapshot()
            
            self.last_update = datetime.now(timezone.utc)
            self.update_count += 1
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update account: {e}")
            return False
    
    async def _create_snapshot(self):
        """Create account snapshot"""
        snapshot = AccountSnapshot(
            timestamp=datetime.now(timezone.utc),
            equity=self.current_equity,
            available_balance=self.current_balance,
            margin_used=self.margin_used,
            unrealized_pnl=self.unrealized_pnl,
            realized_pnl=self.realized_pnl,
            total_pnl=self.session_pnl,
            positions_value=self.margin_used * Decimal('5'),  # Approximate
            leverage=self.margin_used / self.current_equity if self.current_equity > 0 else Decimal('0')
        )
        
        self.snapshots.append(snapshot)
        
        # Limit snapshot history
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)
    
    def record_trade(self, pnl: Decimal, fees: Decimal = Decimal('0')):
        """
        Record a completed trade
        
        Args:
            pnl: Trade P&L
            fees: Trading fees
        """
        self.realized_pnl += pnl
        self.session_pnl += pnl
        self.session_fees += fees
        self.session_trades += 1
        
        logger.info(f"📝 Trade recorded - P&L: ${pnl:.2f}, Fees: ${fees:.4f}")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current account state"""
        return {
            'equity': float(self.current_equity),
            'available_balance': float(self.current_balance),
            'margin_used': float(self.margin_used),
            'unrealized_pnl': float(self.unrealized_pnl),
            'realized_pnl': float(self.realized_pnl),
            'session_pnl': float(self.session_pnl),
            'session_pnl_pct': float(self.session_pnl / self.session_start_equity * 100) if self.session_start_equity > 0 else 0,
            'total_pnl': float(self.current_equity - self.initial_equity),
            'total_pnl_pct': float((self.current_equity - self.initial_equity) / self.initial_equity * 100) if self.initial_equity > 0 else 0,
            'peak_equity': float(self.peak_equity),
            'drawdown': float((self.peak_equity - self.current_equity) / self.peak_equity * 100) if self.peak_equity > 0 else 0,
            'session_trades': self.session_trades,
            'session_fees': float(self.session_fees),
            'leverage': float(self.margin_used / self.current_equity) if self.current_equity > 0 else 0,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if len(self.snapshots) < 2:
            return {}
        
        # Calculate returns over time
        first_snapshot = self.snapshots[0]
        last_snapshot = self.snapshots[-1]
        
        time_elapsed = (last_snapshot.timestamp - first_snapshot.timestamp).total_seconds()
        hours_elapsed = time_elapsed / 3600
        
        total_return = float((last_snapshot.equity - first_snapshot.equity) / first_snapshot.equity * 100)
        
        return {
            'total_return_pct': total_return,
            'hourly_return_pct': total_return / hours_elapsed if hours_elapsed > 0 else 0,
            'max_equity': float(self.peak_equity),
            'min_equity': float(min(s.equity for s in self.snapshots)),
            'avg_equity': float(sum(s.equity for s in self.snapshots) / len(self.snapshots)),
            'max_drawdown': float(max((self.peak_equity - s.equity) / self.peak_equity * 100 for s in self.snapshots)),
            'trades_count': self.session_trades,
            'avg_pnl_per_trade': float(self.session_pnl / self.session_trades) if self.session_trades > 0 else 0,
            'total_fees': float(self.session_fees),
            'snapshots_count': len(self.snapshots),
            'hours_tracked': hours_elapsed
        }
    
    def can_trade(self, required_margin: Decimal) -> tuple[bool, Optional[str]]:
        """
        Check if account can take a trade
        
        Args:
            required_margin: Required margin for the trade
            
        Returns:
            (can_trade, reason)
        """
        if required_margin > self.current_balance:
            return False, f"Insufficient balance: need ${required_margin:.2f}, have ${self.current_balance:.2f}"
        
        if self.current_balance < self.current_equity * Decimal('0.1'):
            return False, "Available balance below 10% of equity - safety limit"
        
        return True, None
    
    def reset_session(self):
        """Reset session statistics"""
        self.session_start_equity = self.current_equity
        self.session_pnl = Decimal('0')
        self.session_trades = 0
        self.session_fees = Decimal('0')
        logger.info("🔄 Session statistics reset")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Calculate risk metrics"""
        current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity * 100 if self.peak_equity > 0 else 0
        
        return {
            'current_drawdown_pct': float(current_drawdown),
            'peak_equity': float(self.peak_equity),
            'equity_from_peak': float(self.current_equity - self.peak_equity),
            'margin_utilization': float(self.margin_used / self.current_equity * 100) if self.current_equity > 0 else 0,
            'available_margin_pct': float(self.current_balance / self.current_equity * 100) if self.current_equity > 0 else 0,
            'risk_level': 'HIGH' if current_drawdown > 10 else 'MEDIUM' if current_drawdown > 5 else 'LOW'
        }
