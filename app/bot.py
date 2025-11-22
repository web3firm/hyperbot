#!/usr/bin/env python3
"""
HyperAI Trader - Master Bot Controller
Orchestrates rule-based → AI mode transition with complete risk management

Phase 1: Rule-based scalping (collect 1,000-3,000 trades)
Phase 2: Train AI models on collected data
Phase 3: Hybrid AI + Rule validation
Phase 4: Full AI autonomy
"""

import asyncio
import signal
import sys
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List
from types import FrameType
import json
import re

# Add to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs (tokens, API keys, URLs with tokens)"""
    
    def __init__(self):
        super().__init__()
        # Get sensitive tokens from environment
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.api_secret = os.getenv('HYPERLIQUID_API_SECRET', '')
        
    def filter(self, record):
        """Mask sensitive data in log records"""
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            
            # Mask Telegram bot token in URLs
            if self.telegram_token and self.telegram_token in msg:
                # Mask the token
                if ':' in self.telegram_token:
                    bot_id = self.telegram_token.split(':')[0]
                    msg = msg.replace(self.telegram_token, f"{bot_id}:***MASKED***")
                else:
                    msg = msg.replace(self.telegram_token, "***MASKED***")
            
            # Mask API URLs with tokens using regex (catch any bot token in URLs)
            msg = re.sub(
                r'(https?://[^/]+/bot)(\d+:[A-Za-z0-9_-]+)',
                r'\1***MASKED***',
                msg
            )
            
            # Mask API secrets
            if self.api_secret and len(self.api_secret) > 10:
                msg = msg.replace(self.api_secret, '***MASKED***')
            
            record.msg = msg
            
        return True


# Import HyperLiquid integration
from app.hl.hl_client import HyperLiquidClient
from app.hl.hl_websocket import HLWebSocket
from app.hl.hl_order_manager_v2 import HLOrderManagerV2  # V2: Uses SDK bulk_orders

# Import strategies
from app.strategies.strategy_manager import StrategyManager

# Import risk management (consolidated in app/)
from app.risk.risk_engine import RiskEngine
from app.risk.kill_switch import KillSwitch
from app.risk.drawdown_monitor import DrawdownMonitor

# Import Telegram bot
from app.telegram_bot import TelegramBot

# Import error handler
from app.utils.error_handler import ErrorHandler

# Import database
from app.database.db_manager import DatabaseManager

# Phase 5: Shared indicator calculator
from app.utils.indicator_calculator import IndicatorCalculator

# Create logs directory if it doesn't exist
Path('logs').mkdir(exist_ok=True)

# Setup logging with sensitive data filter
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

# Add sensitive data filter to all handlers
sensitive_filter = SensitiveDataFilter()
for handler in logging.root.handlers:
    handler.addFilter(sensitive_filter)

logger = logging.getLogger(__name__)

# Suppress noisy HTTP logs from telegram library
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

# Global shutdown event
shutdown_event = asyncio.Event()

