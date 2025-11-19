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
        
        logger.info("📱 Telegram Bot initialized")
        logger.info(f"   Chat ID: {self.chat_id}")
    
    async def start(self):
        """Start the Telegram bot"""
        if self.is_running:
            return
        
        try:
            # Build application
            self.application = Application.builder().token(self.token).build()
            
            # Register handlers
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
            self.application.add_handler(CallbackQueryHandler(self._handle_callback))
            
            # Start bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            
            # Send startup message
            await self.send_message(
                "🚀 *ENTERPRISE BOT STARTED*\n\n"
                f"✅ Connected to trading system\n"
                f"💰 Account: ${self.bot.account_value:.2f}\n"
                f"🎯 Strategies: Swing (70%) + Scalping\n"
                f"⏰ Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                "Use /help for commands"
            )
            
            logger.info("✅ Telegram bot started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            raise
    
    async def stop(self):
        """Stop the Telegram bot"""
        if not self.is_running or not self.application:
            return
        
        try:
            await self.send_message("🛑 *BOT STOPPING*\n\nTelegram bot shutting down...")
            
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            self.is_running = False
            logger.info("✅ Telegram bot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
    
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
                "<b>Monitoring:</b>\n"
                "/status - Bot and account status\n"
                "/positions - Active open positions\n"
                "/trades - Last 10 completed trades\n"
                "/pnl - Daily and weekly PnL\n"
                "/stats - Performance statistics\n"
                "/logs - Recent live logs (last 50 lines)\n\n"
                "<b>Analytics:</b>\n"
                "/analytics - Full performance dashboard\n"
                "/analytics daily - Last 30 days breakdown\n"
                "/analytics symbols - Best trading pairs\n"
                "/analytics hours - Optimal trading hours\n"
                "/analytics ml - ML model accuracy\n"
                "/dbstats - Database health and size\n\n"
                "<b>ML Training:</b>\n"
                "/train - Trigger ML model retraining\n\n"
                "<b>Control:</b>\n"
                "Use the inline buttons for:\n"
                "🚀 START - Resume trading\n"
                "🛑 STOP - Pause trading\n\n"
                "<b>Notes:</b>\n"
                "• Real-time updates on signals\n"
                "• Emergency alerts for big moves\n"
                "• Risk warnings at -0.8% PnL\n"
                "• TP notifications at +1.6% PnL\n"
                "• PostgreSQL analytics (if DATABASE_URL set)\n\n"
                "🎯 Target: 70% win rate | 3:1 R:R"
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in /help command: {e}", exc_info=True)
            await update.message.reply_text("Error displaying help. Please try again.")
    
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
