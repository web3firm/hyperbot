"""
Metrics Dashboard - Real-time trading metrics and KPIs
Comprehensive performance tracking and system health monitoring
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Trading performance metrics"""
    # P&L metrics
    total_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    unrealized_pnl: Decimal = Decimal('0')
    session_pnl: Decimal = Decimal('0')
    
    # Return metrics
    total_return_pct: Decimal = Decimal('0')
    session_return_pct: Decimal = Decimal('0')
    
    # Risk metrics
    max_drawdown_pct: Decimal = Decimal('0')
    current_drawdown_pct: Decimal = Decimal('0')
    sharpe_ratio: Optional[Decimal] = None
    
    # Trade metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal = Decimal('0')
    profit_factor: Optional[Decimal] = None
    avg_win: Decimal = Decimal('0')
    avg_loss: Decimal = Decimal('0')
    
    # Position metrics
    open_positions: int = 0
    total_exposure: Decimal = Decimal('0')
    margin_used: Decimal = Decimal('0')
    margin_available: Decimal = Decimal('0')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pnl': {
                'total': float(self.total_pnl),
                'realized': float(self.realized_pnl),
                'unrealized': float(self.unrealized_pnl),
                'session': float(self.session_pnl)
            },
            'returns': {
                'total_pct': float(self.total_return_pct),
                'session_pct': float(self.session_return_pct)
            },
            'risk': {
                'max_drawdown_pct': float(self.max_drawdown_pct),
                'current_drawdown_pct': float(self.current_drawdown_pct),
                'sharpe_ratio': float(self.sharpe_ratio) if self.sharpe_ratio else None
            },
            'trades': {
                'total': self.total_trades,
                'winning': self.winning_trades,
                'losing': self.losing_trades,
                'win_rate': float(self.win_rate),
                'profit_factor': float(self.profit_factor) if self.profit_factor else None,
                'avg_win': float(self.avg_win),
                'avg_loss': float(self.avg_loss)
            },
            'positions': {
                'open': self.open_positions,
                'exposure': float(self.total_exposure),
                'margin_used': float(self.margin_used),
                'margin_available': float(self.margin_available)
            }
        }


