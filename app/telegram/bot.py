"""
Modern Telegram Bot v2 for HyperBot
Clean architecture with handlers, formatters, and keyboards.

Features:
- Interactive inline keyboards
- Rich message formatting
- Paginated lists
- Conversation flows
- Rate limiting
- Scheduled updates
- Clean error handling
"""

import logging
import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.error import TelegramError

from .formatters import MessageFormatter
from .keyboards import KeyboardFactory

logger = logging.getLogger(__name__)


def mask_token(token: str) -> str:
    """Mask sensitive token for logging."""
    if not token or len(token) < 20:
        return "***"
    if ':' in token:
        parts = token.split(':')
        return f"{parts[0]}:{parts[1][:3]}...{parts[1][-4:]}"
    return f"{token[:10]}...{token[-4:]}"


class TelegramBotV2:
    """
    Modern Telegram Bot with clean architecture.
    
    Features:
    - Modular handlers
    - Rich formatting
    - Interactive keyboards
    - Conversation flows
    - Rate limiting
    - Graceful error handling
    """
    
    # Conversation states
    SET_TP_PRICE = 1
    SET_SL_PRICE = 2
    
    def __init__(self, bot_instance, config: Dict[str, Any] = None):
        """
        Initialize Telegram bot.
        
        Args:
            bot_instance: Main trading bot instance
            config: Optional configuration
        """
        self.bot = bot_instance
        self.config = config or {}
        
        # Credentials
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required in .env")
        
        self.application: Optional[Application] = None
        self.is_running = False
        
        # Formatters
        self.fmt = MessageFormatter
        self.kb = KeyboardFactory
        
        # Session tracking
        self.session_start = datetime.now(timezone.utc)
        
        # Rate limiting
        self._last_message_time: Dict[str, datetime] = {}
        self._message_cooldown = timedelta(seconds=2)
        
        # Notification settings
        self.notify_signals = os.getenv('TG_NOTIFY_SIGNALS', 'true').lower() == 'true'
        self.notify_fills = os.getenv('TG_NOTIFY_FILLS', 'true').lower() == 'true'
        self.notify_pnl_warnings = os.getenv('TG_NOTIFY_PNL_WARNINGS', 'true').lower() == 'true'
        self.status_interval = int(os.getenv('TG_STATUS_INTERVAL', '3600'))
        
        # Background tasks
        self._status_task: Optional[asyncio.Task] = None
        
        logger.info(f"📱 Telegram Bot V2 initialized")
        logger.info(f"   Token: {mask_token(self.token)}")
        logger.info(f"   Chat ID: {self.chat_id}")
    
    # ==================== LIFECYCLE ====================
    
    async def start(self):
        """Start the Telegram bot."""
        if self.is_running:
            return
        
        try:
            self.application = (
                Application.builder()
                .token(self.token)
                .read_timeout(30)
                .write_timeout(30)
                .connect_timeout(30)
                .build()
            )
            
            # Register command handlers
            self._register_handlers()
            
            # Start bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            self.is_running = True
            
            # Start scheduled updates
            if self.status_interval > 0:
                self._status_task = asyncio.create_task(self._scheduled_status())
            
            # Send startup message
            await self._send_startup_message()
            
            logger.info("✅ Telegram Bot V2 started")
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            raise
    
    async def stop(self):
        """Stop the Telegram bot gracefully."""
        if not self.is_running:
            return
        
        try:
            # Cancel background tasks
            if self._status_task and not self._status_task.done():
                self._status_task.cancel()
                try:
                    await self._status_task
                except asyncio.CancelledError:
                    pass
            
            # Send shutdown message
            try:
                await self.send_message("🛑 *BOT SHUTTING DOWN*\n\nGoodbye!")
            except:
                pass
            
            # Stop application
            if self.application:
                if self.application.updater:
                    await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            self.is_running = False
            logger.info("✅ Telegram Bot V2 stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
            self.is_running = False
    
    def _register_handlers(self):
        """Register all command and callback handlers."""
        app = self.application
        
        # Command handlers
        commands = [
            ("start", self._cmd_start),
            ("menu", self._cmd_start),
            ("help", self._cmd_help),
            ("status", self._cmd_dashboard),
            ("dashboard", self._cmd_dashboard),
            ("pos", self._cmd_positions),
            ("positions", self._cmd_positions),
            ("trades", self._cmd_trades),
            ("pnl", self._cmd_pnl),
            ("balance", self._cmd_balance),
            ("market", self._cmd_market),
            ("stats", self._cmd_stats),
            ("close", self._cmd_close),
            ("closeall", self._cmd_closeall),
            ("sl", self._cmd_set_sl),
            ("tp", self._cmd_set_tp),
            ("managed", self._cmd_managed),
            ("logs", self._cmd_logs),
            ("db", self._cmd_db_stats),
            ("kelly", self._cmd_kelly),
            ("regime", self._cmd_regime),
            ("assets", self._cmd_assets),
            ("alerts", self._cmd_alerts),
        ]
        
        for cmd, handler in commands:
            app.add_handler(CommandHandler(cmd, handler))
        
        # Callback query handler
        app.add_handler(CallbackQueryHandler(self._handle_callback))
    
    # ==================== MESSAGE HELPERS ====================
    
    async def send_message(
        self, 
        text: str, 
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str = 'Markdown',
        disable_preview: bool = True,
    ) -> bool:
        """Send message to configured chat."""
        if not self.application:
            return False
        
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
            )
            return True
        except TelegramError as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    async def _edit_or_reply(
        self,
        update: Update,
        text: str,
        reply_markup: InlineKeyboardMarkup = None,
        parse_mode: str = 'Markdown',
    ):
        """Edit message if callback, otherwise reply."""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
            elif update.message:
                await update.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
        except TelegramError as e:
            logger.error(f"Message error: {e}")
    
    def _can_send(self, msg_type: str) -> bool:
        """Rate limiting check."""
        now = datetime.now(timezone.utc)
        last = self._last_message_time.get(msg_type)
        
        if last and (now - last) < self._message_cooldown:
            return False
        
        self._last_message_time[msg_type] = now
        return True
    
    # ==================== COMMAND HANDLERS ====================
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - show main menu."""
        message = (
            "🤖 *HYPERBOT CONTROL PANEL*\n\n"
            "Welcome to your trading bot dashboard!\n\n"
            "Use the buttons below or type commands.\n"
            "Type /help for full command list."
        )
        await self._edit_or_reply(update, message, self.kb.main_menu())
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await self._edit_or_reply(update, self.fmt.format_help(), self.kb.back_to_menu())
    
    async def _cmd_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status or /dashboard command."""
        try:
            # Gather dashboard data
            data = await self._get_dashboard_data()
            message = self.fmt.format_dashboard(data)
            await self._edit_or_reply(update, message, self.kb.dashboard_actions())
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            await self._edit_or_reply(
                update, 
                self.fmt.format_error("Dashboard Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command."""
        try:
            positions = await self._get_positions()
            message = self.fmt.format_positions_list(positions)
            
            if positions:
                keyboard = self.kb.positions_list(positions)
            else:
                keyboard = self.kb.empty_positions()
            
            await self._edit_or_reply(update, message, keyboard)
        except Exception as e:
            logger.error(f"Positions error: {e}")
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Positions Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trades command."""
        try:
            trades = await self._get_recent_trades()
            message = self.fmt.format_trades_list(trades)
            
            if trades:
                keyboard = self.kb.trades_list()
            else:
                keyboard = self.kb.empty_trades()
            
            await self._edit_or_reply(update, message, keyboard)
        except Exception as e:
            logger.error(f"Trades error: {e}")
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Trades Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pnl command."""
        try:
            data = await self._get_pnl_data()
            message = self.fmt.format_pnl_breakdown(data)
            await self._edit_or_reply(update, message, self.kb.quick_actions())
        except Exception as e:
            logger.error(f"PnL error: {e}")
            await self._edit_or_reply(
                update,
                self.fmt.format_error("P&L Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command - quick balance check."""
        try:
            account = float(self.bot.account_value)
            margin = float(self.bot.margin_used)
            available = account - margin
            
            message = (
                "💰 *QUICK BALANCE*\n\n"
                f"Balance:   {self.fmt.format_money(account)}\n"
                f"Margin:    {self.fmt.format_money(margin)}\n"
                f"Available: {self.fmt.format_money(available)}"
            )
            await self._edit_or_reply(update, message, self.kb.quick_actions())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Balance Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /market command."""
        try:
            data = await self._get_market_data()
            message = self.fmt.format_market_overview(data)
            await self._edit_or_reply(update, message, self.kb.quick_actions())
        except Exception as e:
            logger.error(f"Market error: {e}")
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Market Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        try:
            stats = self.bot.strategy.get_statistics() if hasattr(self.bot, 'strategy') else {}
            
            lines = [
                "📊 *PERFORMANCE STATISTICS*",
                "",
                "─────── Strategy ────────",
            ]
            
            for name, data in stats.get('strategy_breakdown', {}).items():
                lines.append(f"{name}: {data.get('signals', 0)} signals, {data.get('trades', 0)} trades")
            
            lines.extend([
                "",
                "─────── Execution ───────",
                f"Total Signals: {stats.get('total_signals', 0)}",
                f"Executed:      {stats.get('total_trades', 0)}",
                f"Rate:          {self.fmt.format_percent(stats.get('execution_rate', 0) * 100)}",
                "",
                f"Uptime: {self.fmt.format_uptime(self.session_start)}",
            ])
            
            await self._edit_or_reply(update, "\n".join(lines), self.kb.quick_actions())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Stats Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /close [symbol] command."""
        try:
            if not context.args:
                await self._edit_or_reply(
                    update,
                    "Usage: /close SYMBOL\nExample: /close SOL",
                    self.kb.back_to_menu()
                )
                return
            
            symbol = context.args[0].upper()
            message = f"⚠️ *CLOSE POSITION*\n\nAre you sure you want to close {symbol}?"
            await self._edit_or_reply(update, message, self.kb.close_confirm(symbol))
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Close Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_closeall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /closeall command."""
        try:
            positions = await self._get_positions()
            
            if not positions:
                await self._edit_or_reply(update, "📭 No positions to close", self.kb.back_to_menu())
                return
            
            total_pnl = sum(p.get('unrealized_pnl', 0) for p in positions)
            
            message = (
                f"⚠️ *CLOSE ALL POSITIONS*\n\n"
                f"This will close {len(positions)} position(s)\n"
                f"Current P&L: {self.fmt.format_money(total_pnl, sign=True)}\n\n"
                f"Are you absolutely sure?"
            )
            await self._edit_or_reply(update, message, self.kb.closeall_confirm())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Close All Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_set_sl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sl [symbol] [price] command."""
        try:
            if len(context.args) < 2:
                await self._edit_or_reply(
                    update,
                    "Usage: /sl SYMBOL PRICE\nExample: /sl SOL 145.50",
                    self.kb.back_to_menu()
                )
                return
            
            symbol = context.args[0].upper()
            price = float(context.args[1])
            
            result = self.bot.order_manager.set_position_tpsl(symbol=symbol, sl_price=price)
            
            if result.get('status') == 'ok':
                await self._edit_or_reply(
                    update,
                    f"✅ *STOP LOSS SET*\n\n{symbol}: ${price:.4f}",
                    self.kb.back_to_menu()
                )
            else:
                await self._edit_or_reply(
                    update,
                    self.fmt.format_error("Set SL Failed", str(result)),
                    self.kb.back_to_menu()
                )
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Set SL Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_set_tp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tp [symbol] [price] command."""
        try:
            if len(context.args) < 2:
                await self._edit_or_reply(
                    update,
                    "Usage: /tp SYMBOL PRICE\nExample: /tp SOL 165.00",
                    self.kb.back_to_menu()
                )
                return
            
            symbol = context.args[0].upper()
            price = float(context.args[1])
            
            result = self.bot.order_manager.set_position_tpsl(symbol=symbol, tp_price=price)
            
            if result.get('status') == 'ok':
                await self._edit_or_reply(
                    update,
                    f"✅ *TAKE PROFIT SET*\n\n{symbol}: ${price:.4f}",
                    self.kb.back_to_menu()
                )
            else:
                await self._edit_or_reply(
                    update,
                    self.fmt.format_error("Set TP Failed", str(result)),
                    self.kb.back_to_menu()
                )
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Set TP Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_managed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /managed command."""
        try:
            if not hasattr(self.bot, 'position_manager') or not self.bot.position_manager:
                await self._edit_or_reply(update, "⚠️ Position Manager not initialized", self.kb.back_to_menu())
                return
            
            pm = self.bot.position_manager
            managed = pm.managed_positions
            
            if not managed:
                await self._edit_or_reply(
                    update,
                    "📊 *MANAGED POSITIONS*\n\nNo positions currently managed.",
                    self.kb.back_to_menu()
                )
                return
            
            lines = ["📊 *MANAGED POSITIONS*\n"]
            
            for symbol, pos in managed.items():
                source = "👤" if pos.is_manual else "🤖"
                side_emoji = "🟢" if pos.side.lower() == 'long' else "🔴"
                
                lines.append(f"{side_emoji} *{symbol}* {source}")
                lines.append(f"   Entry: ${pos.entry_price:.4f}")
                lines.append(f"   SL: {'✅' if pos.sl_price else '⚠️'} TP: {'✅' if pos.tp_price else '⚠️'}")
                lines.append("")
            
            await self._edit_or_reply(update, "\n".join(lines), self.kb.back_to_menu())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Managed Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs command."""
        try:
            from pathlib import Path
            
            log_date = datetime.now().strftime('%Y%m%d')
            workspace = Path(__file__).parent.parent.parent
            
            log_paths = [
                workspace / f"logs/bot_{log_date}.log",
                workspace / "logs/bot.log",
                Path(f"/home/hyperbot/logs/bot_{log_date}.log"),
            ]
            
            log_file = None
            for path in log_paths:
                if path.exists():
                    log_file = path
                    break
            
            if not log_file:
                await self._edit_or_reply(update, "📭 No log file found", self.kb.back_to_menu())
                return
            
            with open(log_file, 'r') as f:
                lines = f.readlines()[-30:]
            
            formatted = []
            for line in lines:
                if ' - INFO - ' in line:
                    emoji = "ℹ️"
                elif ' - WARNING - ' in line:
                    emoji = "⚠️"
                elif ' - ERROR - ' in line:
                    emoji = "❌"
                else:
                    continue
                
                parts = line.split(' - ', 3)
                if len(parts) >= 4:
                    time = parts[0].split(' ')[1].split(',')[0]
                    msg = parts[3].strip()[:80]
                    formatted.append(f"{emoji} `{time}` {msg}")
            
            message = "📝 *RECENT LOGS*\n\n" + "\n".join(formatted[-15:])
            await self._edit_or_reply(update, message, self.kb.quick_actions())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Logs Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_db_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /db command."""
        try:
            if not self.bot.db:
                await self._edit_or_reply(update, "❌ Database not connected", self.kb.back_to_menu())
                return
            
            stats = await self.bot.db.get_total_stats()
            
            lines = [
                "📊 *DATABASE STATISTICS*",
                "",
                f"Total Trades: {int(stats.get('total_trades', 0))}",
                f"Wins: {int(stats.get('winning_trades', 0))}",
                f"Losses: {int(stats.get('losing_trades', 0))}",
                f"Win Rate: {self.fmt.format_percent(float(stats.get('win_rate', 0)))}",
                "",
                f"Total P&L: {self.fmt.format_money(float(stats.get('total_pnl', 0)), sign=True)}",
                f"Best Trade: {self.fmt.format_money(float(stats.get('best_trade', 0)), sign=True)}",
                f"Worst Trade: {self.fmt.format_money(float(stats.get('worst_trade', 0)), sign=True)}",
            ]
            
            await self._edit_or_reply(update, "\n".join(lines), self.kb.back_to_menu())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("DB Stats Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_kelly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /kelly command."""
        try:
            if not hasattr(self.bot, 'kelly_calculator'):
                await self._edit_or_reply(update, "⚠️ Kelly Calculator not available", self.kb.back_to_menu())
                return
            
            kc = self.bot.kelly_calculator
            
            lines = [
                "📊 *KELLY CRITERION*",
                "",
                f"Recommended Size: {self.fmt.format_percent(kc.recommended_size * 100)}",
                f"Win Rate: {self.fmt.format_percent(kc.win_rate * 100)}",
                f"Avg Win: {self.fmt.format_money(kc.avg_win, sign=True)}",
                f"Avg Loss: {self.fmt.format_money(kc.avg_loss)}",
                f"Trades Analyzed: {kc.trade_count}",
            ]
            
            await self._edit_or_reply(update, "\n".join(lines), self.kb.back_to_menu())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Kelly Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_regime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /regime command."""
        try:
            # Get regime from strategy
            regime = "Unknown"
            if hasattr(self.bot, 'strategy') and hasattr(self.bot.strategy, 'strategies'):
                for name, strat in self.bot.strategy.strategies.items():
                    if hasattr(strat, 'regime_detector'):
                        regime = strat.regime_detector.current_regime.value
                        break
            
            message = f"📊 *MARKET REGIME*\n\nCurrent: {regime}"
            await self._edit_or_reply(update, message, self.kb.back_to_menu())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Regime Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_assets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /assets command for multi-asset mode."""
        try:
            if not hasattr(self.bot, 'trading_symbols'):
                symbols = [self.bot.symbol]
            else:
                symbols = self.bot.trading_symbols
            
            lines = [
                "🌐 *TRADING ASSETS*",
                "",
            ]
            
            for symbol in symbols:
                lines.append(f"• {symbol}")
            
            await self._edit_or_reply(update, "\n".join(lines), self.kb.back_to_menu())
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Assets Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _cmd_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command - notification settings."""
        message = (
            "🔔 *NOTIFICATION SETTINGS*\n\n"
            f"Signal Alerts: {'✅' if self.notify_signals else '❌'}\n"
            f"Trade Fills: {'✅' if self.notify_fills else '❌'}\n"
            f"P&L Warnings: {'✅' if self.notify_pnl_warnings else '❌'}\n"
            f"Status Interval: {self.status_interval}s"
        )
        await self._edit_or_reply(
            update, 
            message, 
            self.kb.notification_settings(
                self.notify_signals,
                self.notify_fills,
                self.notify_pnl_warnings
            )
        )
    
    # ==================== CALLBACK HANDLER ====================
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses."""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        
        # Route to appropriate handler
        handlers = {
            "main_menu": self._cmd_start,
            "dashboard": self._cmd_dashboard,
            "refresh_dashboard": self._cmd_dashboard,
            "positions": self._cmd_positions,
            "trades": self._cmd_trades,
            "pnl": self._cmd_pnl,
            "market": self._cmd_market,
            "stats": self._cmd_stats,
            "help": self._cmd_help,
            "settings": self._cmd_alerts,
            "noop": lambda u, c: None,
        }
        
        if action in handlers:
            await handlers[action](update, context)
        elif action == "bot_start":
            await self._handle_bot_start(update)
        elif action == "bot_pause":
            await self._handle_bot_pause(update)
        elif action.startswith("close_confirm_"):
            symbol = action.replace("close_confirm_", "")
            await self._handle_close_confirm(update, symbol)
        elif action.startswith("close_execute_"):
            symbol = action.replace("close_execute_", "")
            await self._handle_close_execute(update, symbol)
        elif action == "closeall_confirm":
            await self._cmd_closeall(update, context)
        elif action == "closeall_execute":
            await self._handle_closeall_execute(update)
        elif action.startswith("pos_detail_"):
            symbol = action.replace("pos_detail_", "")
            await self._handle_position_detail(update, symbol)
        elif action.startswith("set_tp_"):
            symbol = action.replace("set_tp_", "")
            await self._handle_set_tp_prompt(update, symbol)
        elif action.startswith("set_sl_"):
            symbol = action.replace("set_sl_", "")
            await self._handle_set_sl_prompt(update, symbol)
        elif action.startswith("toggle_"):
            await self._handle_toggle_setting(update, action)
        elif action.startswith("positions_page_"):
            page = int(action.replace("positions_page_", ""))
            await self._handle_positions_page(update, page)
    
    async def _handle_bot_start(self, update: Update):
        """Handle bot start button."""
        if hasattr(self.bot, 'resume'):
            self.bot.resume()
        self.bot.is_paused = False
        
        await self._edit_or_reply(
            update,
            "🚀 *BOT STARTED*\n\nTrading resumed. Monitoring markets...",
            self.kb.bot_control(True, False)
        )
    
    async def _handle_bot_pause(self, update: Update):
        """Handle bot pause button."""
        if hasattr(self.bot, 'pause'):
            self.bot.pause()
        self.bot.is_paused = True
        
        await self._edit_or_reply(
            update,
            "⏸️ *BOT PAUSED*\n\nNo new trades will be opened.",
            self.kb.bot_control(True, True)
        )
    
    async def _handle_close_confirm(self, update: Update, symbol: str):
        """Show close confirmation."""
        message = f"⚠️ *CLOSE {symbol}?*\n\nThis action cannot be undone."
        await self._edit_or_reply(update, message, self.kb.close_confirm(symbol))
    
    async def _handle_close_execute(self, update: Update, symbol: str):
        """Execute position close."""
        try:
            await self._edit_or_reply(update, f"⏳ Closing {symbol}...", None)
            
            result = self.bot.order_manager.market_close(symbol)
            
            if result.get('status') == 'ok':
                await self._edit_or_reply(
                    update,
                    f"✅ *POSITION CLOSED*\n\n{symbol} has been closed.",
                    self.kb.back_to_menu()
                )
            else:
                await self._edit_or_reply(
                    update,
                    self.fmt.format_error("Close Failed", str(result)),
                    self.kb.back_to_menu()
                )
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Close Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _handle_closeall_execute(self, update: Update):
        """Execute close all positions."""
        try:
            positions = await self._get_positions()
            
            if not positions:
                await self._edit_or_reply(update, "📭 No positions to close", self.kb.back_to_menu())
                return
            
            await self._edit_or_reply(update, f"⏳ Closing {len(positions)} positions...", None)
            
            closed = 0
            for pos in positions:
                try:
                    result = self.bot.order_manager.market_close(pos['symbol'])
                    if result.get('status') == 'ok':
                        closed += 1
                except Exception as e:
                    logger.error(f"Error closing {pos['symbol']}: {e}")
            
            await self._edit_or_reply(
                update,
                f"✅ *ALL POSITIONS CLOSED*\n\nClosed {closed}/{len(positions)} positions.",
                self.kb.back_to_menu()
            )
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Close All Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _handle_position_detail(self, update: Update, symbol: str):
        """Show position detail with actions."""
        try:
            positions = await self._get_positions()
            pos = next((p for p in positions if p.get('symbol') == symbol), None)
            
            if not pos:
                await self._edit_or_reply(update, f"❌ Position {symbol} not found", self.kb.back_to_menu())
                return
            
            side_emoji = "🟢" if pos.get('side', '').lower() == 'long' else "🔴"
            pnl = pos.get('unrealized_pnl', 0)
            
            lines = [
                f"{side_emoji} *{symbol} POSITION*",
                "",
                f"Side:    {pos.get('side', 'N/A').upper()}",
                f"Size:    {self.fmt.format_number(abs(pos.get('size', 0)))}",
                f"Entry:   {self.fmt.format_money(pos.get('entry_price', 0), 4)}",
                f"Current: {self.fmt.format_money(pos.get('current_price', 0), 4)}",
                "",
                f"P&L: {self.fmt.pnl_emoji(pnl)} {self.fmt.format_money(pnl, sign=True)}",
                f"     ({self.fmt.format_percent(pos.get('unrealized_pnl_pct', 0), sign=True)})",
            ]
            
            await self._edit_or_reply(update, "\n".join(lines), self.kb.position_detail(symbol))
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Position Detail Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _handle_set_tp_prompt(self, update: Update, symbol: str):
        """Show TP price selection."""
        try:
            price = await self.bot.client.get_market_price(symbol)
            message = f"🎯 *SET TAKE PROFIT*\n\n{symbol}\nCurrent: {self.fmt.format_money(float(price), 4)}"
            await self._edit_or_reply(update, message, self.kb.price_input(symbol, 'tp', float(price)))
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Set TP Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _handle_set_sl_prompt(self, update: Update, symbol: str):
        """Show SL price selection."""
        try:
            price = await self.bot.client.get_market_price(symbol)
            message = f"🛑 *SET STOP LOSS*\n\n{symbol}\nCurrent: {self.fmt.format_money(float(price), 4)}"
            await self._edit_or_reply(update, message, self.kb.price_input(symbol, 'sl', float(price)))
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Set SL Error", str(e)),
                self.kb.back_to_menu()
            )
    
    async def _handle_toggle_setting(self, update: Update, action: str):
        """Toggle notification setting."""
        if action == "toggle_signals":
            self.notify_signals = not self.notify_signals
        elif action == "toggle_fills":
            self.notify_fills = not self.notify_fills
        elif action == "toggle_pnl_warnings":
            self.notify_pnl_warnings = not self.notify_pnl_warnings
        
        await self._cmd_alerts(update, None)
    
    async def _handle_positions_page(self, update: Update, page: int):
        """Handle positions pagination."""
        try:
            positions = await self._get_positions()
            message = self.fmt.format_positions_list(positions, page=page)
            await self._edit_or_reply(update, message, self.kb.positions_list(positions, page=page))
        except Exception as e:
            await self._edit_or_reply(
                update,
                self.fmt.format_error("Positions Error", str(e)),
                self.kb.back_to_menu()
            )
    
    # ==================== DATA FETCHERS ====================
    
    async def _get_dashboard_data(self) -> Dict[str, Any]:
        """Gather dashboard data from bot."""
        positions = await self._get_positions()
        
        return {
            'account_value': float(self.bot.account_value),
            'margin_used': float(self.bot.margin_used),
            'daily_pnl': float(getattr(self.bot, 'session_pnl', 0)),
            'daily_pnl_pct': 0,  # TODO: Calculate
            'open_positions': len(positions),
            'is_running': self.bot.is_running,
            'is_paused': getattr(self.bot, 'is_paused', False),
            'uptime': self.session_start,
            'trades_today': getattr(self.bot, 'trades_executed', 0),
        }
    
    async def _get_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions."""
        try:
            account = await self.bot.client.get_account_state()
            positions = account.get('positions', [])
            
            # Enrich with current prices
            for pos in positions:
                symbol = pos.get('symbol')
                try:
                    current = await self.bot.client.get_market_price(symbol)
                    pos['current_price'] = float(current)
                except:
                    pos['current_price'] = pos.get('entry_price', 0)
            
            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def _get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent completed trades."""
        try:
            fills = self.bot.client.info.user_fills(self.bot.client.address)
            
            trades = []
            for fill in fills[:50]:
                pnl = float(fill.get('closedPnl', '0'))
                if pnl != 0:
                    trades.append({
                        'symbol': fill.get('coin'),
                        'side': 'long' if fill.get('side') == 'B' else 'short',
                        'pnl': pnl,
                        'time': datetime.fromtimestamp(fill['time'] / 1000, tz=timezone.utc),
                        'price': float(fill.get('px', 0)),
                        'size': float(fill.get('sz', 0)),
                    })
            
            return trades[:limit]
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    async def _get_pnl_data(self) -> Dict[str, Any]:
        """Get P&L breakdown data."""
        try:
            fills = self.bot.client.info.user_fills(self.bot.client.address)
            
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            today_pnl = 0
            today_fees = 0
            today_trades = 0
            weekly_pnl = 0
            monthly_pnl = 0
            
            for fill in fills:
                fill_time = datetime.fromtimestamp(fill['time'] / 1000, tz=timezone.utc)
                pnl = float(fill.get('closedPnl', '0'))
                fee = float(fill.get('fee', '0'))
                
                if fill_time >= today_start:
                    if pnl != 0:
                        today_pnl += pnl
                        today_trades += 1
                    today_fees += fee
                
                if fill_time >= week_ago and pnl != 0:
                    weekly_pnl += pnl
                
                if fill_time >= month_ago and pnl != 0:
                    monthly_pnl += pnl
            
            return {
                'today_pnl': today_pnl,
                'today_fees': today_fees,
                'today_trades': today_trades,
                'weekly_pnl': weekly_pnl,
                'monthly_pnl': monthly_pnl,
                'session_pnl': float(getattr(self.bot, 'session_pnl', 0)),
                'session_start': self.session_start,
            }
        except Exception as e:
            logger.error(f"Error getting PnL data: {e}")
            return {}
    
    async def _get_market_data(self) -> Dict[str, Any]:
        """Get market overview data."""
        try:
            symbol = self.bot.symbol
            price = await self.bot.client.get_market_price(symbol)
            
            candles = getattr(self.bot, 'current_candles', [])
            
            if candles and len(candles) > 0:
                high_24h = max(c.get('high', c.get('h', 0)) for c in candles[-1440:])
                low_24h = min(c.get('low', c.get('l', 0)) for c in candles[-1440:])
                open_24h = candles[-min(1440, len(candles))].get('open', candles[-1].get('o', float(price)))
                change_24h = ((float(price) - open_24h) / open_24h * 100) if open_24h else 0
            else:
                high_24h = low_24h = float(price)
                change_24h = 0
            
            # Get regime
            regime = "Unknown"
            if hasattr(self.bot, 'strategy') and hasattr(self.bot.strategy, 'strategies'):
                for name, strat in self.bot.strategy.strategies.items():
                    if hasattr(strat, 'regime_detector'):
                        regime = strat.regime_detector.current_regime.value
                        break
            
            return {
                'symbol': symbol,
                'price': float(price),
                'change_24h': change_24h,
                'high_24h': high_24h,
                'low_24h': low_24h,
                'regime': regime,
                'session': datetime.now(timezone.utc).strftime('%H:%M UTC'),
            }
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {'symbol': 'N/A', 'price': 0}
    
    # ==================== NOTIFICATIONS ====================
    
    async def notify_signal(self, signal: Dict[str, Any]):
        """Send signal notification."""
        if not self.notify_signals or not self._can_send('signal'):
            return
        
        message = self.fmt.format_signal_notification(signal)
        await self.send_message(message)
    
    async def notify_fill(self, fill: Dict[str, Any]):
        """Send fill notification."""
        if not self.notify_fills or not self._can_send('fill'):
            return
        
        message = self.fmt.format_fill_notification(fill)
        await self.send_message(message)
    
    async def notify_pnl_warning(self, pnl: float, threshold: float):
        """Send P&L warning notification."""
        if not self.notify_pnl_warnings or not self._can_send('pnl_warning'):
            return
        
        emoji = "⚠️" if pnl < 0 else "🎉"
        message = (
            f"{emoji} *P&L ALERT*\n\n"
            f"Session P&L: {self.fmt.format_money(pnl, sign=True)}\n"
            f"Threshold: {self.fmt.format_percent(threshold)}"
        )
        await self.send_message(message)
    
    async def notify_error(self, error: str, context: str = "System"):
        """Send error notification."""
        if not self._can_send('error'):
            return
        
        message = self.fmt.format_error(f"{context} Error", error[:200])
        await self.send_message(message)
    
    # ==================== SCHEDULED TASKS ====================
    
    async def _scheduled_status(self):
        """Send periodic status updates."""
        while self.is_running:
            try:
                await asyncio.sleep(self.status_interval)
                
                if not self.is_running:
                    break
                
                data = await self._get_dashboard_data()
                message = (
                    "📊 *SCHEDULED STATUS*\n\n"
                    f"Balance: {self.fmt.format_money(data['account_value'])}\n"
                    f"P&L: {self.fmt.pnl_emoji(data['daily_pnl'])} {self.fmt.format_money(data['daily_pnl'], sign=True)}\n"
                    f"Positions: {data['open_positions']}\n"
                    f"Status: {'🟢 Active' if data['is_running'] and not data['is_paused'] else '⏸️ Paused'}"
                )
                await self.send_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduled status error: {e}")
    
    async def _send_startup_message(self):
        """Send startup notification."""
        message = (
            "🚀 *HYPERBOT STARTED*\n\n"
            f"💰 Balance: {self.fmt.format_money(float(self.bot.account_value))}\n"
            f"🎯 Mode: Multi-Asset Trading\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            "Tap /menu for control panel"
        )
        await self.send_message(message, self.kb.main_menu())