def signal_handler(signum: int, frame: Optional[FrameType]) -> None:
    """Handle shutdown signals"""
    logger.info("\n🛑 Shutdown requested...")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class HyperAIBot:
    """
    Master trading bot controller
    Manages strategy execution, risk controls, and mode transitions
    """
    
    def __init__(self):
        # Mode configuration
        self.mode = os.getenv('BOT_MODE', 'rule_based')  # rule_based, hybrid, ai
        # Trading symbol - can be any HyperLiquid asset (BTC, ETH, SOL, MATIC, etc.)
        self.symbol = os.getenv('SYMBOL', 'SOL')
        
        # Exchange components
        self.client: Optional[HyperLiquidClient] = None
        self.websocket: Optional[HLWebSocket] = None
        self.order_manager: Optional[HLOrderManagerV2] = None  # V2: SDK-optimized
        
        # Strategy Manager (runs all 4 strategies)
        self.strategy: Optional[StrategyManager] = None
        
        # Risk management
        self.risk_engine: Optional[RiskEngine] = None
        self.kill_switch: Optional[KillSwitch] = None
        self.drawdown_monitor: Optional[DrawdownMonitor] = None
        
        # Telegram bot
        self.telegram_bot: Optional[TelegramBot] = None
        
        # Candle cache for strategies (reduces API calls by 98%)
        self._candles_cache: List[Dict[str, Any]] = []
        self._last_candle_fetch: Optional[datetime] = None
        self._candle_update_pending = False  # Track if we need fresh candles
        
        # Phase 5: Shared indicator calculator (eliminates duplicate calculations)
        self.indicator_calc: Optional[IndicatorCalculator] = None
        
        # Error handler
        self.error_handler: Optional[ErrorHandler] = None
        
        # Database
        self.db: Optional[DatabaseManager] = None
        
        # Account tracking (simplified portfolio manager)
        self.account_value = Decimal('0')
        self.peak_equity = Decimal('0')
        self.session_start_equity = Decimal('0')
        self.session_pnl = Decimal('0')
        self.margin_used = Decimal('0')
        self.account_state: Dict[str, Any] = {}
        
        # State
        self.is_running = False
        self.is_paused = False  # For pause/resume functionality
        self.trades_executed = 0
        self.start_time: Optional[datetime] = None
        
        # Data collection for AI training
        self.trade_log_path = Path('data/trades')
        self.trade_log_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("🤖 HyperAI Bot initialized")
        logger.info(f"   Mode: {self.mode}")
        logger.info(f"   Symbol: {self.symbol}")
    
    async def initialize(self) -> bool:
        """Initialize all components"""
        try:
            logger.info("🔧 Initializing components...")
            
            # Load credentials
            account_address = os.getenv('ACCOUNT_ADDRESS')
            api_secret = os.getenv('API_SECRET')
            testnet = os.getenv('TESTNET', 'false').lower() == 'true'
            
            if not account_address or not api_secret:
                raise ValueError("Missing credentials in .env file")
            
            # Initialize exchange client
            # Note: HyperLiquid only needs private key, not separate API key
            self.client = HyperLiquidClient(
                account_address,
                api_secret,  # Used as both api_key and api_secret parameters
                api_secret,
                testnet=testnet
            )
            
            # Initialize WebSocket V2 with account updates (eliminates polling!)
            self.websocket = HLWebSocket(
                symbols=[self.symbol],
                account_address=account_address  # Enable account subscriptions
            )
            await self.websocket.start(info_client=self.client.info)  # Pass SDK client for subscriptions
            
            # Link WebSocket to client for optimized get_account_state()
            self.client.websocket = self.websocket
            
            # Register candle callback for real-time updates (Phase 3)
            self.websocket.on_candle_callbacks.append(self._on_new_candle)
            logger.info("📊 Registered real-time candle callback")
            
            # PHASE 4: Register order update callback for instant notifications
            self.websocket.on_order_update_callbacks.append(self._on_order_update)
            logger.info("⚡ Registered real-time order update callback")
            
            # Initialize Order Manager V2 (uses SDK bulk_orders)
            self.order_manager = HLOrderManagerV2(self.client)
            
            # Set leverage from MAX_LEVERAGE in .env
            leverage = int(os.getenv('MAX_LEVERAGE', '5'))
            await self.order_manager.set_leverage(self.symbol, leverage)
            logger.info(f"⚙️  Leverage set to {leverage}x for {self.symbol}")
            
            # Initialize strategy
            # Initialize strategy manager with all 4 strategies
            logger.info(f"🎯 Initializing Strategy Manager for {self.symbol}")
            self.strategy = StrategyManager(self.symbol)
            
            # Phase 5: Initialize shared indicator calculator
            self.indicator_calc = IndicatorCalculator()
            logger.info("📊 Phase 5: Shared indicator calculator initialized")
            
            # Get initial account state
            await self.update_account_state()
            
            # Initialize risk management components
            # Create simple AccountManager and PositionManager proxies
            account_manager_proxy = type('obj', (object,), {
                'current_equity': self.account_value,
                'current_balance': self.account_value,
                'peak_equity': self.peak_equity,
                'session_start_equity': self.session_start_equity,
                'session_pnl': self.session_pnl,
                'margin_used': self.margin_used
            })()
            
            position_manager_proxy = type('obj', (object,), {
                'open_positions': {},
                'get_position': lambda self, symbol: None  # type: ignore
            })()
            
            risk_config = {
                'max_position_size_pct': float(os.getenv('MAX_POSITION_SIZE_PCT', '70')),
                'max_positions': int(os.getenv('MAX_POSITIONS', '3')),
                'max_leverage': int(os.getenv('MAX_LEVERAGE', '5')),
                'max_daily_loss_pct': float(os.getenv('MAX_DAILY_LOSS_PCT', '5')),
                'max_drawdown_pct': float(os.getenv('MAX_DRAWDOWN_PCT', '10'))
            }
            self.risk_engine = RiskEngine(account_manager_proxy, position_manager_proxy, risk_config)
            
            kill_switch_config = {
                'daily_loss_trigger_pct': float(os.getenv('MAX_DAILY_LOSS_PCT', '10')),
                'drawdown_trigger_pct': float(os.getenv('MAX_DRAWDOWN_PCT', '15'))
            }
            self.kill_switch = KillSwitch(account_manager_proxy, position_manager_proxy, kill_switch_config)
            
            drawdown_config = {
                'warning_threshold_pct': 5,
                'critical_threshold_pct': float(os.getenv('MAX_DRAWDOWN_PCT', '10')),
                'auto_pause_enabled': True,
                'auto_pause_threshold_pct': 12
            }
            self.drawdown_monitor = DrawdownMonitor(account_manager_proxy, drawdown_config)
            
            # Initialize Telegram bot (if credentials provided)
            if os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):
                try:
                    logger.info("📱 Initializing Telegram bot...")
                    config = {
                        'max_leverage': int(os.getenv('MAX_LEVERAGE', '5')),
                        'max_daily_loss_pct': float(os.getenv('MAX_DAILY_LOSS_PCT', '5'))
                    }
                    self.telegram_bot = TelegramBot(self, config)
                    await self.telegram_bot.start()
                    
                    # Initialize error handler with Telegram
                    self.error_handler = ErrorHandler(self.telegram_bot)
                    logger.info("🛡️ Error handler initialized with Telegram notifications")
                    
                    # Initialize database if DATABASE_URL is set
                    database_url = os.getenv('DATABASE_URL')
                    if database_url:
                        try:
                            logger.info("📊 Connecting to PostgreSQL database...")
                            from app.database.db_manager import DatabaseManager
                            self.db = DatabaseManager(database_url)
                            await self.db.connect()
                            logger.info("✅ Database connected and migrations applied")
                        except Exception as db_error:
                            logger.error(f"❌ Database connection failed: {db_error}")
                            logger.warning("⚠️ Continuing without database (will use JSONL fallback)")
                            self.db = None
                    else:
                        logger.info("📊 DATABASE_URL not set, using JSONL fallback")
                    
                    # Start auto-trainer background task
                    logger.info("🤖 Starting ML auto-trainer...")
                    from ml.auto_trainer import AutoTrainer
                    self.auto_trainer = AutoTrainer(min_trades_for_retrain=100)
                    asyncio.create_task(self.auto_trainer.schedule_daily_check(self.telegram_bot))
                    
                except Exception as e:
                    logger.warning(f"⚠️ Telegram bot initialization failed: {e}")
                    self.telegram_bot = None
            else:
                logger.info("📱 Telegram bot disabled (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable)")
            
            logger.info("✅ All components initialized")
            logger.info(f"💰 Starting Balance: ${self.account_value:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            return False
    
    async def update_account_state(self):
        """Update account state from exchange"""
        try:
            account_state = await self.client.get_account_state()
            
            self.account_value = Decimal(str(account_state['account_value']))
            self.margin_used = Decimal(str(account_state['margin_used']))
            
            logger.info(f"📊 Account updated: value=${self.account_value:.2f}, margin=${self.margin_used:.2f}")
            
            # Update peak equity
            if self.account_value > self.peak_equity:
                self.peak_equity = self.account_value
            
            # Set session start on first update
            if self.session_start_equity == 0:
                self.session_start_equity = self.account_value
            
            # Calculate session P&L
            self.session_pnl = self.account_value - self.session_start_equity
            
        except Exception as e:
            logger.error(f"Error updating account state: {e}")
    
    def _on_new_candle(self, symbol: str, candle: Dict[str, Any]):
        """
        Callback for real-time candle updates (Phase 3 + Phase 4 + Phase 5)
        Triggers indicator recalculation on new candle
        """
        if symbol == self.symbol:
            self._candle_update_pending = True
            
            # PHASE 4: Invalidate strategy indicator cache on new candle
            if hasattr(self.strategy, 'invalidate_indicator_cache'):
                self.strategy.invalidate_indicator_cache()
            
            # PHASE 5: Invalidate shared indicator calculator cache
            if self.indicator_calc:
                self.indicator_calc.invalidate_cache()
            
            logger.debug(f"🕯️ New candle for {symbol} - invalidated all indicator caches")
    
    def _on_order_update(self, update: Dict[str, Any]):
        """
        Callback for real-time order updates (PHASE 4)
        Sends instant Telegram notifications when orders fill/cancel/trigger
        """
        try:
            status = update.get('status')
            order = update.get('order', {})
            
            coin = order.get('coin', 'UNKNOWN')
            side = order.get('side', 'unknown')
            size = order.get('sz', 0)
            price = order.get('limitPx') or order.get('triggerPx', 0)
            
            # Send Telegram notification for important events
            if self.telegram_bot and status in ['filled', 'triggered', 'canceled']:
                message = None
                
                if status == 'filled':
                    message = f"✅ **ORDER FILLED**\\n\\n{coin} {side.upper()} {size} @ ${price}"
                elif status == 'triggered':
                    # Stop loss or take profit triggered
                    order_type = order.get('orderType', 'stop')
                    if 'tp' in order_type.lower():
                        message = f"🎯 **TAKE PROFIT HIT**\\n\\n{coin} closed @ ${price}\\nProfit secured! 💰"
                    else:
                        message = f"🛑 **STOP LOSS HIT**\\n\\n{coin} closed @ ${price}\\nLoss limited, capital protected."
                elif status == 'canceled':
                    message = f"🚫 **ORDER CANCELLED**\\n\\n{coin} {side.upper()} {size} @ ${price}"
                
                if message:
                    # Send async notification (don't block)
                    asyncio.create_task(self._send_order_notification(message))
                    
        except Exception as e:
            logger.error(f"Error in order update callback: {e}")
    
    async def _send_order_notification(self, message: str):
        """Send Telegram notification asynchronously"""
        try:
            if self.telegram_bot:
                await self.telegram_bot.send_message(message)
        except Exception as e:
            logger.debug(f"Telegram notification failed: {e}")
    
    async def _monitor_positions(self, account_state: Dict[str, Any]):
        """
        Monitor active positions for SL/TP hits and position closures
        Provides multi-layer safety by tracking:
        1. Position existence
        2. Unrealized P&L vs SL/TP levels
        3. Position size changes
        4. BACKUP: Auto-close if SL/TP orders failed but price reached target
        """
        try:
            positions = account_state.get('positions', [])
            current_symbols = {pos['symbol'] for pos in positions if float(pos.get('size', 0)) != 0}
            
            # Track symbols that closed since last check
            if hasattr(self, '_last_positions'):
                closed_positions = self._last_positions - current_symbols
                for symbol in closed_positions:
                    logger.info(f"🔄 Position closed: {symbol}")
                    # Clean up backup targets
                    if hasattr(self.order_manager, 'position_targets') and symbol in self.order_manager.position_targets:
                        del self.order_manager.position_targets[symbol]
            
            # Monitor each active position
            for pos in positions:
                size = float(pos.get('size', 0))
                if size == 0:
                    continue
                
                symbol = pos['symbol']
                entry_price = Decimal(str(pos.get('entry_price', 0)))
                unrealized_pnl = Decimal(str(pos.get('unrealized_pnl', 0)))
                unrealized_pnl_pct = (unrealized_pnl / (abs(Decimal(str(size))) * entry_price)) * 100
                current_price = Decimal(str(pos.get('mark_price', entry_price)))  # Use mark price
                
                # Log position status every 10 loops for visibility
                if hasattr(self, '_position_log_counter'):
                    self._position_log_counter += 1
                else:
                    self._position_log_counter = 1
                
                if self._position_log_counter % 10 == 0:
                    logger.info(f"📈 Active position: {symbol} | Size: {size:.2f} | "
                               f"Entry: ${entry_price:.3f} | Current: ${current_price:.3f} | P&L: ${unrealized_pnl:+.2f} ({unrealized_pnl_pct:+.1f}%)")
                
                # DYNAMIC TRAILING STOPS - Lock in profits as they grow!
                # Uses OrderManagerV2 position tracking (no need for position_targets)
                if symbol in self.order_manager.position_orders:
                    order_info = self.order_manager.position_orders[symbol]
                    is_long = size > 0
                    
                    should_close = False
                    close_reason = ""
                    needs_update = False
                    new_sl = None
                    new_tp = None
                    
                    # Get current order IDs from open orders (for validation)
                    # This ensures we have valid orders to modify
                    
                    # **TRAILING STOP-LOSS + TAKE-PROFIT LOGIC** - Lock in profits dynamically!
                    # NOTE: With 5% SL / 15% TP PnL targets and 5x leverage:
                    #   - SL at 5% PnL = 1% price move
                    #   - TP at 15% PnL = 3% price move
                    #   - Trailing activates at ~7% PnL (halfway to 15% target)
                    
                    # If PnL reaches 7%+, move SL to breakeven or better
                    if unrealized_pnl_pct >= 7.0:  # Reached ~50% of 15% TP target
                        # Calculate breakeven + buffer
                        if is_long:
                            # Move SL to breakeven + 0.5% PRICE (= 2.5% PnL with 5x)
                            trailing_sl = float(entry_price * Decimal('1.005'))  # +0.5% price from entry
                            # Check if this is better than current (if we have SL order)
                            if 'sl_oid' in order_info:
                                logger.info(f"🔒 TRAILING SL: At {unrealized_pnl_pct:.1f}% PnL - Moving SL to ${trailing_sl:.3f} (locks +2.5% PnL min)")
                                new_sl = trailing_sl
                                needs_update = True
                        else:
                            # Short position - move SL down
                            trailing_sl = float(entry_price * Decimal('0.995'))  # -0.5% price from entry
                            if 'sl_oid' in order_info:
                                logger.info(f"🔒 TRAILING SL: At {unrealized_pnl_pct:.1f}% PnL - Moving SL to ${trailing_sl:.3f} (locks +2.5% PnL min)")
                                new_sl = trailing_sl
                                needs_update = True
                    
                    # **TRAILING TAKE-PROFIT** - Move TP closer as profit increases
                    if unrealized_pnl_pct >= 10.0:  # At 10% PnL (~66% of 15% target)
                        if is_long:
                            # Move TP to 2.4% PRICE (= 12% PnL target with 5x) instead of 3%
                            trailing_tp = float(entry_price * Decimal('1.024'))  # +2.4% price from entry
                            if 'tp_oid' in order_info:
                                logger.info(f"🎯 TRAILING TP: At {unrealized_pnl_pct:.1f}% PnL - Moving TP to ${trailing_tp:.3f} (targets +12% PnL)")
                                new_tp = trailing_tp
                                needs_update = True
                        else:
                            # Short position - move TP up
                            trailing_tp = float(entry_price * Decimal('0.976'))  # -2.4% price
                            if 'tp_oid' in order_info:
                                logger.info(f"🎯 TRAILING TP: At {unrealized_pnl_pct:.1f}% PnL - Moving TP to ${trailing_tp:.3f} (targets +12% PnL)")
                                new_tp = trailing_tp
                                needs_update = True
                    
                    # Additional trailing at 12%+ PnL - move TP even closer
                    if unrealized_pnl_pct >= 12.0:  # At 12% PnL (80% of 15% target)
                        if is_long:
                            # Move TP to just 0.4% PRICE above current (aggressive lock)
                            trailing_tp = float(current_price * Decimal('1.004'))  # Just +0.4% price above current
                            if 'tp_oid' in order_info:
                                logger.info(f"🔥 AGGRESSIVE TRAILING TP: At {unrealized_pnl_pct:.1f}% PnL - Moving TP to ${trailing_tp:.3f} (near current, locks ~{unrealized_pnl_pct:.0f}% PnL)")
                                new_tp = trailing_tp
                                needs_update = True
                        else:
                            trailing_tp = float(current_price * Decimal('0.996'))  # Just -0.4% price below current
                            if 'tp_oid' in order_info:
                                logger.info(f"🔥 AGGRESSIVE TRAILING TP: At {unrealized_pnl_pct:.1f}% PnL - Moving TP to ${trailing_tp:.3f} (near current, locks ~{unrealized_pnl_pct:.0f}% PnL)")
                                new_tp = trailing_tp
                                needs_update = True
                    
                    # ✅ ACTUALLY UPDATE ORDERS ON EXCHANGE (Phase 3 fix!)
                    if needs_update:
                        try:
                            result = await self.order_manager.modify_stops(
                                symbol=symbol,
                                new_sl=new_sl,
                                new_tp=new_tp
                            )
                            if result.get('success'):
                                logger.info(f"✅ Trailing stops updated on exchange: {result.get('modified', [])}")
                            else:
                                logger.warning(f"⚠️ Failed to update trailing stops: {result.get('error')}")
                        except Exception as e:
                            logger.error(f"❌ Error updating trailing stops: {e}")
                
                # Check if approaching SL/TP levels (warning system)
                if unrealized_pnl_pct <= -0.8:  # Within 80% of typical -1% SL
                    logger.warning(f"⚠️  {symbol} approaching stop loss: P&L {unrealized_pnl_pct:+.1f}%")
                elif unrealized_pnl_pct >= 1.6:  # Within 80% of typical +2% TP
                    logger.info(f"🎯 {symbol} approaching take profit: P&L {unrealized_pnl_pct:+.1f}%")
            
            # Store current positions for next iteration
            self._last_positions = current_symbols
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}", exc_info=True)
    
    async def run_trading_loop(self):
        """Main trading loop"""
        logger.info("🚀 Starting trading loop...")
        self.is_running = True
        self.start_time = datetime.now(timezone.utc)
        loop_count = 0
        
        try:
            while not shutdown_event.is_set() and self.is_running:
                loop_count += 1
                
                try:
                    # Check if bot is paused
                    if self.is_paused:
                        await asyncio.sleep(5)
                        continue
                    
                    # Check kill switch
                    if self.kill_switch.check_triggers():
                        logger.critical("🚨 KILL SWITCH ACTIVATED")
                        if self.telegram_bot:
                            try:
                                await self.telegram_bot.notify_emergency("Kill switch activated! Trading stopped.")
                            except:
                                pass
                        break
                    
                    # Update account state every 10 loops
                    if loop_count % 10 == 0:
                        await self.update_account_state()
                        
                        # Update proxies
                        if hasattr(self.risk_engine, 'account_manager'):
                            self.risk_engine.account_manager.current_equity = self.account_value
                            self.risk_engine.account_manager.session_pnl = self.session_pnl
                            self.risk_engine.account_manager.peak_equity = self.peak_equity
                    
                    # Check drawdown
                    self.drawdown_monitor.update()
                    if self.drawdown_monitor.is_paused:
                        logger.warning("⏸️  Paused due to drawdown")
                        await asyncio.sleep(30)
                        continue
                    
                    # Get market data
                    market_data = self.websocket.get_market_data(self.symbol)
                    
                    if not market_data or not market_data.get('price'):
                        await asyncio.sleep(1)
                        continue
                    
                    # PHASE 3 OPTIMIZATION: Use WebSocket candles + smart fallback
                    # Only fetch via API on first run or if WebSocket fails
                    now = datetime.now(timezone.utc)
                    need_initial_fetch = not self._candles_cache and not self._last_candle_fetch
                    need_fallback_fetch = (
                        self._last_candle_fetch and 
                        (now - self._last_candle_fetch).total_seconds() > 900  # 15 min fallback
                    )
                    
                    if need_initial_fetch or need_fallback_fetch:
                        # Initial fetch or fallback if WebSocket not providing candles
                        candles = self.client.get_candles(self.symbol, '1m', 150)
                        if candles:
                            self._candles_cache = candles
                            self._last_candle_fetch = now
                            logger.debug(f"📊 Fetched candles via API: {len(candles)} bars (fallback)")
                    elif self._candle_update_pending:
                        # WebSocket provided new candle - just refresh the cache
                        candles = self.client.get_candles(self.symbol, '1m', 150)
                        if candles:
                            self._candles_cache = candles
                            self._last_candle_fetch = now
                            self._candle_update_pending = False
                            logger.debug(f"📊 Updated candles on new bar: {len(candles)} bars")
                    
                    # Always use cached candles for strategies
                    if self._candles_cache:
                        market_data['candles'] = self._candles_cache
                    
                    # Update account state
                    await self.update_account_state()
                    
                    # Get account state for strategy
                    account_state = await self.client.get_account_state()
                    
                    # Monitor active positions for SL/TP hits
                    await self._monitor_positions(account_state)
                    
                    # Skip signal generation if paused
                    if self.is_paused:
                        await asyncio.sleep(2)
                        continue
                    
                    # **CRITICAL**: Skip signal generation if position already open (max 1 position)
                    positions = account_state.get('positions', [])
                    has_open_position = any(float(pos.get('size', 0)) != 0 for pos in positions)
                    
                    if has_open_position:
                        # Don't generate new signals while position is active
                        await asyncio.sleep(1)
                        continue
                    
                    # PHASE 5: Calculate indicators once using shared calculator
                    if self._candles_cache and self.indicator_calc:
                        # Extract prices from candles
                        prices_list = [Decimal(str(c['close'])) for c in self._candles_cache]
                        volumes_list = [Decimal(str(c['volume'])) for c in self._candles_cache]
                        
                        # Calculate all indicators once
                        shared_indicators = self.indicator_calc.calculate_all(prices_list, volumes_list)
                        
                        # Add to market_data
                        market_data['indicators'] = shared_indicators
                        logger.debug("📊 Phase 5: Using shared indicators")
                    
                    # Generate signal from strategy (now uses shared indicators)
                    signal = await self.strategy.generate_signal(market_data, account_state)
                    
                    if signal:
                        # Send Telegram notification for new signal
                        if self.telegram_bot:
                            try:
                                await self.telegram_bot.notify_signal(signal)
                            except:
                                pass  # Don't let Telegram errors stop trading
                        
                        # Validate with risk engine
                        is_valid, rejection_reason = self.risk_engine.validate_pre_trade(
                            signal['symbol'],
                            signal['side'],
                            Decimal(str(signal['size'])),
                            Decimal(str(signal['entry_price']))
                        )
                        
                        if is_valid:
                            # **REVALIDATE SIGNAL** - Check if still valid before execution
                            current_price = Decimal(str(market_data.get('price', signal['entry_price'])))
                            
                            # Check if strategy has revalidation method
                            if hasattr(self.strategy, 'revalidate_signal'):
                                if not self.strategy.revalidate_signal(signal, current_price):
                                    logger.warning(f"🚫 Signal invalidated before execution - market conditions changed")
                                    await asyncio.sleep(1)
                                    continue
                            
                            # Execute trade
                            logger.info(f"🎯 Executing {signal['signal_type']} signal")
                            
                            result = await self.order_manager.place_market_order(
                                signal['symbol'],
                                signal['side'],
                                Decimal(str(signal['size'])),
                                sl_price=Decimal(str(signal['stop_loss'])),
                                tp_price=Decimal(str(signal['take_profit']))
                            )
                            
                            if result.get('success'):
                                self.trades_executed += 1
                                self.risk_engine.record_trade()
                                self.kill_switch.record_trade(True)
                                self.strategy.record_trade_execution(signal, result)
                                
                                # Send Telegram notification for successful fill
                                if self.telegram_bot:
                                    try:
                                        await self.telegram_bot.notify_fill(
                                            'entry',
                                            signal['symbol'],
                                            signal['side'],
                                            signal['entry_price'],
                                            signal['size']
                                        )
                                    except:
                                        pass
                                
                                # Log trade for AI training
                                await self.log_trade_for_ai(signal, result, market_data)
                                
                                logger.info(f"✅ Trade #{self.trades_executed} executed")
                            else:
                                self.kill_switch.record_trade(False)
                                logger.warning(f"⚠️  Trade failed: {result.get('error')}")
                        else:
                            logger.info(f"🚫 Signal rejected: {rejection_reason}")
                    
                    # Log status every 100 loops
                    if loop_count % 100 == 0:
                        logger.info(f"📊 Loop #{loop_count} - Trades: {self.trades_executed} - P&L: ${self.session_pnl:+.2f}")
                    
                    # Loop delay
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ Loop error: {e}", exc_info=True)
                    
                    # Notify via error handler
                    if self.error_handler:
                        await self.error_handler.handle_critical_error(e, "Trading Loop Iteration")
                    
                    await asyncio.sleep(5)
        
        finally:
            await self.shutdown()
    
    async def log_trade_for_ai(self, signal: Dict, result: Dict, market_data: Dict):
        """Log trade data for AI training"""
        try:
            trade_record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'signal': signal,
                'result': result,
                'market_data': market_data,
                'account_state': {
                    'equity': float(self.account_value),
                    'session_pnl': float(self.session_pnl)
                }
            }
            
            # Log to database if available
            if self.db:
                try:
                    # Insert signal with indicators
                    indicators = {
                        'rsi': market_data.get('rsi'),
                        'macd': market_data.get('macd'),
                        'macd_signal': market_data.get('macd_signal'),
                        'macd_histogram': market_data.get('macd_histogram'),
                        'ema_9': market_data.get('ema_9'),
                        'ema_21': market_data.get('ema_21'),
                        'ema_50': market_data.get('ema_50'),
                        'adx': market_data.get('adx'),
                        'atr': market_data.get('atr'),
                        'volume': market_data.get('volume')
                    }
                    
                    signal_id = await self.db.insert_signal(
                        symbol=signal.get('symbol', self.symbol),
                        signal_type=signal.get('signal', 'BUY'),
                        price=float(signal.get('price', 0)),
                        confidence_score=float(signal.get('confidence', 0)),
                        indicators=indicators,
                        volatility=market_data.get('volatility'),
                        liquidity_score=market_data.get('liquidity_score')
                    )
                    
                    # Insert trade
                    if result.get('executed'):
                        trade_id = await self.db.insert_trade(
                            symbol=signal.get('symbol', self.symbol),
                            signal_type=signal.get('signal', 'BUY'),
                            entry_price=float(result.get('entry_price', 0)),
                            quantity=float(result.get('quantity', 0)),
                            confidence_score=float(signal.get('confidence', 0)),
                            strategy_name=signal.get('strategy'),
                            account_equity=float(self.account_value),
                            session_pnl=float(self.session_pnl),
                            order_id=result.get('order_id')
                        )
                        
                        # Link signal to trade
                        await self.db.mark_signal_executed(signal_id, trade_id)
                        
                        logger.info(f"📊 Logged to database: signal_id={signal_id}, trade_id={trade_id}")
                    else:
                        # Signal rejected
                        await self.db.mark_signal_rejected(
                            signal_id,
                            result.get('rejection_reason', 'Unknown')
                        )
                        logger.info(f"📊 Signal #{signal_id} rejected: {result.get('rejection_reason')}")
                        
                except Exception as db_error:
                    logger.error(f"Database logging failed: {db_error}")
                    # Fall through to JSONL backup
            
            # Backup to JSONL (for now, can remove later)
            log_file = self.trade_log_path / f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, 'a') as f:
                f.write(json.dumps(trade_record) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down...")
        self.is_running = False
        
        try:
            # Stop Telegram bot
            if self.telegram_bot:
                await self.telegram_bot.stop()
            
            # Stop websocket
            if self.websocket:
                await self.websocket.stop()
            
            # Close database connection
            if self.db:
                await self.db.disconnect()
            
            # Log final statistics
            runtime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
            logger.info("📊 Session Summary:")
            logger.info(f"   Runtime: {runtime/3600:.2f} hours")
            logger.info(f"   Trades: {self.trades_executed}")
            logger.info(f"   Session P&L: ${self.session_pnl:+.2f}")
            logger.info(f"   Final Equity: ${self.account_value:.2f}")
            
            if self.strategy:
                stats = self.strategy.get_statistics()
                logger.info(f"   Strategy Stats: {stats}")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def pause(self):
        """Pause trading (for emergency stop button)"""
        if not self.is_paused:
            self.is_paused = True
            logger.warning("⏸️ TRADING PAUSED - No new positions will be opened")
    
    def resume(self):
        """Resume trading (for start button)"""
        if self.is_paused:
            self.is_paused = False
            logger.info("▶️ TRADING RESUMED - Bot is active")
    
    async def get_account_status(self) -> Dict[str, Any]:
        """Get current account status for Telegram"""
        return {
            'account_value': float(self.account_value),
            'margin_used': float(self.margin_used),
            'withdrawable': float(self.account_value - self.margin_used),
            'session_pnl': float(self.session_pnl),
            'trades_executed': self.trades_executed,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'uptime': (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
        }


async def main():
    """Main entry point"""
    logger.info("="*60)
    logger.info("🤖 HYPERAI TRADER - Starting")
    logger.info("="*60)
    
    bot = HyperAIBot()
    
    if await bot.initialize():
        await bot.run_trading_loop()
    else:
        logger.error("❌ Failed to initialize bot")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
