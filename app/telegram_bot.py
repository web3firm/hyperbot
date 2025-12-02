"""
Enterprise Telegram Bot for HyperBot
Features: Positions, Trades, PnL, Emergency Controls, Real-time Updates
"""

import logging
import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)


def mask_token(token: str) -> str:
    """
    Mask sensitive token for logging
    Shows first 10 chars and last 4 chars, masks the middle
    Example: 8374468872:AAGZEBeQ3Yjwb4v2xNQRuePIbnBrSVKaOGI -> 8374468872:AAG...aOGI
    """
    if not token or len(token) < 20:
        return "***"
    
    # For Telegram tokens format: XXXXXXXXXX:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    if ':' in token:
        parts = token.split(':')
        bot_id = parts[0]
        token_part = parts[1]
        return f"{bot_id}:{token_part[:3]}...{token_part[-4:]}"
    
    # Generic masking
    return f"{token[:10]}...{token[-4:]}"


def mask_sensitive_data(text: str, token: str = None) -> str:
    """
    Mask sensitive data in text (for error messages, logs, etc.)
    Replaces full token with masked version
    """
    if not text:
        return text
    
    # Get token from environment if not provided
    if not token:
        token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    if token and token in text:
        masked = mask_token(token)
        text = text.replace(token, masked)
    
    return text


