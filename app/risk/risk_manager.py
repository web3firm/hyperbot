"""
Risk Manager
Multi-layer risk management with kill switches and monitoring
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(Enum):
    """Types of risk events"""
    DRAWDOWN = "drawdown"
    LEVERAGE = "leverage"
    POSITION_SIZE = "position_size"
    CORRELATION = "correlation"
    MARKET_CONDITIONS = "market_conditions"
    EXECUTION = "execution"
    CONNECTIVITY = "connectivity"
    ACCOUNT = "account"


@dataclass
class RiskEvent:
    """Risk event data structure"""
    event_id: str
    risk_type: RiskType
    level: RiskLevel
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class RiskLimits:
    """Risk limit configuration"""
    max_drawdown_pct: float
    max_daily_loss_pct: float
    max_leverage: float
    max_position_size_pct: float
    max_positions: int
    max_correlation_exposure: float
    stop_loss_pct: float
    take_profit_pct: float
    
    # Kill switch triggers
    critical_drawdown_pct: float
    emergency_loss_amount: Decimal
    max_consecutive_losses: int
    
    # Market condition limits
    max_volatility_pct: float
    min_liquidity_threshold: Decimal
    max_spread_pct: float


@dataclass
class PositionRisk:
    """Individual position risk assessment"""
    symbol: str
    current_pnl: Decimal
    current_pnl_pct: float
    unrealized_risk: Decimal
    time_in_position: timedelta
    stop_loss_distance: Optional[Decimal]
    risk_reward_ratio: Optional[float]
    position_size_pct: float
    leverage: float
    risk_level: RiskLevel


class RiskManager:
    """
    Enterprise risk management system with multiple safety layers
    """
    
    def __init__(self, portfolio_manager, exchange_client, config: Dict[str, Any]):
        """
        Initialize risk manager
        
        Args:
            portfolio_manager: Portfolio manager instance
            exchange_client: Exchange client
            config: Risk management configuration
        """
        self.portfolio_manager = portfolio_manager
        self.client = exchange_client
        self.config = config
        
        # Risk limits
        self.limits = self._load_risk_limits(config)
        
        # Risk state
        self.risk_events: List[RiskEvent] = []
        self.active_risks: Dict[str, RiskEvent] = {}
        self.kill_switch_active = False
        self.trading_paused = False
        
        # Performance tracking
        self.daily_start_equity = None
        self.daily_losses = Decimal('0')
        self.consecutive_losses = 0
        self.last_loss_check = datetime.now(timezone.utc).date()
        
        # Risk callbacks
        self.risk_callbacks: Dict[RiskLevel, List[Callable]] = {
            RiskLevel.LOW: [],
            RiskLevel.MEDIUM: [],
            RiskLevel.HIGH: [],
            RiskLevel.CRITICAL: []
        }
        
        # Monitoring intervals
        self.check_interval = 10  # seconds
        self.risk_monitor_task = None
        
        logger.info("🛡️ Risk Manager initialized")

    def _load_risk_limits(self, config: Dict[str, Any]) -> RiskLimits:
        """Load risk limits from configuration"""
        risk_config = config.get('risk_management', {})
        
        return RiskLimits(
            max_drawdown_pct=risk_config.get('max_drawdown_pct', 10.0),
            max_daily_loss_pct=risk_config.get('max_daily_loss_pct', 5.0),
            max_leverage=risk_config.get('max_leverage', 10.0),
            max_position_size_pct=risk_config.get('max_position_size_pct', 20.0),
            max_positions=risk_config.get('max_positions', 5),
            max_correlation_exposure=risk_config.get('max_correlation_exposure', 50.0),
            stop_loss_pct=risk_config.get('stop_loss_pct', 2.0),
            take_profit_pct=risk_config.get('take_profit_pct', 4.0),
            critical_drawdown_pct=risk_config.get('critical_drawdown_pct', 15.0),
            emergency_loss_amount=Decimal(str(risk_config.get('emergency_loss_amount', 1000))),
            max_consecutive_losses=risk_config.get('max_consecutive_losses', 5),
            max_volatility_pct=risk_config.get('max_volatility_pct', 20.0),
            min_liquidity_threshold=Decimal(str(risk_config.get('min_liquidity_threshold', 10000))),
            max_spread_pct=risk_config.get('max_spread_pct', 1.0)
        )

    async def start_monitoring(self):
        """Start the risk monitoring background task"""
        if self.risk_monitor_task:
            return
        
        self.risk_monitor_task = asyncio.create_task(self._risk_monitor_loop())
        logger.info("🔍 Risk monitoring started")

    async def stop_monitoring(self):
        """Stop the risk monitoring"""
        if self.risk_monitor_task:
            self.risk_monitor_task.cancel()
            self.risk_monitor_task = None
        logger.info("⏹️ Risk monitoring stopped")

    async def _risk_monitor_loop(self):
        """Background risk monitoring loop"""
        try:
            while True:
                await self._perform_risk_checks()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("Risk monitoring loop cancelled")
        except Exception as e:
            logger.error(f"❌ Risk monitoring error: {e}")

    async def _perform_risk_checks(self):
        """Perform comprehensive risk checks"""
        try:
            # Update portfolio state
            await self.portfolio_manager.update_portfolio_state()
            
            # Check daily loss reset
            await self._check_daily_reset()
            
            # Perform all risk checks
            await asyncio.gather(
                self._check_drawdown_risk(),
                self._check_leverage_risk(),
                self._check_position_risks(),
                self._check_daily_loss_risk(),
                self._check_correlation_risk(),
                self._check_connectivity_risk(),
                return_exceptions=True
            )
            
            # Process risk events
            await self._process_risk_events()
            
        except Exception as e:
            logger.error(f"❌ Risk check error: {e}")

    async def _check_daily_reset(self):
        """Reset daily counters if new day"""
        today = datetime.now(timezone.utc).date()
        
        if today != self.last_loss_check:
            # New day - reset daily counters
            self.daily_losses = Decimal('0')
            if self.portfolio_manager.current_balance:
                self.daily_start_equity = self.portfolio_manager.current_balance.equity
            
            self.last_loss_check = today
            logger.info(f"📅 Daily risk counters reset for {today}")

    async def _check_drawdown_risk(self):
        """Check portfolio drawdown risk"""
        try:
            if not self.portfolio_manager.current_balance or not self.portfolio_manager.peak_equity:
                return
            
            current_equity = self.portfolio_manager.current_balance.equity
            peak_equity = self.portfolio_manager.peak_equity
            
            # Calculate current drawdown
            drawdown_pct = float((peak_equity - current_equity) / peak_equity * 100)
            
            # Determine risk level
            if drawdown_pct >= self.limits.critical_drawdown_pct:
                await self._create_risk_event(
                    RiskType.DRAWDOWN,
                    RiskLevel.CRITICAL,
                    f"Critical drawdown reached: {drawdown_pct:.1f}%",
                    {
                        'drawdown_pct': drawdown_pct,
                        'current_equity': float(current_equity),
                        'peak_equity': float(peak_equity),
                        'limit': self.limits.critical_drawdown_pct
                    }
                )
            elif drawdown_pct >= self.limits.max_drawdown_pct:
                await self._create_risk_event(
                    RiskType.DRAWDOWN,
                    RiskLevel.HIGH,
                    f"Maximum drawdown exceeded: {drawdown_pct:.1f}%",
                    {
                        'drawdown_pct': drawdown_pct,
                        'current_equity': float(current_equity),
                        'peak_equity': float(peak_equity),
                        'limit': self.limits.max_drawdown_pct
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ Drawdown risk check error: {e}")

    async def _check_leverage_risk(self):
        """Check portfolio leverage risk"""
        try:
            if not self.portfolio_manager.current_balance:
                return
            
            # Calculate current leverage
            total_exposure = sum(
                pos.size * pos.mark_price 
                for pos in self.portfolio_manager.current_positions
            )
            
            current_leverage = float(
                total_exposure / self.portfolio_manager.current_balance.equity
            ) if self.portfolio_manager.current_balance.equity > 0 else 0.0
            
            # Check leverage limits
            if current_leverage >= self.limits.max_leverage * 1.1:  # 110% of limit
                await self._create_risk_event(
                    RiskType.LEVERAGE,
                    RiskLevel.HIGH,
                    f"Leverage limit exceeded: {current_leverage:.1f}x",
                    {
                        'current_leverage': current_leverage,
                        'limit': self.limits.max_leverage,
                        'total_exposure': float(total_exposure),
                        'equity': float(self.portfolio_manager.current_balance.equity)
                    }
                )
            elif current_leverage >= self.limits.max_leverage * 0.9:  # 90% of limit
                await self._create_risk_event(
                    RiskType.LEVERAGE,
                    RiskLevel.MEDIUM,
                    f"Leverage approaching limit: {current_leverage:.1f}x",
                    {
                        'current_leverage': current_leverage,
                        'limit': self.limits.max_leverage,
                        'total_exposure': float(total_exposure),
                        'equity': float(self.portfolio_manager.current_balance.equity)
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ Leverage risk check error: {e}")

    async def _check_position_risks(self):
        """Check individual position risks"""
        try:
            if not self.portfolio_manager.current_positions:
                return
            
            for position in self.portfolio_manager.current_positions:
                risk_assessment = await self._assess_position_risk(position)
                
                if risk_assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    await self._create_risk_event(
                        RiskType.POSITION_SIZE,
                        risk_assessment.risk_level,
                        f"Position risk alert: {position.symbol}",
                        {
                            'symbol': position.symbol,
                            'current_pnl': float(risk_assessment.current_pnl),
                            'current_pnl_pct': risk_assessment.current_pnl_pct,
                            'position_size_pct': risk_assessment.position_size_pct,
                            'leverage': risk_assessment.leverage,
                            'time_in_position': str(risk_assessment.time_in_position)
                        }
                    )
            
        except Exception as e:
            logger.error(f"❌ Position risk check error: {e}")

    async def _assess_position_risk(self, position) -> PositionRisk:
        """Assess risk for individual position"""
        # Calculate current P&L percentage
        pnl_pct = 0.0
        if position.entry_price > 0:
            if position.side == 'long':
                pnl_pct = float((position.mark_price - position.entry_price) / position.entry_price * 100)
            else:
                pnl_pct = float((position.entry_price - position.mark_price) / position.entry_price * 100)
        
        # Calculate position size as percentage of equity
        if self.portfolio_manager.current_balance:
            position_value = position.size * position.mark_price
            position_size_pct = float(position_value / self.portfolio_manager.current_balance.equity * 100)
        else:
            position_size_pct = 0.0
        
        # Calculate time in position
        time_in_position = datetime.now(timezone.utc) - position.timestamp
        
        # Determine risk level
        risk_level = RiskLevel.LOW
        
        # Check for critical losses
        if pnl_pct <= -self.limits.stop_loss_pct * 1.5:
            risk_level = RiskLevel.CRITICAL
        elif pnl_pct <= -self.limits.stop_loss_pct:
            risk_level = RiskLevel.HIGH
        elif position_size_pct > self.limits.max_position_size_pct:
            risk_level = RiskLevel.MEDIUM
        elif float(position.leverage) > self.limits.max_leverage:
            risk_level = RiskLevel.HIGH
        
        return PositionRisk(
            symbol=position.symbol,
            current_pnl=position.unrealized_pnl,
            current_pnl_pct=pnl_pct,
            unrealized_risk=position_value * Decimal(self.limits.stop_loss_pct / 100),
            time_in_position=time_in_position,
            stop_loss_distance=None,  # TODO: Calculate from strategy
            risk_reward_ratio=None,   # TODO: Calculate from strategy
            position_size_pct=position_size_pct,
            leverage=float(position.leverage),
            risk_level=risk_level
        )

    async def _check_daily_loss_risk(self):
        """Check daily loss limits"""
        try:
            if not self.portfolio_manager.current_balance or not self.daily_start_equity:
                return
            
            current_equity = self.portfolio_manager.current_balance.equity
            daily_pnl = current_equity - self.daily_start_equity
            daily_loss_pct = float(abs(daily_pnl) / self.daily_start_equity * 100) if daily_pnl < 0 else 0.0
            
            # Check daily loss limit
            if daily_loss_pct >= self.limits.max_daily_loss_pct:
                await self._create_risk_event(
                    RiskType.DRAWDOWN,
                    RiskLevel.CRITICAL,
                    f"Daily loss limit exceeded: {daily_loss_pct:.1f}%",
                    {
                        'daily_loss_pct': daily_loss_pct,
                        'daily_pnl': float(daily_pnl),
                        'start_equity': float(self.daily_start_equity),
                        'current_equity': float(current_equity),
                        'limit': self.limits.max_daily_loss_pct
                    }
                )
            
            # Check emergency loss amount
            if abs(daily_pnl) >= self.limits.emergency_loss_amount and daily_pnl < 0:
                await self._create_risk_event(
                    RiskType.DRAWDOWN,
                    RiskLevel.CRITICAL,
                    f"Emergency loss amount reached: ${daily_pnl:.2f}",
                    {
                        'daily_pnl': float(daily_pnl),
                        'emergency_limit': float(self.limits.emergency_loss_amount)
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ Daily loss risk check error: {e}")

    async def _check_correlation_risk(self):
        """Check portfolio correlation and concentration risk"""
        try:
            if not self.portfolio_manager.current_positions:
                return
            
            # For now, simple check - count positions in same asset class
            # TODO: Implement proper correlation analysis
            
            position_count = len(self.portfolio_manager.current_positions)
            
            if position_count >= self.limits.max_positions:
                await self._create_risk_event(
                    RiskType.CORRELATION,
                    RiskLevel.MEDIUM,
                    f"Maximum position count reached: {position_count}",
                    {
                        'position_count': position_count,
                        'limit': self.limits.max_positions
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ Correlation risk check error: {e}")

    async def _check_connectivity_risk(self):
        """Check exchange connectivity and market conditions"""
        try:
            # Check exchange connection
            connection_status = self.client.get_connection_status()
            
            if not connection_status.get('connected', False):
                await self._create_risk_event(
                    RiskType.CONNECTIVITY,
                    RiskLevel.HIGH,
                    "Exchange connection lost",
                    {'connection_status': connection_status}
                )
            
            # Check last message time (if WebSocket is available)
            last_request_time = connection_status.get('last_request_time', 0)
            if last_request_time > 0:
                time_since_last = time.time() - last_request_time
                if time_since_last > 60:  # No activity for 1 minute
                    await self._create_risk_event(
                        RiskType.CONNECTIVITY,
                        RiskLevel.MEDIUM,
                        f"No exchange activity for {time_since_last:.0f} seconds",
                        {'seconds_since_activity': time_since_last}
                    )
            
        except Exception as e:
            logger.error(f"❌ Connectivity risk check error: {e}")

    async def _create_risk_event(
        self,
        risk_type: RiskType,
        level: RiskLevel,
        message: str,
        details: Dict[str, Any]
    ):
        """Create and process a new risk event"""
        event_id = f"{risk_type.value}_{level.value}_{int(datetime.now(timezone.utc).timestamp())}"
        
        # Check if similar event already exists
        existing_key = f"{risk_type.value}_{level.value}"
        if existing_key in self.active_risks:
            # Update existing event
            existing_event = self.active_risks[existing_key]
            existing_event.details.update(details)
            existing_event.timestamp = datetime.now(timezone.utc)
            return
        
        # Create new risk event
        event = RiskEvent(
            event_id=event_id,
            risk_type=risk_type,
            level=level,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.risk_events.append(event)
        self.active_risks[existing_key] = event
        
        # Log the event
        if level == RiskLevel.CRITICAL:
            logger.critical(f"🚨 CRITICAL RISK: {message}")
        elif level == RiskLevel.HIGH:
            logger.error(f"🔴 HIGH RISK: {message}")
        elif level == RiskLevel.MEDIUM:
            logger.warning(f"🟡 MEDIUM RISK: {message}")
        else:
            logger.info(f"🔵 LOW RISK: {message}")

    async def _process_risk_events(self):
        """Process active risk events and take appropriate actions"""
        critical_events = [
            event for event in self.active_risks.values()
            if event.level == RiskLevel.CRITICAL and not event.acknowledged
        ]
        
        if critical_events:
            await self._handle_critical_risks(critical_events)
        
        # Call registered callbacks
        for event in self.active_risks.values():
            if not event.acknowledged and event.level in self.risk_callbacks:
                for callback in self.risk_callbacks[event.level]:
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"❌ Risk callback error: {e}")

    async def _handle_critical_risks(self, events: List[RiskEvent]):
        """Handle critical risk events with emergency actions"""
        logger.critical(f"🚨 CRITICAL RISK DETECTED: {len(events)} events")
        
        # Activate kill switch if not already active
        if not self.kill_switch_active:
            await self.activate_kill_switch("Critical risk events detected")
        
        # Acknowledge events
        for event in events:
            event.acknowledged = True

    async def activate_kill_switch(self, reason: str):
        """Activate emergency kill switch"""
        if self.kill_switch_active:
            return
        
        self.kill_switch_active = True
        self.trading_paused = True
        
        logger.critical(f"🚨 KILL SWITCH ACTIVATED: {reason}")
        
        try:
            # Emergency portfolio shutdown
            await self.portfolio_manager.emergency_shutdown(reason)
            
            # Create critical risk event
            await self._create_risk_event(
                RiskType.ACCOUNT,
                RiskLevel.CRITICAL,
                f"Kill switch activated: {reason}",
                {'reason': reason, 'timestamp': datetime.now(timezone.utc).isoformat()}
            )
            
        except Exception as e:
            logger.critical(f"🚨 KILL SWITCH ERROR: {e}")

    async def deactivate_kill_switch(self, reason: str):
        """Deactivate kill switch (manual intervention required)"""
        if not self.kill_switch_active:
            return
        
        logger.warning(f"⚠️ Kill switch deactivated: {reason}")
        
        self.kill_switch_active = False
        self.trading_paused = False
        
        # Clear acknowledged risk events
        self.active_risks = {
            k: v for k, v in self.active_risks.items()
            if not v.acknowledged
        }

    def pause_trading(self, reason: str):
        """Pause trading without full kill switch"""
        self.trading_paused = True
        logger.warning(f"⏸️ Trading paused: {reason}")

    def resume_trading(self, reason: str):
        """Resume trading"""
        if not self.kill_switch_active:
            self.trading_paused = False
            logger.info(f"▶️ Trading resumed: {reason}")

    async def validate_order(
        self,
        symbol: str,
        side: str,
        size: Decimal,
        price: Decimal
    ) -> Tuple[bool, str]:
        """
        Validate order against risk limits
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Order size
            price: Order price
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check if trading is paused or kill switch is active
        if self.kill_switch_active:
            return False, "Kill switch is active"
        
        if self.trading_paused:
            return False, "Trading is paused"
        
        # Check position count limit
        current_position_count = len(self.portfolio_manager.current_positions)
        existing_position = any(pos.symbol == symbol for pos in self.portfolio_manager.current_positions)
        
        if not existing_position and current_position_count >= self.limits.max_positions:
            return False, f"Position limit reached ({self.limits.max_positions})"
        
        # Check portfolio leverage
        if self.portfolio_manager.current_balance:
            position_value = size * price
            current_exposure = sum(
                pos.size * pos.mark_price 
                for pos in self.portfolio_manager.current_positions
            )
            new_exposure = current_exposure + position_value
            new_leverage = float(new_exposure / self.portfolio_manager.current_balance.equity)
            
            if new_leverage > self.limits.max_leverage:
                return False, f"Leverage limit exceeded: {new_leverage:.1f}x > {self.limits.max_leverage}x"
        
        # Check position size limit
        if self.portfolio_manager.current_balance:
            position_size_pct = float(position_value / self.portfolio_manager.current_balance.equity * 100)
            if position_size_pct > self.limits.max_position_size_pct:
                return False, f"Position size limit exceeded: {position_size_pct:.1f}% > {self.limits.max_position_size_pct}%"
        
        return True, "Order validated"

    def add_risk_callback(self, level: RiskLevel, callback: Callable):
        """Add a callback for risk events of specific level"""
        self.risk_callbacks[level].append(callback)

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        # Count events by level
        event_counts = {level.value: 0 for level in RiskLevel}
        for event in self.active_risks.values():
            event_counts[event.level.value] += 1
        
        # Calculate risk score (0-100)
        risk_score = 0
        risk_score += event_counts['critical'] * 40
        risk_score += event_counts['high'] * 20
        risk_score += event_counts['medium'] * 10
        risk_score += event_counts['low'] * 5
        risk_score = min(risk_score, 100)
        
        # Overall risk status
        if risk_score >= 80:
            risk_status = "CRITICAL"
        elif risk_score >= 60:
            risk_status = "HIGH"
        elif risk_score >= 30:
            risk_status = "MEDIUM"
        else:
            risk_status = "LOW"
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'risk_status': risk_status,
            'risk_score': risk_score,
            'kill_switch_active': self.kill_switch_active,
            'trading_paused': self.trading_paused,
            'active_events': event_counts,
            'total_events': len(self.risk_events),
            'consecutive_losses': self.consecutive_losses,
            'daily_loss_amount': float(self.daily_losses),
            'limits': {
                'max_drawdown_pct': self.limits.max_drawdown_pct,
                'max_daily_loss_pct': self.limits.max_daily_loss_pct,
                'max_leverage': self.limits.max_leverage,
                'max_positions': self.limits.max_positions,
                'stop_loss_pct': self.limits.stop_loss_pct
            }
        }

    def get_active_risks(self) -> List[Dict[str, Any]]:
        """Get list of active risk events"""
        return [
            {
                'event_id': event.event_id,
                'risk_type': event.risk_type.value,
                'level': event.level.value,
                'message': event.message,
                'details': event.details,
                'timestamp': event.timestamp.isoformat(),
                'acknowledged': event.acknowledged
            }
            for event in self.active_risks.values()
        ]

    async def acknowledge_risk(self, event_id: str, user: str = "system"):
        """Acknowledge a risk event"""
        for event in self.active_risks.values():
            if event.event_id == event_id:
                event.acknowledged = True
                logger.info(f"✅ Risk event acknowledged by {user}: {event.message}")
                break

    async def resolve_risk(self, event_id: str, user: str = "system"):
        """Resolve a risk event"""
        keys_to_remove = []
        for key, event in self.active_risks.items():
            if event.event_id == event_id:
                event.resolved = True
                keys_to_remove.append(key)
                logger.info(f"✅ Risk event resolved by {user}: {event.message}")
        
        # Remove resolved events
        for key in keys_to_remove:
            del self.active_risks[key]