@dataclass
class SystemHealth:
    """System health metrics"""
    uptime_seconds: int = 0
    is_connected: bool = False
    is_trading: bool = False
    kill_switch_active: bool = False
    risk_engine_enabled: bool = True
    drawdown_paused: bool = False
    
    # Component health
    websocket_healthy: bool = False
    order_router_healthy: bool = False
    
    # Error tracking
    errors_last_hour: int = 0
    errors_last_day: int = 0
    last_error_time: Optional[datetime] = None
    
    # Performance
    avg_order_latency_ms: Optional[float] = None
    api_calls_per_minute: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'uptime_seconds': self.uptime_seconds,
            'uptime_formatted': self._format_uptime(self.uptime_seconds),
            'status': {
                'connected': self.is_connected,
                'trading': self.is_trading,
                'kill_switch': self.kill_switch_active,
                'risk_engine': self.risk_engine_enabled,
                'drawdown_paused': self.drawdown_paused
            },
            'components': {
                'websocket': self.websocket_healthy,
                'order_router': self.order_router_healthy
            },
            'errors': {
                'last_hour': self.errors_last_hour,
                'last_day': self.errors_last_day,
                'last_error': self.last_error_time.isoformat() if self.last_error_time else None
            },
            'performance': {
                'avg_order_latency_ms': self.avg_order_latency_ms,
                'api_calls_per_minute': self.api_calls_per_minute
            }
        }
    
    @staticmethod
    def _format_uptime(seconds: int) -> str:
        """Format uptime in human-readable format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"


class MetricsDashboard:
    """
    Real-time metrics dashboard and KPI tracking
    """
    
    def __init__(self, account_manager, position_manager, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics dashboard
        
        Args:
            account_manager: AccountManager instance
            position_manager: PositionManager instance
            config: Configuration
        """
        self.account_manager = account_manager
        self.position_manager = position_manager
        
        cfg = config or {}
        
        # Dashboard state
        self.start_time = datetime.now(timezone.utc)
        
        # Metrics history
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = cfg.get('max_history', 1000)
        
        # Health monitoring
        self.system_health = SystemHealth()
        
        # Update interval
        self.update_interval_seconds = cfg.get('update_interval_seconds', 5)
        self.last_update = None
        
        logger.info("📊 Metrics Dashboard initialized")
    
    def update(self) -> PerformanceMetrics:
        """
        Update all metrics
        
        Returns:
            Current performance metrics
        """
        metrics = PerformanceMetrics()
        
        # Get account metrics
        account_perf = self.account_manager.get_performance_metrics()
        
        # P&L metrics
        metrics.total_pnl = account_perf['total_pnl']
        metrics.realized_pnl = account_perf['realized_pnl']
        metrics.unrealized_pnl = account_perf['unrealized_pnl']
        metrics.session_pnl = account_perf['session_pnl']
        
        # Return metrics
        metrics.total_return_pct = account_perf['total_return_pct']
        metrics.session_return_pct = account_perf['session_return_pct']
        
        # Risk metrics
        risk_metrics = self.account_manager.get_risk_metrics()
        metrics.max_drawdown_pct = risk_metrics['max_drawdown_pct']
        metrics.current_drawdown_pct = risk_metrics['drawdown_pct']
        
        # Trade metrics
        position_stats = self.position_manager.get_statistics()
        metrics.total_trades = position_stats['closed_positions']
        metrics.winning_trades = position_stats['winning_trades']
        metrics.losing_trades = position_stats['losing_trades']
        metrics.win_rate = position_stats['win_rate']
        metrics.profit_factor = position_stats['profit_factor']
        metrics.avg_win = position_stats['avg_win']
        metrics.avg_loss = position_stats['avg_loss']
        
        # Position metrics
        metrics.open_positions = len(self.position_manager.open_positions)
        metrics.total_exposure = self.position_manager.get_total_exposure()
        metrics.margin_used = self.account_manager.margin_used
        metrics.margin_available = self.account_manager.current_balance - self.account_manager.margin_used
        
        # Store in history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
        
        self.last_update = datetime.now(timezone.utc)
        
        return metrics
    
    def update_system_health(self, **kwargs):
        """
        Update system health metrics
        
        Args:
            **kwargs: Health parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.system_health, key):
                setattr(self.system_health, key, value)
        
        # Calculate uptime
        self.system_health.uptime_seconds = int((datetime.now(timezone.utc) - self.start_time).total_seconds())
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        metrics = self.update()
        return metrics.to_dict()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return self.system_health.to_dict()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive dashboard summary"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'performance': self.get_current_metrics(),
            'health': self.get_system_health(),
            'account': {
                'balance': float(self.account_manager.current_balance),
                'equity': float(self.account_manager.current_equity),
                'peak_equity': float(self.account_manager.peak_equity)
            }
        }
    
    def get_metrics_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get metrics history for specified time period
        
        Args:
            minutes: Number of minutes of history
            
        Returns:
            List of metrics dictionaries
        """
        if not self.metrics_history:
            return []
        
        # Calculate how many entries to return (based on update interval)
        entries = min(len(self.metrics_history), minutes * 60 // self.update_interval_seconds)
        
        recent = self.metrics_history[-entries:] if entries > 0 else []
        return [m.to_dict() for m in recent]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get high-level performance summary"""
        if not self.metrics_history:
            return {}
        
        latest = self.metrics_history[-1]
        
        return {
            'session': {
                'pnl': float(latest.session_pnl),
                'return_pct': float(latest.session_return_pct),
                'trades': latest.total_trades,
                'win_rate': float(latest.win_rate)
            },
            'current': {
                'positions': latest.open_positions,
                'exposure': float(latest.total_exposure),
                'drawdown_pct': float(latest.current_drawdown_pct)
            },
            'risk': {
                'max_drawdown_pct': float(latest.max_drawdown_pct),
                'margin_used_pct': float(latest.margin_used / (latest.margin_used + latest.margin_available) * 100) if (latest.margin_used + latest.margin_available) > 0 else 0
            }
        }
    
    def print_dashboard(self):
        """Print formatted dashboard to console"""
        metrics = self.update()
        health = self.system_health
        
        print("\n" + "="*60)
        print("📊 HYPERBOT DASHBOARD")
        print("="*60)
        
        # Performance section
        print("\n💰 PERFORMANCE")
        print(f"  Session P&L:     ${metrics.session_pnl:+.2f} ({metrics.session_return_pct:+.2f}%)")
        print(f"  Total P&L:       ${metrics.total_pnl:+.2f} ({metrics.total_return_pct:+.2f}%)")
        print(f"  Realized:        ${metrics.realized_pnl:+.2f}")
        print(f"  Unrealized:      ${metrics.unrealized_pnl:+.2f}")
        
        # Trades section
        print("\n📈 TRADES")
        print(f"  Total:           {metrics.total_trades}")
        print(f"  Win Rate:        {metrics.win_rate:.1f}% ({metrics.winning_trades}W / {metrics.losing_trades}L)")
        print(f"  Avg Win:         ${metrics.avg_win:.2f}")
        print(f"  Avg Loss:        ${metrics.avg_loss:.2f}")
        if metrics.profit_factor:
            print(f"  Profit Factor:   {metrics.profit_factor:.2f}")
        
        # Positions section
        print("\n📊 POSITIONS")
        print(f"  Open:            {metrics.open_positions}")
        print(f"  Exposure:        ${metrics.total_exposure:.2f}")
        print(f"  Margin Used:     ${metrics.margin_used:.2f}")
        print(f"  Margin Available: ${metrics.margin_available:.2f}")
        
        # Risk section
        print("\n⚠️  RISK")
        print(f"  Current Drawdown: {metrics.current_drawdown_pct:.2f}%")
        print(f"  Max Drawdown:     {metrics.max_drawdown_pct:.2f}%")
        
        # System health section
        print("\n🔧 SYSTEM HEALTH")
        print(f"  Uptime:          {health._format_uptime(health.uptime_seconds)}")
        print(f"  Connected:       {'✅' if health.is_connected else '❌'}")
        print(f"  Trading:         {'✅' if health.is_trading else '⏸️'}")
        print(f"  Kill Switch:     {'🚨 ACTIVE' if health.kill_switch_active else '✅ OK'}")
        print(f"  Risk Engine:     {'✅' if health.risk_engine_enabled else '⚠️ DISABLED'}")
        
        print("\n" + "="*60 + "\n")