class TelegramBot:
    """
    Enterprise Telegram Bot for trading system monitoring and control
    
    Features:
    - Real-time position monitoring
    - Last 10 trades with PnL
    - Daily/weekly statistics
    - Emergency start/stop buttons
    - Account status and margin
    - Performance analytics
    - Rate limiting and spam protection
    - Scheduled status updates
    """
    
    def __init__(self, bot_instance, config: Dict[str, Any] = None):
        """
        Initialize Telegram bot
        
        Args:
            bot_instance: Main trading bot instance
            config: Configuration dictionary
        """
        self.bot = bot_instance
        self.config = config or {}
        
        # Telegram credentials
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        
        self.application = None
        self.is_running = False
        
        # Statistics tracking
        self.trade_history = []
        self.daily_pnl = Decimal('0')
        self.session_start = datetime.now(timezone.utc)
        
        # Rate limiting (prevent spam)
        self._last_message_time: Dict[str, datetime] = {}
        self._message_cooldown = timedelta(seconds=2)  # Min 2s between same type messages
        
        # Notification settings (configurable)
        self.notify_signals = os.getenv('TG_NOTIFY_SIGNALS', 'true').lower() == 'true'
        self.notify_fills = os.getenv('TG_NOTIFY_FILLS', 'true').lower() == 'true'
        self.notify_pnl_warnings = os.getenv('TG_NOTIFY_PNL_WARNINGS', 'true').lower() == 'true'
        self.status_update_interval = int(os.getenv('TG_STATUS_INTERVAL', '3600'))  # Default 1 hour
        
        # Scheduled tasks
        self._status_task = None
        
        logger.info("📱 Telegram Bot initialized")
        logger.info(f"   Token: {mask_token(self.token)}")
        logger.info(f"   Chat ID: {self.chat_id}")
    
    async def start(self):
        """Start the Telegram bot"""
        if self.is_running:
            return
        
        try:
            # Build application with custom defaults
            self.application = (
                Application.builder()
                .token(self.token)
                .read_timeout(30)
                .write_timeout(30)
                .connect_timeout(30)
                .build()
            )
            
            # Register handlers - Core commands
            self.application.add_handler(CommandHandler("start", self._cmd_start))
            self.application.add_handler(CommandHandler("status", self._cmd_status))
            self.application.add_handler(CommandHandler("positions", self._cmd_positions))
            self.application.add_handler(CommandHandler("trades", self._cmd_trades))
            self.application.add_handler(CommandHandler("pnl", self._cmd_pnl))
            self.application.add_handler(CommandHandler("stats", self._cmd_stats))
            self.application.add_handler(CommandHandler("logs", self._cmd_logs))
            self.application.add_handler(CommandHandler("train", self._cmd_train))
            self.application.add_handler(CommandHandler("analytics", self._cmd_analytics))
            self.application.add_handler(CommandHandler("dbstats", self._cmd_dbstats))
            self.application.add_handler(CommandHandler("help", self._cmd_help))
            
            # New enhanced commands
            self.application.add_handler(CommandHandler("market", self._cmd_market))
            self.application.add_handler(CommandHandler("close", self._cmd_close))
            self.application.add_handler(CommandHandler("closeall", self._cmd_closeall))
            self.application.add_handler(CommandHandler("balance", self._cmd_balance))
            self.application.add_handler(CommandHandler("regime", self._cmd_regime))
            self.application.add_handler(CommandHandler("session", self._cmd_session))
            
            # Callback handler for inline buttons
            self.application.add_handler(CallbackQueryHandler(self._handle_callback))
            
            # Start bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            self.is_running = True
            
            # Start scheduled status updates
            if self.status_update_interval > 0:
                self._status_task = asyncio.create_task(self._scheduled_status_updates())
            
            # Send startup message
            await self.send_message(
                "🚀 *ENTERPRISE BOT STARTED*\n\n"
                f"✅ Connected to trading system\n"
                f"💰 Account: ${self.bot.account_value:.2f}\n"
                f"🎯 Strategies: World-Class Swing + Scalping\n"
                f"⏰ Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                "Use /help for commands"
            )
            
            logger.info("✅ Telegram bot started successfully")
            
        except Exception as e:
            error_msg = mask_sensitive_data(str(e), self.token)
            logger.error(f"Failed to start Telegram bot: {error_msg}")
            raise Exception(f"Failed to start Telegram bot: {error_msg}") from None
    
    async def stop(self):
        """Stop the Telegram bot gracefully"""
        if not self.is_running:
            logger.info("Telegram bot already stopped")
            return
        
        try:
            # Cancel scheduled tasks
            if self._status_task and not self._status_task.done():
                self._status_task.cancel()
                try:
                    await self._status_task
                except asyncio.CancelledError:
                    pass
            
            # Try to send shutdown message (may fail if already disconnected)
            try:
                await self.send_message("🛑 *BOT STOPPING*\n\nTelegram bot shutting down...")
            except Exception:
                pass  # Ignore send errors during shutdown
            
            # Stop polling first
            if self.application and self.application.updater:
                try:
                    await self.application.updater.stop()
                except Exception as e:
                    logger.debug(f"Error stopping updater: {e}")
            
            # Stop and shutdown application
            if self.application:
                try:
                    await self.application.stop()
                except Exception as e:
                    logger.debug(f"Error stopping application: {e}")
                    
                try:
                    await self.application.shutdown()
                except Exception as e:
                    logger.debug(f"Error shutting down application: {e}")
            
            self.is_running = False
            logger.info("✅ Telegram bot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
            self.is_running = False
    
    async def send_message(self, text: str, reply_markup=None, parse_mode='Markdown'):
        """Send message to Telegram chat"""
        if not self.application:
            return
        
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    # ==================== COMMAND HANDLERS ====================
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="status"),
                InlineKeyboardButton("💼 Positions", callback_data="positions")
            ],
            [
                InlineKeyboardButton("📈 Trades", callback_data="trades"),
                InlineKeyboardButton("💰 PnL", callback_data="pnl")
            ],
            [
                InlineKeyboardButton("🚀 START", callback_data="start_bot"),
                InlineKeyboardButton("🛑 STOP", callback_data="stop_bot")
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data="stats"),
                InlineKeyboardButton("📝 Logs", callback_data="logs")
            ],
            [
                InlineKeyboardButton("🤖 Train ML", callback_data="train")
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "🤖 *HYPERBOT ENTERPRISE CONTROL PANEL*\n\n"
            "Select an option below or use commands:\n\n"
            "📊 /status - Account & bot status\n"
            "💼 /positions - Active positions\n"
            "📈 /trades - Last 10 trades\n"
            "💰 /pnl - Daily PnL breakdown\n"
            "📊 /stats - Performance statistics\n"
            "❓ /help - Full command list"
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            uptime = datetime.now(timezone.utc) - self.session_start
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            
            # Bot status emoji
            status_emoji = "✅" if self.bot.is_running and not self.bot.is_paused else "⏸️" if self.bot.is_paused else "🛑"
            
            # Get account values safely
            account_value = float(self.bot.account_value)
            margin_used = float(self.bot.margin_used)
            available = account_value - margin_used
            margin_pct = (margin_used / account_value * 100) if account_value > 0 else 0
            
            message = (
                f"{status_emoji} *SYSTEM STATUS*\n\n"
                f"*Account:*\n"
                f"💰 Balance: ${account_value:.2f}\n"
                f"📊 Margin: ${margin_used:.2f}\n"
                f"✅ Available: ${available:.2f}\n"
                f"📈 Margin %: {margin_pct:.1f}%\n\n"
                f"*Trading:*\n"
                f"🎯 Status: {'ACTIVE' if self.bot.is_running and not self.bot.is_paused else 'PAUSED' if self.bot.is_paused else 'STOPPED'}\n"
                f"📊 Strategies: 2 (Swing 70% + Scalping)\n"
                f"🔄 Trades Today: {self.bot.trades_executed}\n"
                f"⏰ Uptime: {uptime_str}\n\n"
                f"*Risk:*\n"
                f"🛡️ Max Leverage: 5x\n"
                f"⚠️ Max Daily Loss: 5%\n"
                f"🔴 Kill Switch: {'ACTIVE' if hasattr(self.bot, 'kill_switch') and self.bot.kill_switch and hasattr(self.bot.kill_switch, 'is_triggered') and self.bot.kill_switch.is_triggered else 'STANDBY'}"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in /status command: {e}", exc_info=True)
            await update.message.reply_text(f"Error fetching status: {str(e)[:100]}")
    
    async def _cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        try:
            # Get account state which includes positions
            account = await self.bot.client.get_account_state()
            positions = account.get('positions', [])
            
            if not positions:
                message = "📭 *NO OPEN POSITIONS*\n\nAll positions are closed."
            else:
                message = "💼 *ACTIVE POSITIONS*\n\n"
                
                for pos in positions:
                    side_emoji = "🟢" if pos['side'] == 'long' else "🔴"
                    pnl_emoji = "✅" if pos['unrealized_pnl'] >= 0 else "❌"
                    
                    # Calculate PnL percentage
                    pnl_pct = 0
                    if pos['position_value'] > 0:
                        pnl_pct = (pos['unrealized_pnl'] / pos['position_value']) * 100
                    
                    # Get current price from market
                    current_price = await self.bot.client.get_market_price(pos['symbol'])
                    current_str = f"${float(current_price):.3f}" if current_price else "N/A"
                    
                    message += (
                        f"{side_emoji} *{pos['side'].upper()} {abs(pos['size']):.4f} {pos['symbol']}*\n"
                        f"💵 Entry: ${pos['entry_price']:.3f}\n"
                        f"📍 Current: {current_str}\n"
                        f"{pnl_emoji} PnL: ${pos['unrealized_pnl']:.2f} ({pnl_pct:+.2f}%)\n"
                        f"💰 Value: ${pos['position_value']:.2f}\n"
                        f"⚡ Leverage: {pos.get('leverage', 1)}x\n\n"
                    )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in /positions command: {e}", exc_info=True)
            await update.message.reply_text(f"Error fetching positions: {e}")
    
    async def _cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trades command"""
        try:
            # Fetch recent fills from HyperLiquid
            fills = self.bot.client.info.user_fills(self.bot.client.account_address)
            
            if not fills:
                message = "📭 *NO RECENT TRADES*\n\nNo trades executed yet."
            else:
                message = "📈 *LAST 10 TRADES*\n\n"
                
                # Group fills into trades (entry + exit pairs)
                trades = []
                temp_entries = {}
                
                for fill in fills[:30]:  # Look at last 30 fills
                    symbol = fill['coin']
                    side = 'long' if fill['side'] == 'B' else 'short'
                    
                    if fill['closedPnl'] != '0':
                        # This is a closing trade
                        pnl = float(fill['closedPnl'])
                        pnl_emoji = "✅" if pnl >= 0 else "❌"
                        time_str = datetime.fromtimestamp(fill['time'] / 1000, tz=timezone.utc).strftime('%m/%d %H:%M')
                        
                        trades.append({
                            'time': time_str,
                            'symbol': symbol,
                            'side': side,
                            'pnl': pnl,
                            'emoji': pnl_emoji
                        })
                
                # Display last 10 completed trades
                for i, trade in enumerate(trades[:10], 1):
                    side_emoji = "🟢" if trade['side'] == 'long' else "🔴"
                    message += (
                        f"{i}. {side_emoji} {trade['symbol']} | "
                        f"{trade['emoji']} ${trade['pnl']:+.2f} | "
                        f"{trade['time']}\n"
                    )
                
                # Summary
                if trades[:10]:
                    total_pnl = sum(t['pnl'] for t in trades[:10])
                    wins = sum(1 for t in trades[:10] if t['pnl'] > 0)
                    losses = sum(1 for t in trades[:10] if t['pnl'] < 0)
                    win_rate = (wins / len(trades[:10]) * 100) if trades[:10] else 0
                    
                    message += (
                        f"\n📊 *Summary (Last 10):*\n"
                        f"💰 Total: ${total_pnl:+.2f}\n"
                        f"✅ Wins: {wins} | ❌ Losses: {losses}\n"
                        f"📈 Win Rate: {win_rate:.1f}%"
                    )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"Error fetching trades: {e}")
    
    async def _cmd_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pnl command"""
        try:
            # Fetch fills from today
            fills = self.bot.client.info.user_fills(self.bot.client.account_address)
            
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_pnl = Decimal('0')
            today_fees = Decimal('0')
            today_trades = 0
            
            weekly_pnl = Decimal('0')
            week_start = now - timedelta(days=7)
            
            for fill in fills:
                fill_time = datetime.fromtimestamp(fill['time'] / 1000, tz=timezone.utc)
                closed_pnl = Decimal(str(fill.get('closedPnl', '0')))
                fee = Decimal(str(fill.get('fee', '0')))
                
                if fill_time >= today_start:
                    if closed_pnl != 0:
                        today_pnl += closed_pnl
                        today_trades += 1
                    today_fees += fee
                
                if fill_time >= week_start:
                    if closed_pnl != 0:
                        weekly_pnl += closed_pnl
            
            # Calculate percentages
            account_value = Decimal(str(self.bot.account_state.get('account_value', 1)))
            starting_balance = account_value - today_pnl  # Approximate
            
            today_pct = (today_pnl / starting_balance * 100) if starting_balance > 0 else Decimal('0')
            
            pnl_emoji = "✅" if today_pnl >= 0 else "❌"
            
            message = (
                f"💰 *PnL BREAKDOWN*\n\n"
                f"*Today:*\n"
                f"{pnl_emoji} Gross PnL: ${today_pnl:+.2f} ({today_pct:+.2f}%)\n"
                f"💸 Fees: ${today_fees:.2f}\n"
                f"💵 Net PnL: ${today_pnl - today_fees:+.2f}\n"
                f"🔄 Trades: {today_trades}\n\n"
                f"*Last 7 Days:*\n"
                f"💰 Total PnL: ${weekly_pnl:+.2f}\n\n"
                f"*Session:*\n"
                f"⏰ Started: {self.session_start.strftime('%m/%d %H:%M UTC')}\n"
                f"🎯 Total Trades: {self.bot.trades_executed}"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"Error calculating PnL: {e}")
    
    async def _cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            # Get strategy statistics
            stats = self.bot.strategy.get_statistics()
            
            message = (
                f"📊 *PERFORMANCE STATISTICS*\n\n"
                f"*Strategy Performance:*\n"
            )
            
            for name, breakdown in stats.get('strategy_breakdown', {}).items():
                message += (
                    f"• {name.title()}: "
                    f"{breakdown['signals']} signals, "
                    f"{breakdown['trades']} trades\n"
                )
            
            message += (
                f"\n*Execution:*\n"
                f"📊 Total Signals: {stats.get('total_signals', 0)}\n"
                f"✅ Executed: {stats.get('total_trades', 0)}\n"
                f"📈 Rate: {stats.get('execution_rate', 0):.1%}\n\n"
                f"*System:*\n"
                f"🤖 Mode: ENTERPRISE (70% target)\n"
                f"🎯 Active: Swing + Scalping\n"
                f"⏰ Uptime: {str(datetime.now(timezone.utc) - self.session_start).split('.')[0]}"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"Error fetching statistics: {e}")
    
    async def _cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs command - show recent bot logs"""
        try:
            from datetime import datetime
            import os
            
            # Get today's log file
            log_date = datetime.now().strftime('%Y%m%d')
            log_file = f"/workspaces/hyperbot/logs/bot_{log_date}.log"
            
            if not os.path.exists(log_file):
                # Try alternative locations
                alt_locations = [
                    f"/root/hyperbot/logs/bot_{log_date}.log",
                    "./logs/bot.log",
                    "./logs/bot_output.log"
                ]
                
                for alt_file in alt_locations:
                    if os.path.exists(alt_file):
                        log_file = alt_file
                        break
                else:
                    await update.message.reply_text(
                        f"📭 No log file found for today ({log_date})\n\n"
                        "This is normal if:\n"
                        "• Bot is running on VPS (logs at /root/hyperbot/logs/)\n"
                        "• Using PM2 (check with: pm2 logs hyperbot)\n"
                        "• No activity today yet"
                    )
                    return
            
            # Read last 50 lines
            with open(log_file, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
            
            # Filter and format logs
            formatted_logs = []
            for line in last_lines:
                # Extract key parts
                if ' - INFO - ' in line:
                    emoji = "ℹ️"
                elif ' - WARNING - ' in line:
                    emoji = "⚠️"
                elif ' - ERROR - ' in line:
                    emoji = "❌"
                else:
                    continue
                
                # Extract timestamp and message
                parts = line.split(' - ', 3)
                if len(parts) >= 4:
                    time = parts[0].split(' ')[1].split(',')[0]  # Extract HH:MM:SS
                    msg = parts[3].strip()
                    
                    # Truncate long messages
                    if len(msg) > 100:
                        msg = msg[:97] + "..."
                    
                    # Escape HTML special characters
                    msg = msg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    
                    formatted_logs.append(f"{emoji} <code>{time}</code> {msg}")
            
            # Split into chunks if too long (Telegram has 4096 char limit)
            log_text = "\n".join(formatted_logs[-30:])  # Last 30 formatted lines
            
            message = (
                f"📝 <b>LIVE LOGS</b> (Last 30 entries)\n\n"
                f"{log_text}\n\n"
                f"<i>Full logs: logs/bot_{log_date}.log</i>"
            )
            
            # Handle message length
            if len(message) > 4000:
                # Split into multiple messages
                chunks = [formatted_logs[i:i+15] for i in range(0, len(formatted_logs[-30:]), 15)]
                for i, chunk in enumerate(chunks):
                    chunk_msg = f"📝 <b>LIVE LOGS</b> (Part {i+1}/{len(chunks)})\n\n" + "\n".join(chunk)
                    await update.message.reply_text(chunk_msg, parse_mode='HTML')
            else:
                await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in /logs command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error reading logs: {str(e)[:100]}")
    
    async def _cmd_train(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /train command - trigger ML retraining"""
        try:
            await update.message.reply_text(
                "🤖 *ML TRAINING CHECK*\n\n"
                "Checking if retraining is needed...\n"
                "This may take a few moments.",
                parse_mode='Markdown'
            )
            
            # Import auto-trainer
            from ml.auto_trainer import AutoTrainer
            trainer = AutoTrainer(min_trades_for_retrain=100)
            
            # Check and train
            triggered = await trainer.check_and_train(self)
            
            if not triggered:
                # Get current stats
                current_count = trainer._count_trades()
                new_trades = current_count - trainer.last_trade_count
                needed = trainer.min_trades - new_trades
                
                await update.message.reply_text(
                    f"ℹ️ *TRAINING NOT NEEDED*\n\n"
                    f"New trades: {new_trades}/{trainer.min_trades}\n"
                    f"Need {needed} more trades for retraining.\n\n"
                    f"Auto-training runs every 24 hours.",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error in /train command: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ *TRAINING ERROR*\n\n"
                f"Failed to trigger training: {str(e)[:200]}\n\n"
                f"Check logs for details.",
                parse_mode='Markdown'
            )
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            message = (
                "❓ <b>HELP - AVAILABLE COMMANDS</b>\n\n"
                "<b>📊 Monitoring:</b>\n"
                "/status - Bot and account status\n"
                "/positions - Active open positions\n"
                "/trades - Last 10 completed trades\n"
                "/pnl - Daily and weekly PnL\n"
                "/balance - Quick balance check\n"
                "/stats - Performance statistics\n"
                "/logs - Recent live logs\n\n"
                "<b>📈 Market Info:</b>\n"
                "/market - Current market overview\n"
                "/regime - Market regime analysis\n"
                "/session - Current trading session\n\n"
                "<b>📉 Position Control:</b>\n"
                "/close [symbol] - Close specific position\n"
                "/closeall - Close all positions (⚠️ careful!)\n\n"
                "<b>📊 Analytics:</b>\n"
                "/analytics - Full performance dashboard\n"
                "/analytics daily - Last 30 days breakdown\n"
                "/analytics symbols - Best trading pairs\n"
                "/dbstats - Database health and size\n\n"
                "<b>🤖 ML Training:</b>\n"
                "/train - Trigger ML model retraining\n\n"
                "<b>🎛️ Control Buttons:</b>\n"
                "🚀 START - Resume trading\n"
                "🛑 STOP - Pause trading\n\n"
                "<b>ℹ️ Notes:</b>\n"
                "• Real-time signal notifications\n"
                "• PnL warnings at key levels\n"
                "• Hourly status updates (configurable)\n\n"
                "🎯 Target: 70% win rate | 3.5:1 R:R"
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in /help command: {e}", exc_info=True)
            await update.message.reply_text("Error displaying help. Please try again.")
    
    # ==================== NEW ENHANCED COMMANDS ====================
    
    async def _cmd_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /market command - Show current market overview"""
        try:
            symbol = self.bot.symbol
            
            # Get current price
            current_price = await self.bot.client.get_market_price(symbol)
            
            # Get 24h data if available
            candles = self.bot.current_candles if hasattr(self.bot, 'current_candles') else []
            
            if candles and len(candles) > 0:
                high_24h = max(c['high'] for c in candles[-1440:]) if len(candles) >= 1440 else max(c['high'] for c in candles)
                low_24h = min(c['low'] for c in candles[-1440:]) if len(candles) >= 1440 else min(c['low'] for c in candles)
                open_24h = candles[-min(1440, len(candles))]['open']
                change_24h = ((float(current_price) - open_24h) / open_24h * 100) if open_24h else 0
                change_emoji = "📈" if change_24h >= 0 else "📉"
            else:
                high_24h = low_24h = current_price
                change_24h = 0
                change_emoji = "➖"
            
            message = (
                f"📊 *MARKET OVERVIEW - {symbol}*\n\n"
                f"💵 Price: ${float(current_price):.4f}\n"
                f"{change_emoji} 24h Change: {change_24h:+.2f}%\n"
                f"📈 24h High: ${float(high_24h):.4f}\n"
                f"📉 24h Low: ${float(low_24h):.4f}\n\n"
                f"🕐 Time: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in /market command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error fetching market data: {str(e)[:100]}")
    
    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command - Quick balance check"""
        try:
            account_value = float(self.bot.account_value)
            margin_used = float(self.bot.margin_used)
            available = account_value - margin_used
            
            emoji = "🟢" if margin_used == 0 else "🟡" if margin_used < account_value * 0.5 else "🔴"
            
            message = (
                f"💰 *BALANCE*\n\n"
                f"{emoji} Total: ${account_value:.2f}\n"
                f"📊 Margin: ${margin_used:.2f}\n"
                f"✅ Available: ${available:.2f}"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    async def _cmd_regime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /regime command - Show current market regime"""
        try:
            if hasattr(self.bot, 'strategy') and hasattr(self.bot.strategy, 'strategies'):
                # Get regime from world-class swing strategy
                for name, strategy in self.bot.strategy.strategies.items():
                    if hasattr(strategy, 'regime_detector'):
                        candles = self.bot.current_candles if hasattr(self.bot, 'current_candles') else []
                        if candles:
                            regime = strategy.regime_detector.detect(candles)
                            
                            regime_emoji = {
                                'trending_up': '📈🟢',
                                'trending_down': '📉🔴', 
                                'ranging': '↔️🟡',
                                'volatile': '⚡🟠',
                                'breakout': '🚀💥'
                            }.get(regime.regime_type, '❓')
                            
                            message = (
                                f"🧠 *MARKET REGIME ANALYSIS*\n\n"
                                f"{regime_emoji} Regime: {regime.regime_type.upper()}\n"
                                f"📊 Confidence: {regime.confidence:.0%}\n"
                                f"📈 ADX: {regime.adx:.1f}\n"
                                f"⚡ Volatility: {'High' if regime.volatility > 1.5 else 'Normal' if regime.volatility > 0.8 else 'Low'}\n"
                                f"📊 Trend Strength: {regime.trend_strength:.0%}\n\n"
                                f"💡 Strategy: {regime.preferred_strategy}"
                            )
                            
                            await update.message.reply_text(message, parse_mode='Markdown')
                            return
            
            await update.message.reply_text("❌ Regime detector not available")
            
        except Exception as e:
            logger.error(f"Error in /regime command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    async def _cmd_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /session command - Show current trading session"""
        try:
            if hasattr(self.bot, 'strategy') and hasattr(self.bot.strategy, 'strategies'):
                for name, strategy in self.bot.strategy.strategies.items():
                    if hasattr(strategy, 'session_manager'):
                        session = strategy.session_manager.get_current_session()
                        params = strategy.session_manager.get_session_params()
                        
                        session_emoji = {
                            'asian': '🌏',
                            'london': '🇬🇧',
                            'us_morning': '🇺🇸',
                            'us_afternoon': '🌆',
                            'off_hours': '🌙'
                        }.get(session, '❓')
                        
                        message = (
                            f"⏰ *TRADING SESSION*\n\n"
                            f"{session_emoji} Session: {session.upper()}\n\n"
                            f"*Parameters:*\n"
                            f"📊 Size Multiplier: {params.get('size_multiplier', 1):.2f}x\n"
                            f"⚡ Volatility Factor: {params.get('volatility_factor', 1):.2f}x\n"
                            f"🎯 Min Score Adjust: {params.get('min_score_adjust', 0):+d}\n"
                            f"⏱️ Trade Frequency: {params.get('trade_frequency', 'normal')}\n"
                            f"🛡️ Should Trade: {'Yes ✅' if params.get('should_trade', True) else 'No ❌'}\n\n"
                            f"🕐 UTC Time: {datetime.now(timezone.utc).strftime('%H:%M')}"
                        )
                        
                        await update.message.reply_text(message, parse_mode='Markdown')
                        return
            
            await update.message.reply_text("❌ Session manager not available")
            
        except Exception as e:
            logger.error(f"Error in /session command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    async def _cmd_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /close command - Close a specific position"""
        try:
            args = context.args
            if not args:
                await update.message.reply_text(
                    "⚠️ Usage: /close [symbol]\n\n"
                    "Example: /close SOL",
                    parse_mode='Markdown'
                )
                return
            
            symbol = args[0].upper()
            
            # Get current position
            positions = self.bot.client.get_open_positions()
            pos = next((p for p in positions if p['symbol'] == symbol), None)
            
            if not pos:
                await update.message.reply_text(f"❌ No open position for {symbol}")
                return
            
            # Confirm close
            keyboard = [
                [
                    InlineKeyboardButton(f"✅ Close {symbol}", callback_data=f"confirm_close_{symbol}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_close")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            pnl_emoji = "🟢" if pos['unrealized_pnl'] >= 0 else "🔴"
            message = (
                f"⚠️ *CONFIRM CLOSE POSITION*\n\n"
                f"📊 {pos['side'].upper()} {abs(pos['size']):.4f} {symbol}\n"
                f"{pnl_emoji} Unrealized PnL: ${pos['unrealized_pnl']:+.2f}\n\n"
                f"Are you sure you want to close this position?"
            )
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in /close command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    async def _cmd_closeall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /closeall command - Close all positions"""
        try:
            positions = self.bot.client.get_open_positions()
            
            if not positions:
                await update.message.reply_text("📭 No open positions to close")
                return
            
            # Confirm close all
            keyboard = [
                [
                    InlineKeyboardButton("⚠️ CLOSE ALL", callback_data="confirm_closeall"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_close")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            total_pnl = sum(p['unrealized_pnl'] for p in positions)
            pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
            
            message = (
                f"⚠️ *CONFIRM CLOSE ALL POSITIONS*\n\n"
                f"📊 Open Positions: {len(positions)}\n"
                f"{pnl_emoji} Total Unrealized PnL: ${total_pnl:+.2f}\n\n"
                f"⚠️ This will close ALL positions!\n"
                f"Are you sure?"
            )
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in /closeall command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}")
    
    # ==================== SCHEDULED TASKS ====================
    
    async def _scheduled_status_updates(self):
        """Send periodic status updates"""
        try:
            while self.is_running:
                await asyncio.sleep(self.status_update_interval)
                
                if not self.is_running:
                    break
                
                # Build status message
                account_value = float(self.bot.account_value)
                margin_used = float(self.bot.margin_used)
                uptime = datetime.now(timezone.utc) - self.session_start
                
                positions = self.bot.client.get_open_positions() if self.bot.client else []
                total_pnl = sum(p['unrealized_pnl'] for p in positions) if positions else 0
                pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
                
                message = (
                    f"📊 *HOURLY STATUS UPDATE*\n\n"
                    f"💰 Balance: ${account_value:.2f}\n"
                    f"📊 Positions: {len(positions)}\n"
                    f"{pnl_emoji} Unrealized PnL: ${total_pnl:+.2f}\n"
                    f"🔄 Trades Today: {self.bot.trades_executed}\n"
                    f"⏰ Uptime: {str(uptime).split('.')[0]}\n"
                    f"🎯 Status: {'ACTIVE ✅' if self.bot.is_running and not self.bot.is_paused else 'PAUSED ⏸️'}"
                )
                
                await self.send_message(message)
                
        except asyncio.CancelledError:
            pass  # Normal shutdown
        except Exception as e:
            logger.error(f"Error in scheduled status updates: {e}")
    
    def _can_send_message(self, message_type: str) -> bool:
        """Rate limiting check"""
        now = datetime.now(timezone.utc)
        last_time = self._last_message_time.get(message_type)
        
        if last_time and (now - last_time) < self._message_cooldown:
            return False
        
        self._last_message_time[message_type] = now
        return True
    
    # ==================== CALLBACK HANDLERS ====================
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        action = query.data
        
        if action == "status":
            await self._send_status(query)
        elif action == "positions":
            await self._send_positions(query)
        elif action == "trades":
            await self._send_trades(query)
        elif action == "pnl":
            await self._send_pnl(query)
        elif action == "stats":
            await self._send_stats(query)
        elif action == "help":
            await self._send_help(query)
        elif action == "start_bot":
            await self._handle_start_bot(query)
        elif action == "stop_bot":
            await self._handle_stop_bot(query)
        elif action.startswith("confirm_close_"):
            await self._handle_confirm_close(query, action.replace("confirm_close_", ""))
        elif action == "confirm_closeall":
            await self._handle_confirm_closeall(query)
        elif action == "cancel_close":
            await query.edit_message_text("❌ Close cancelled", parse_mode='Markdown')
    
    async def _handle_confirm_close(self, query, symbol: str):
        """Handle confirmed position close"""
        try:
            # Get position
            positions = self.bot.client.get_open_positions()
            pos = next((p for p in positions if p['symbol'] == symbol), None)
            
            if not pos:
                await query.edit_message_text(f"❌ Position {symbol} already closed")
                return
            
            # Close position using market order
            side = 'sell' if pos['side'] == 'long' else 'buy'
            size = abs(pos['size'])
            
            await query.edit_message_text(f"⏳ Closing {symbol} position...")
            
            result = await self.bot.client.market_close(symbol, size, side)
            
            if result.get('status') == 'ok':
                await query.edit_message_text(
                    f"✅ *POSITION CLOSED*\n\n"
                    f"📊 {pos['side'].upper()} {size:.4f} {symbol}\n"
                    f"💰 Realized PnL: ~${pos['unrealized_pnl']:+.2f}",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(f"❌ Failed to close: {result}")
                
        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    
    async def _handle_confirm_closeall(self, query):
        """Handle confirmed close all positions"""
        try:
            positions = self.bot.client.get_open_positions()
            
            if not positions:
                await query.edit_message_text("📭 No positions to close")
                return
            
            await query.edit_message_text(f"⏳ Closing {len(positions)} positions...")
            
            closed = 0
            total_pnl = 0
            
            for pos in positions:
                try:
                    side = 'sell' if pos['side'] == 'long' else 'buy'
                    size = abs(pos['size'])
                    
                    result = await self.bot.client.market_close(pos['symbol'], size, side)
                    
                    if result.get('status') == 'ok':
                        closed += 1
                        total_pnl += pos['unrealized_pnl']
                except Exception as e:
                    logger.error(f"Error closing {pos['symbol']}: {e}")
            
            pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
            await query.edit_message_text(
                f"✅ *ALL POSITIONS CLOSED*\n\n"
                f"📊 Closed: {closed}/{len(positions)}\n"
                f"{pnl_emoji} Total PnL: ${total_pnl:+.2f}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error closing all positions: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    
    async def _handle_start_bot(self, query):
        """Handle START button"""
        if self.bot.is_paused:
            self.bot.resume()
            await query.edit_message_text(
                "🚀 *BOT STARTED*\n\n"
                "Trading has been resumed.\n"
                "Monitoring markets for signals...",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "✅ Bot is already running!",
                parse_mode='Markdown'
            )
    
    async def _handle_stop_bot(self, query):
        """Handle STOP button"""
        if not self.bot.is_paused:
            self.bot.pause()
            await query.edit_message_text(
                "🛑 *BOT STOPPED*\n\n"
                "Trading has been paused.\n"
                "No new positions will be opened.\n"
                "Use 🚀 START to resume.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "⏸️ Bot is already paused!",
                parse_mode='Markdown'
            )
    
    async def _send_status(self, query):
        """Send status via callback"""
        try:
            account = self.bot.account_state
            message = (
                f"📊 *QUICK STATUS*\n\n"
                f"💰 Balance: ${account.get('account_value', 0):.2f}\n"
                f"📊 Margin: ${account.get('margin_used', 0):.2f}\n"
                f"🎯 Status: {'ACTIVE' if self.bot.is_running else 'STOPPED'}\n"
                f"🔄 Trades: {self.bot.trades_executed}"
            )
            await query.edit_message_text(message, parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"Error: {e}")
    
    async def _send_positions(self, query):
        """Send positions via callback"""
        try:
            positions = self.bot.client.get_open_positions()
            
            if not positions:
                message = "📭 No open positions"
            else:
                message = "💼 *POSITIONS*\n\n"
                for pos in positions[:3]:  # Show max 3
                    pnl_pct = (pos['unrealized_pnl'] / pos['position_value']) * 100
                    message += f"{pos['side'].upper()} {pos['symbol']}: ${pos['unrealized_pnl']:+.2f} ({pnl_pct:+.1f}%)\n"
            
            await query.edit_message_text(message, parse_mode='Markdown')
        except Exception as e:
            await query.edit_message_text(f"Error: {e}")
    
    async def _send_trades(self, query):
        """Send trades via callback"""
        await query.edit_message_text("📈 Use /trades for detailed trade history", parse_mode='Markdown')
    
    async def _send_pnl(self, query):
        """Send PnL via callback"""
        await query.edit_message_text("💰 Use /pnl for detailed PnL breakdown", parse_mode='Markdown')
    
    async def _send_stats(self, query):
        """Send stats via callback"""
        await query.edit_message_text("📊 Use /stats for full performance statistics", parse_mode='Markdown')
    
    async def _send_help(self, query):
        """Send help via callback"""
        await query.edit_message_text("❓ Use /help for full command list", parse_mode='Markdown')
    
    # ==================== NOTIFICATION METHODS ====================
    
    async def notify_signal(self, signal: Dict[str, Any]):
        """Send notification for new trading signal"""
        side_emoji = "🟢" if signal['side'] == 'buy' else "🔴"
        
        message = (
            f"{side_emoji} *NEW SIGNAL: {signal['side'].upper()} {signal['symbol']}*\n\n"
            f"💵 Entry: ${signal['entry_price']:.3f}\n"
            f"📊 Size: {signal['size']:.2f} ({signal['leverage']}x)\n"
            f"🎯 TP: ${signal['take_profit']:.3f} (+{signal.get('tp_pct', 3)}%)\n"
            f"🛡️ SL: ${signal['stop_loss']:.3f} (-{signal.get('sl_pct', 1)}%)\n"
            f"⭐ Score: {signal.get('signal_score', 0)}/{signal.get('max_score', 8)}\n\n"
            f"📝 Reason: {signal.get('reason', 'N/A')}"
        )
        
        await self.send_message(message)
    
    async def _cmd_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analytics command - Database analytics dashboard"""
        try:
            # Check if database is available
            if not self.bot.db:
                await update.message.reply_text(
                    "❌ Database not connected\n\n"
                    "Add DATABASE_URL to .env and restart bot.\n"
                    "See NEONDB_SETUP.md for instructions.",
                    parse_mode='Markdown'
                )
                return
            
            # Get query type from command args
            args = context.args
            query_type = args[0] if args else "full"
            
            # Import analytics
            from app.database.analytics import AnalyticsDashboard, format_analytics_message
            
            await update.message.reply_text("📊 Generating analytics report...", parse_mode='Markdown')
            
            # Generate report
            dashboard = AnalyticsDashboard(self.bot.db)
            report = await format_analytics_message(dashboard, query_type)
            
            # Send report (split if too long)
            if len(report) > 4000:
                chunks = [report[i:i+4000] for i in range(0, len(report), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode='Markdown')
            else:
                await update.message.reply_text(report, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Analytics command error: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error generating analytics:\n{str(e)}",
                parse_mode='Markdown'
            )
    
    async def _cmd_dbstats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dbstats command - Database health and statistics"""
        try:
            if not self.bot.db:
                await update.message.reply_text(
                    "❌ Database not connected",
                    parse_mode='Markdown'
                )
                return
            
            # Get database statistics
            stats = await self.bot.db.get_total_stats()
            
            # Count open trades
            open_trades = await self.bot.db.get_open_trades()
            
            # Handle empty stats
            if not stats or stats.get('total_trades') == 0:
                message = [
                    "📊 **DATABASE STATISTICS**",
                    "=" * 35,
                    "",
                    "✅ Status: Connected",
                    "📝 Total Trades: 0",
                    "📂 Open Positions: 0",
                    "",
                    "💡 No trades recorded yet.",
                    "Start trading to see analytics!",
                    "",
                    "Use /analytics for detailed reports"
                ]
            else:
                message = [
                    "📊 **DATABASE STATISTICS**",
                    "=" * 35,
                    "",
                    f"✅ Status: Connected",
                    f"📝 Total Trades: {int(stats.get('total_trades', 0))}",
                    f"📂 Open Positions: {len(open_trades)}",
                    f"✅ Wins: {int(stats.get('winning_trades', 0))}",
                    f"❌ Losses: {int(stats.get('losing_trades', 0))}",
                    f"📈 Win Rate: {float(stats.get('win_rate', 0)):.1f}%",
                    "",
                    f"💰 Total P&L: ${float(stats.get('total_pnl', 0)):+.2f}",
                    f"🏆 Best Trade: ${float(stats.get('best_trade', 0)):+.2f}",
                    f"📉 Worst Trade: ${float(stats.get('worst_trade', 0)):+.2f}",
                    "",
                    "Use /analytics for detailed reports"
                ]
            
            await update.message.reply_text("\n".join(message), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"DB stats command error: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error fetching DB stats:\n{str(e)}",
                parse_mode='Markdown'
            )
    
    async def notify_fill(self, fill_type: str, symbol: str, side: str, price: float, size: float):
        """Send notification for order fill"""
        emoji = "✅" if fill_type == 'entry' else "🏁"
        message = (
            f"{emoji} *{fill_type.upper()}: {side.upper()} {symbol}*\n\n"
            f"💵 Price: ${price:.3f}\n"
            f"📊 Size: {size:.2f}"
        )
        
        await self.send_message(message)
    
    async def notify_pnl_warning(self, position: Dict[str, Any], warning_type: str):
        """Send warning for position approaching SL or TP"""
        if warning_type == 'sl':
            emoji = "⚠️"
            msg_type = "STOP LOSS APPROACHING"
        else:
            emoji = "🎯"
            msg_type = "TAKE PROFIT APPROACHING"
        
        pnl_pct = (position['unrealized_pnl'] / position['position_value']) * 100
        
        message = (
            f"{emoji} *{msg_type}*\n\n"
            f"📊 {position['side'].upper()} {position['symbol']}\n"
            f"💰 PnL: ${position['unrealized_pnl']:+.2f} ({pnl_pct:+.2f}%)\n"
            f"💵 Entry: ${position['entry_price']:.3f}\n"
            f"📍 Current: ${position['mark_price']:.3f}"
        )
        
        await self.send_message(message)
    
    async def notify_trade_closed(self, symbol: str, side: str, pnl: float, pnl_pct: float):
        """Send notification when trade is closed"""
        emoji = "✅" if pnl >= 0 else "❌"
        result = "WIN" if pnl >= 0 else "LOSS"
        
        message = (
            f"{emoji} *TRADE CLOSED - {result}*\n\n"
            f"📊 {side.upper()} {symbol}\n"
            f"💰 PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)\n\n"
            f"🔄 Session Trades: {self.bot.trades_executed}"
        )
        
        await self.send_message(message)
    
    async def notify_emergency(self, message: str):
        """Send emergency notification"""
        alert = f"🚨 *EMERGENCY ALERT*\n\n{message}"
        await self.send_message(alert)
