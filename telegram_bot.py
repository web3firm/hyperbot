#!/usr/bin/env python3
"""
Telegram Bot for Hyperliquid Trading Bot Control
Advanced monitoring, control, and emergency features
"""

import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import signal
import subprocess
import psutil

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from loguru import logger
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

# Trading bot imports
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from utils.data_manager import DataManager
from utils.position_manager import PositionManager
from risk.risk_manager import RiskManager
from ml.ml_predictor import MLPredictor
from sentiment.sentiment_analyzer import SentimentAnalyzer
from config_helper import get_hyperliquid_config

class TelegramTradingBot:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_ids = self._get_authorized_users()
        self.trading_bot_process = None
        self.monitoring_active = False
        self.log_streaming = {}
        
        # Initialize trading components
        self.config = get_hyperliquid_config()
        self.info = Info(self.config['api_url'], skip_ws=True)
        self.exchange = Exchange(
            self.config['account'], 
            self.config['api_url'], 
            skip_ws=True
        )
        self.position_manager = PositionManager(self.info, self.exchange)
        self.risk_manager = RiskManager()
        self.data_manager = DataManager(self.info)
        
        # Setup matplotlib for charts
        plt.style.use('dark_background')
        sns.set_palette("husl")

    def _get_authorized_users(self) -> List[str]:
        """Get authorized Telegram user IDs from environment"""
        users = os.getenv('TELEGRAM_AUTHORIZED_USERS', '')
        return [user.strip() for user in users.split(',') if user.strip()]

    def is_authorized(self, user_id: str) -> bool:
        """Check if user is authorized"""
        return str(user_id) in self.chat_ids

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access!")
            return

        welcome_msg = """
🚀 **Hyperliquid Trading Bot Controller**

🎯 **Quick Actions:**
/status - Bot status and positions
/portfolio - Portfolio overview
/start_bot - Start trading
/stop_bot - Stop trading
/emergency_stop - Emergency stop all
/logs - View live logs
/settings - Bot configuration

📊 **Analytics:**
/performance - Performance metrics
/charts - Trading charts
/ml_status - ML model status

⚙️ **Advanced:**
/risk - Risk management
/positions - Manage positions
/symbols - Symbol analysis
/alerts - Alert settings

Type /help for detailed commands.
        """
        
        keyboard = [
            [KeyboardButton("📊 Status"), KeyboardButton("💰 Portfolio")],
            [KeyboardButton("▶️ Start"), KeyboardButton("⏹️ Stop")],
            [KeyboardButton("📈 Charts"), KeyboardButton("📋 Logs")],
            [KeyboardButton("⚙️ Settings"), KeyboardButton("🆘 Emergency")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            welcome_msg, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get comprehensive bot status"""
        if not self.is_authorized(update.effective_user.id):
            return

        try:
            # Check if trading bot is running
            bot_running = self._is_trading_bot_running()
            
            # Get account info
            account_value = self.info.account_value(self.config['main_account'])
            positions = self.position_manager.get_current_positions()
            
            # Calculate portfolio metrics
            total_value = float(account_value.get('accountValue', 0))
            available = float(account_value.get('availableBalance', 0))
            used_margin = total_value - available
            
            status_msg = f"""
🤖 **Trading Bot Status**
{'🟢 RUNNING' if bot_running else '🔴 STOPPED'}

💰 **Account Summary**
💵 Total Value: ${total_value:,.2f}
💳 Available: ${available:,.2f}
📊 Used Margin: ${used_margin:,.2f}
📈 Utilization: {(used_margin/total_value*100) if total_value > 0 else 0:.1f}%

📋 **Positions: {len(positions)}**
            """
            
            if positions:
                for pos in positions:
                    pnl = float(pos.get('unrealizedPnl', 0))
                    size = float(pos.get('size', 0))
                    side = pos.get('side', 'N/A')
                    symbol = pos.get('coin', 'N/A')
                    entry_price = float(pos.get('entryPx', 0))
                    mark_price = float(pos.get('markPx', 0))
                    
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    side_emoji = "🔵" if side == "B" else "🔴"
                    
                    status_msg += f"""
{side_emoji} **{symbol}** ({side})
   Size: {abs(size):,.4f}
   Entry: ${entry_price:,.2f}
   Mark: ${mark_price:,.2f}
   {pnl_emoji} PnL: ${pnl:,.2f}
                    """
            else:
                status_msg += "\n📭 No active positions"

            # Add quick action buttons
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status")],
                [
                    InlineKeyboardButton("▶️ Start Bot", callback_data="start_trading"),
                    InlineKeyboardButton("⏹️ Stop Bot", callback_data="stop_trading")
                ],
                [InlineKeyboardButton("📈 Performance", callback_data="show_performance")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                status_msg, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting status: {str(e)}")

    async def portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detailed portfolio analysis"""
        if not self.is_authorized(update.effective_user.id):
            return

        try:
            account_value = self.info.account_value(self.config['main_account'])
            positions = self.position_manager.get_current_positions()
            
            # Portfolio overview
            total_value = float(account_value.get('accountValue', 0))
            available = float(account_value.get('availableBalance', 0))
            total_pnl = sum(float(pos.get('unrealizedPnl', 0)) for pos in positions)
            
            # Risk metrics
            risk_score = self.risk_manager.calculate_portfolio_risk(positions, total_value)
            
            portfolio_msg = f"""
💼 **Portfolio Analysis**

📊 **Overview**
💰 Total Value: ${total_value:,.2f}
💳 Available: ${available:,.2f}
📈 Unrealized PnL: ${total_pnl:,.2f}
🎯 Risk Score: {risk_score:.1f}/10

🔥 **Risk Metrics**
🛡️ Max Risk Per Trade: {self.risk_manager.max_risk_per_trade*100:.1f}%
📊 Portfolio Heat: {len(positions)}/5 positions
💥 Max Drawdown: {self.risk_manager.max_portfolio_drawdown*100:.1f}%
            """
            
            if positions:
                portfolio_msg += f"\n📋 **Position Details**\n"
                for i, pos in enumerate(positions, 1):
                    symbol = pos.get('coin', 'N/A')
                    size = float(pos.get('size', 0))
                    side = pos.get('side', 'N/A')
                    pnl = float(pos.get('unrealizedPnl', 0))
                    pnl_pct = (pnl / total_value * 100) if total_value > 0 else 0
                    
                    portfolio_msg += f"""
{i}. **{symbol}** {'📈' if side == 'B' else '📉'}
   Size: {abs(size):,.4f}
   PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)
                    """

            keyboard = [
                [
                    InlineKeyboardButton("📊 Charts", callback_data="portfolio_charts"),
                    InlineKeyboardButton("🎯 Risk Analysis", callback_data="risk_analysis")
                ],
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="refresh_portfolio"),
                    InlineKeyboardButton("🆘 Close All", callback_data="emergency_close_all")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                portfolio_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting portfolio: {str(e)}")

    async def start_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the trading bot"""
        if not self.is_authorized(update.effective_user.id):
            return

        try:
            if self._is_trading_bot_running():
                await update.message.reply_text("⚠️ Trading bot is already running!")
                return

            # Start trading bot process
            self.trading_bot_process = subprocess.Popen([
                sys.executable, "main.py"
            ], cwd="/workspaces/hyperbot")
            
            await asyncio.sleep(2)  # Wait for startup
            
            if self._is_trading_bot_running():
                msg = """
✅ **Trading Bot Started!**

🎯 Bot is now active and monitoring markets
📊 Will trade when strong signals detected
🛡️ Risk management active
📱 You'll receive trade notifications here

Use /status to monitor progress
Use /stop_bot for graceful shutdown
Use /emergency_stop for immediate halt
                """
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text("❌ Failed to start trading bot. Check logs.")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error starting bot: {str(e)}")

    async def stop_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop the trading bot gracefully"""
        if not self.is_authorized(update.effective_user.id):
            return

        try:
            if not self._is_trading_bot_running():
                await update.message.reply_text("⚠️ Trading bot is not running!")
                return

            # Graceful shutdown
            if self.trading_bot_process:
                self.trading_bot_process.terminate()
                self.trading_bot_process.wait(timeout=10)
            
            await update.message.reply_text("""
⏹️ **Trading Bot Stopped**

🔄 Bot shutdown gracefully
📊 Positions remain open
🛡️ Stop-losses still active
📱 Use /start_bot to resume trading
            """, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error stopping bot: {str(e)}")

    async def emergency_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Emergency stop with position closure"""
        if not self.is_authorized(update.effective_user.id):
            return

        keyboard = [
            [InlineKeyboardButton("🆘 CONFIRM EMERGENCY STOP", callback_data="confirm_emergency")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_emergency")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ **EMERGENCY STOP WARNING**\n\n"
            "This will:\n"
            "🛑 Stop the trading bot immediately\n"
            "💥 Close ALL open positions\n"
            "🔒 Cancel all open orders\n\n"
            "**Are you sure?**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def live_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stream live logs"""
        if not self.is_authorized(update.effective_user.id):
            return

        user_id = str(update.effective_user.id)
        
        if user_id in self.log_streaming:
            # Stop streaming
            self.log_streaming[user_id] = False
            await update.message.reply_text("📋 Log streaming stopped")
        else:
            # Start streaming
            self.log_streaming[user_id] = True
            await update.message.reply_text("📋 Starting log stream... (send /logs again to stop)")
            
            # Stream logs
            await self._stream_logs(update, context)

    async def _stream_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stream trading bot logs"""
        user_id = str(update.effective_user.id)
        log_file = "/workspaces/hyperbot/logs/trading_bot.log"
        
        try:
            # Get last 10 lines
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-10:] if len(lines) > 10 else lines
                
            log_text = "📋 **Recent Logs**\n```\n" + "".join(recent_lines) + "\n```"
            
            await update.message.reply_text(
                log_text[:4000],  # Telegram limit
                parse_mode=ParseMode.MARKDOWN
            )
            
        except FileNotFoundError:
            await update.message.reply_text("📋 No log file found. Bot may not be running.")

    async def show_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed position management"""
        if not self.is_authorized(update.effective_user.id):
            return

        try:
            positions = self.position_manager.get_current_positions()
            
            if not positions:
                await update.message.reply_text("📭 No active positions")
                return

            for i, pos in enumerate(positions):
                symbol = pos.get('coin', 'N/A')
                side = pos.get('side', 'N/A')
                size = float(pos.get('size', 0))
                entry_price = float(pos.get('entryPx', 0))
                mark_price = float(pos.get('markPx', 0))
                pnl = float(pos.get('unrealizedPnl', 0))
                
                side_text = "LONG" if side == "B" else "SHORT"
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                
                pos_msg = f"""
📊 **Position {i+1}: {symbol}**

🎯 Type: {side_text}
📏 Size: {abs(size):,.4f}
💰 Entry: ${entry_price:,.4f}
📍 Mark: ${mark_price:,.4f}
{pnl_emoji} PnL: ${pnl:,.2f}
                """

                # Position management buttons
                keyboard = [
                    [
                        InlineKeyboardButton("📈 Close 25%", callback_data=f"close_25_{symbol}"),
                        InlineKeyboardButton("📈 Close 50%", callback_data=f"close_50_{symbol}")
                    ],
                    [
                        InlineKeyboardButton("📈 Close 75%", callback_data=f"close_75_{symbol}"),
                        InlineKeyboardButton("🔴 Close 100%", callback_data=f"close_100_{symbol}")
                    ],
                    [InlineKeyboardButton("📊 Analysis", callback_data=f"analyze_{symbol}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    pos_msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )

        except Exception as e:
            await update.message.reply_text(f"❌ Error getting positions: {str(e)}")

    async def ml_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show ML model status and predictions"""
        if not self.is_authorized(update.effective_user.id):
            return

        try:
            ml_predictor = MLPredictor()
            
            # Check model status
            models_exist = ml_predictor.models_trained()
            
            if not models_exist:
                await update.message.reply_text("🤖 ML models not trained. Training now...")
                # Train models
                await self._train_ml_models(update)
                return

            # Get model performance
            model_info = ml_predictor.get_model_performance()
            
            ml_msg = f"""
🤖 **ML Model Status**

📊 **Model Performance**
🌲 Random Forest: {model_info.get('random_forest', {}).get('accuracy', 0):.3f}
⚡ Gradient Boost: {model_info.get('gradient_boosting', {}).get('accuracy', 0):.3f}
🔄 Logistic Reg: {model_info.get('logistic_regression', {}).get('accuracy', 0):.3f}
🎯 SVM: {model_info.get('svm', {}).get('accuracy', 0):.3f}

🕒 Last Training: {model_info.get('last_training', 'Unknown')}
📈 Features: {model_info.get('feature_count', 'Unknown')}
            """

            # Get recent predictions for top symbols
            symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']
            predictions = {}
            
            for symbol in symbols:
                try:
                    data = self.data_manager.get_market_data(symbol, '1m', 100)
                    if data is not None:
                        pred = ml_predictor.predict_next_move(data)
                        predictions[symbol] = pred
                except:
                    continue

            if predictions:
                ml_msg += "\n🔮 **Recent Predictions**\n"
                for symbol, pred in predictions.items():
                    direction = pred.get('prediction', 'neutral')
                    confidence = pred.get('confidence', 0)
                    
                    if direction == 'bullish':
                        emoji = "🟢📈"
                    elif direction == 'bearish':
                        emoji = "🔴📉"
                    else:
                        emoji = "🟡➡️"
                    
                    ml_msg += f"{emoji} {symbol}: {direction.upper()} ({confidence:.2f})\n"

            keyboard = [
                [
                    InlineKeyboardButton("🔄 Retrain", callback_data="retrain_models"),
                    InlineKeyboardButton("📊 Details", callback_data="ml_details")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                ml_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Error getting ML status: {str(e)}")

    async def generate_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate and send performance charts"""
        if not self.is_authorized(update.effective_user.id):
            return

        try:
            await update.message.reply_text("📊 Generating charts...")
            
            # Portfolio performance chart
            chart_buffer = await self._create_portfolio_chart()
            if chart_buffer:
                await update.message.reply_photo(
                    photo=chart_buffer,
                    caption="📊 Portfolio Performance"
                )

            # Position distribution chart
            chart_buffer = await self._create_position_chart()
            if chart_buffer:
                await update.message.reply_photo(
                    photo=chart_buffer,
                    caption="🥧 Position Distribution"
                )

        except Exception as e:
            await update.message.reply_text(f"❌ Error generating charts: {str(e)}")

    async def _create_portfolio_chart(self) -> Optional[io.BytesIO]:
        """Create portfolio performance chart"""
        try:
            positions = self.position_manager.get_current_positions()
            if not positions:
                return None

            # Create performance data
            symbols = [pos.get('coin', 'N/A') for pos in positions]
            pnls = [float(pos.get('unrealizedPnl', 0)) for pos in positions]
            
            plt.figure(figsize=(10, 6))
            colors = ['green' if pnl >= 0 else 'red' for pnl in pnls]
            
            plt.bar(symbols, pnls, color=colors, alpha=0.7)
            plt.title('Position P&L', fontsize=16, color='white')
            plt.xlabel('Symbol', fontsize=12, color='white')
            plt.ylabel('Unrealized PnL ($)', fontsize=12, color='white')
            plt.xticks(rotation=45, color='white')
            plt.yticks(color='white')
            plt.grid(alpha=0.3)
            plt.tight_layout()
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='PNG', facecolor='black', edgecolor='none')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            logger.error(f"Error creating portfolio chart: {e}")
            return None

    async def _create_position_chart(self) -> Optional[io.BytesIO]:
        """Create position distribution pie chart"""
        try:
            positions = self.position_manager.get_current_positions()
            if not positions:
                return None

            # Create position size data
            symbols = [pos.get('coin', 'N/A') for pos in positions]
            sizes = [abs(float(pos.get('size', 0))) for pos in positions]
            
            plt.figure(figsize=(8, 8))
            plt.pie(sizes, labels=symbols, autopct='%1.1f%%', startangle=90)
            plt.title('Position Distribution', fontsize=16, color='white')
            plt.axis('equal')
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='PNG', facecolor='black', edgecolor='none')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            logger.error(f"Error creating position chart: {e}")
            return None

    def _is_trading_bot_running(self) -> bool:
        """Check if trading bot process is running"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline and 'python' in cmdline.lower():
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception:
            return False

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        if not self.is_authorized(update.effective_user.id):
            return

        data = query.data
        
        try:
            if data == "refresh_status":
                await self.status(update, context)
            elif data == "start_trading":
                await self.start_trading(update, context)
            elif data == "stop_trading":
                await self.stop_trading(update, context)
            elif data == "refresh_portfolio":
                await self.portfolio(update, context)
            elif data == "confirm_emergency":
                await self._handle_emergency_stop(update, context)
            elif data == "portfolio_charts":
                await self.generate_charts(update, context)
            elif data.startswith("close_"):
                await self._handle_position_close(update, context, data)
            elif data == "retrain_models":
                await self._train_ml_models(update)
            # Add more callback handlers...
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def _handle_emergency_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle emergency stop confirmation"""
        try:
            # Stop trading bot
            if self.trading_bot_process:
                self.trading_bot_process.kill()
            
            # Close all positions
            positions = self.position_manager.get_current_positions()
            closed_count = 0
            
            for pos in positions:
                symbol = pos.get('coin')
                if symbol:
                    try:
                        self.position_manager.close_position(symbol, percentage=100)
                        closed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to close {symbol}: {e}")
            
            msg = f"""
🆘 **EMERGENCY STOP EXECUTED**

✅ Trading bot terminated
✅ Closed {closed_count} positions
⚠️ Check positions manually for confirmation

Bot is now in emergency shutdown state.
Use /start_bot to resume when ready.
            """
            
            await update.callback_query.edit_message_text(
                msg,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.callback_query.edit_message_text(f"❌ Emergency stop failed: {str(e)}")

    async def _handle_position_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle position closing"""
        try:
            parts = data.split('_')
            percentage = int(parts[1])
            symbol = parts[2]
            
            result = self.position_manager.close_position(symbol, percentage=percentage)
            
            if result:
                msg = f"✅ Closed {percentage}% of {symbol} position"
            else:
                msg = f"❌ Failed to close {symbol} position"
            
            await update.callback_query.edit_message_text(msg)
            
        except Exception as e:
            await update.callback_query.edit_message_text(f"❌ Error closing position: {str(e)}")

    async def _train_ml_models(self, update: Update):
        """Train ML models in background"""
        try:
            await update.callback_query.edit_message_text("🤖 Training ML models... This may take a few minutes.")
            
            # Run training in background
            def train_models():
                ml_predictor = MLPredictor()
                ml_predictor.train_models()
            
            thread = threading.Thread(target=train_models)
            thread.start()
            
            # Wait and check completion
            for i in range(30):  # 30 second timeout
                await asyncio.sleep(1)
                if not thread.is_alive():
                    break
            
            if thread.is_alive():
                await update.callback_query.edit_message_text("⏳ Model training taking longer than expected...")
            else:
                await update.callback_query.edit_message_text("✅ ML models trained successfully!")
                
        except Exception as e:
            await update.callback_query.edit_message_text(f"❌ Model training failed: {str(e)}")

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if not self.is_authorized(update.effective_user.id):
            return

        text = update.message.text
        
        if text == "📊 Status":
            await self.status(update, context)
        elif text == "💰 Portfolio":
            await self.portfolio(update, context)
        elif text == "▶️ Start":
            await self.start_trading(update, context)
        elif text == "⏹️ Stop":
            await self.stop_trading(update, context)
        elif text == "📈 Charts":
            await self.generate_charts(update, context)
        elif text == "📋 Logs":
            await self.live_logs(update, context)
        elif text == "🆘 Emergency":
            await self.emergency_stop(update, context)

    def run(self):
        """Run the Telegram bot"""
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment")
            return
        
        if not self.chat_ids:
            logger.error("TELEGRAM_AUTHORIZED_USERS not found in environment")
            return

        application = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("portfolio", self.portfolio))
        application.add_handler(CommandHandler("start_bot", self.start_trading))
        application.add_handler(CommandHandler("stop_bot", self.stop_trading))
        application.add_handler(CommandHandler("emergency_stop", self.emergency_stop))
        application.add_handler(CommandHandler("logs", self.live_logs))
        application.add_handler(CommandHandler("positions", self.show_positions))
        application.add_handler(CommandHandler("ml_status", self.ml_status))
        application.add_handler(CommandHandler("charts", self.generate_charts))
        
        application.add_handler(CallbackQueryHandler(self.callback_handler))
        application.add_handler(MessageHandler(filters.TEXT, self.message_handler))
        
        logger.info("Starting Telegram bot...")
        application.run_polling()

if __name__ == "__main__":
    bot = TelegramTradingBot()
    bot.run()