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
from typing import Dict, Any, Optional
from types import FrameType
import json

# Add to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import HyperLiquid integration
from app.hl.hl_client import HyperLiquidClient
from app.hl.hl_websocket import HLWebSocket
from app.hl.hl_order_manager import HLOrderManager

# Import strategies
from app.strategies.strategy_manager import StrategyManager

# Import risk management (consolidated in app/)
from app.risk.risk_engine import RiskEngine
from app.risk.kill_switch import KillSwitch
from app.risk.drawdown_monitor import DrawdownMonitor

# Import Telegram bot
from app.telegram_bot import TelegramBot

# Create logs directory if it doesn't exist
Path('logs').mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        self.order_manager: Optional[HLOrderManager] = None
        
        # Strategy Manager (runs all 4 strategies)
        self.strategy: Optional[StrategyManager] = None
        
        # Risk management
        self.risk_engine: Optional[RiskEngine] = None
        self.kill_switch: Optional[KillSwitch] = None
        self.drawdown_monitor: Optional[DrawdownMonitor] = None
        
        # Telegram bot
        self.telegram_bot: Optional[TelegramBot] = None
        
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
            
            # Initialize websocket
            self.websocket = HLWebSocket([self.symbol])
            await self.websocket.start()
            
            # Initialize order manager
            self.order_manager = HLOrderManager(self.client)
            
            # Set leverage from MAX_LEVERAGE in .env
            leverage = int(os.getenv('MAX_LEVERAGE', '5'))
            await self.order_manager.set_leverage(self.symbol, leverage)
            logger.info(f"⚙️  Leverage set to {leverage}x for {self.symbol}")
            
            # Initialize strategy
            # Initialize strategy manager with all 4 strategies
            logger.info(f"🎯 Initializing Strategy Manager for {self.symbol}")
            self.strategy = StrategyManager(self.symbol)
            
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
                
                # BACKUP SAFETY: Check if SL/TP should have triggered but didn't
                if hasattr(self.order_manager, 'position_targets') and symbol in self.order_manager.position_targets:
                    targets = self.order_manager.position_targets[symbol]
                    sl_price = targets.get('sl_price')
                    tp_price = targets.get('tp_price')
                    is_long = size > 0
                    
                    should_close = False
                    close_reason = ""
                    
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
                            trailing_sl = entry_price * Decimal('1.005')  # +0.5% price from entry
                            if sl_price and trailing_sl > sl_price:
                                logger.info(f"🔒 TRAILING SL: At {unrealized_pnl_pct:.1f}% PnL - Moving SL from ${sl_price:.3f} to ${trailing_sl:.3f} (locks +2.5% PnL min)")
                                targets['sl_price'] = trailing_sl
                        else:
                            # Short position - move SL down
                            trailing_sl = entry_price * Decimal('0.995')  # -0.5% price from entry
                            if sl_price and trailing_sl < sl_price:
                                logger.info(f"🔒 TRAILING SL: At {unrealized_pnl_pct:.1f}% PnL - Moving SL from ${sl_price:.3f} to ${trailing_sl:.3f} (locks +2.5% PnL min)")
                                targets['sl_price'] = trailing_sl
                    
                    # **TRAILING TAKE-PROFIT** - Move TP closer as profit increases
                    if unrealized_pnl_pct >= 10.0 and tp_price:  # At 10% PnL (~66% of 15% target)
                        if is_long:
                            # Move TP to 2.4% PRICE (= 12% PnL target with 5x) instead of 3%
                            trailing_tp = entry_price * Decimal('1.024')  # +2.4% price from entry
                            if trailing_tp < tp_price:  # Only move TP closer, never further
                                logger.info(f"🎯 TRAILING TP: At {unrealized_pnl_pct:.1f}% PnL - Moving TP from ${tp_price:.3f} to ${trailing_tp:.3f} (targets +12% PnL)")
                                targets['tp_price'] = trailing_tp
                        else:
                            # Short position - move TP up
                            trailing_tp = entry_price * Decimal('0.976')  # -2.4% price
                            if trailing_tp > tp_price:  # Only move TP closer
                                logger.info(f"🎯 TRAILING TP: At {unrealized_pnl_pct:.1f}% PnL - Moving TP from ${tp_price:.3f} to ${trailing_tp:.3f} (targets +12% PnL)")
                                targets['tp_price'] = trailing_tp
                    
                    # Additional trailing at 12%+ PnL - move TP even closer
                    if unrealized_pnl_pct >= 12.0 and tp_price:  # At 12% PnL (80% of 15% target)
                        if is_long:
                            # Move TP to just 0.4% PRICE above current (aggressive lock)
                            trailing_tp = current_price * Decimal('1.004')  # Just +0.4% price above current
                            if trailing_tp < tp_price:
                                logger.info(f"🔥 AGGRESSIVE TRAILING TP: At {unrealized_pnl_pct:.1f}% PnL - Moving TP to ${trailing_tp:.3f} (near current, locks ~{unrealized_pnl_pct:.0f}% PnL)")
                                targets['tp_price'] = trailing_tp
                        else:
                            trailing_tp = current_price * Decimal('0.996')  # Just -0.4% price below current
                            if trailing_tp > tp_price:
                                logger.info(f"🔥 AGGRESSIVE TRAILING TP: At {unrealized_pnl_pct:.1f}% PnL - Moving TP to ${trailing_tp:.3f} (near current, locks ~{unrealized_pnl_pct:.0f}% PnL)")
                                targets['tp_price'] = trailing_tp
                    
                    # Check if SL breached
                    if sl_price:
                        if is_long and current_price <= sl_price:
                            should_close = True
                            close_reason = f"BACKUP SL triggered: price ${current_price:.3f} <= SL ${sl_price:.3f}"
                        elif not is_long and current_price >= sl_price:
                            should_close = True
                            close_reason = f"BACKUP SL triggered: price ${current_price:.3f} >= SL ${sl_price:.3f}"
                    
                    # Check if TP breached
                    if tp_price and not should_close:
                        if is_long and current_price >= tp_price:
                            should_close = True
                            close_reason = f"BACKUP TP triggered: price ${current_price:.3f} >= TP ${tp_price:.3f}"
                        elif not is_long and current_price <= tp_price:
                            should_close = True
                            close_reason = f"BACKUP TP triggered: price ${current_price:.3f} <= TP ${tp_price:.3f}"
                    
                    # Emergency close position if SL/TP orders failed
                    if should_close:
                        logger.critical(f"🚨 {close_reason}")
                        logger.critical(f"🚨 Emergency closing position (SL/TP orders may have failed)")
                        
                        # Send Telegram alert
                        if self.telegram_bot:
                            try:
                                await self.telegram_bot.notify_warning(
                                    f"⚠️ EMERGENCY CLOSE\n{symbol}\n{close_reason}\nClosing position now!"
                                )
                            except:
                                pass
                        
                        # Close position immediately
                        try:
                            close_side = 'sell' if is_long else 'buy'
                            result = await self.order_manager.place_market_order(
                                symbol,
                                close_side,
                                abs(Decimal(str(size)))
                            )
                            
                            if result.get('success'):
                                logger.info(f"✅ Emergency close successful")
                                # Clean up targets
                                del self.order_manager.position_targets[symbol]
                            else:
                                logger.error(f"❌ Emergency close failed: {result.get('error')}")
                        except Exception as e:
                            logger.error(f"❌ Emergency close error: {e}", exc_info=True)
                
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
                    
                    # Generate signal from strategy
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
            
            # Save to daily trade log
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
