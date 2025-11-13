#!/usr/bin/env python3
"""
Advanced Telegram Notification System for Trading Bot
Sends real-time alerts for trades, risk events, and performance updates
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Bot
from telegram.constants import ParseMode
import os
from loguru import logger

class TradingNotifications:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_ids = self._get_authorized_users()
        self.bot = Bot(self.bot_token) if self.bot_token else None
        
    def _get_authorized_users(self) -> List[str]:
        """Get authorized Telegram user IDs from environment"""
        users = os.getenv('TELEGRAM_AUTHORIZED_USERS', '')
        return [user.strip() for user in users.split(',') if user.strip()]

    async def send_trade_alert(self, 
                              action: str, 
                              symbol: str, 
                              side: str, 
                              size: float, 
                              price: float, 
                              reason: str = ""):
        """Send trade execution alert"""
        if not self.bot:
            return

        action_emoji = {
            'OPEN': '🟢',
            'CLOSE': '🔴',
            'PARTIAL_CLOSE': '🟡'
        }

        side_emoji = '📈' if side.upper() in ['LONG', 'B'] else '📉'
        
        message = f"""
{action_emoji.get(action, '⚪')} **TRADE {action}**

{side_emoji} {symbol} {side.upper()}
💰 Size: {size:,.4f}
💵 Price: ${price:,.4f}
💸 Value: ${size * price:,.2f}

{f"📝 Reason: {reason}" if reason else ""}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        await self._broadcast_message(message)

    async def send_risk_alert(self, 
                             alert_type: str, 
                             message: str, 
                             severity: str = "WARNING"):
        """Send risk management alert"""
        if not self.bot:
            return

        severity_emoji = {
            'INFO': '🔵',
            'WARNING': '🟡',
            'DANGER': '🔴',
            'CRITICAL': '💥'
        }

        alert_msg = f"""
{severity_emoji.get(severity, '⚪')} **RISK {severity}**

⚠️ {alert_type}

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        await self._broadcast_message(alert_msg)

    async def send_pnl_update(self, 
                             total_pnl: float, 
                             daily_pnl: float, 
                             portfolio_value: float,
                             positions: List[Dict]):
        """Send P&L performance update"""
        if not self.bot:
            return

        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        daily_emoji = "📈" if daily_pnl >= 0 else "📉"
        
        message = f"""
📊 **PORTFOLIO UPDATE**

{pnl_emoji} Total PnL: ${total_pnl:,.2f}
{daily_emoji} Daily PnL: ${daily_pnl:,.2f}
💰 Portfolio Value: ${portfolio_value:,.2f}

📋 Active Positions: {len(positions)}
        """
        
        if positions:
            message += "\n🎯 **Top Performers:**\n"
            # Sort by PnL and show top 3
            sorted_pos = sorted(positions, 
                              key=lambda x: float(x.get('unrealizedPnl', 0)), 
                              reverse=True)[:3]
            
            for pos in sorted_pos:
                symbol = pos.get('coin', 'N/A')
                pnl = float(pos.get('unrealizedPnl', 0))
                emoji = "🟢" if pnl >= 0 else "🔴"
                message += f"{emoji} {symbol}: ${pnl:,.2f}\n"

        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        await self._broadcast_message(message)

    async def send_ml_prediction(self, 
                               symbol: str, 
                               prediction: str, 
                               confidence: float, 
                               features: Dict):
        """Send ML prediction alert"""
        if not self.bot:
            return

        pred_emoji = {
            'bullish': '🟢📈',
            'bearish': '🔴📉',
            'neutral': '🟡➡️'
        }

        confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        
        message = f"""
🤖 **ML PREDICTION**

{pred_emoji.get(prediction.lower(), '⚪')} {symbol}: {prediction.upper()}

🎯 Confidence: {confidence:.2f}
[{confidence_bar}] {confidence*100:.1f}%

📊 Key Signals:
• RSI: {features.get('rsi', 'N/A'):.2f}
• MACD: {features.get('macd_signal', 'N/A'):.2f}
• Volume: {features.get('volume_ratio', 'N/A'):.2f}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        await self._broadcast_message(message)

    async def send_system_alert(self, 
                              alert_type: str, 
                              message: str):
        """Send system/bot status alert"""
        if not self.bot:
            return

        type_emoji = {
            'STARTUP': '🚀',
            'SHUTDOWN': '⏹️',
            'ERROR': '❌',
            'RECONNECT': '🔄',
            'UPDATE': 'ℹ️'
        }

        alert_msg = f"""
{type_emoji.get(alert_type, '⚪')} **SYSTEM {alert_type}**

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        await self._broadcast_message(alert_msg)

    async def send_market_alert(self, 
                              symbol: str, 
                              alert_type: str, 
                              current_price: float, 
                              change_pct: float):
        """Send market movement alert"""
        if not self.bot:
            return

        change_emoji = "🟢" if change_pct >= 0 else "🔴"
        
        alert_emoji = {
            'BREAKOUT': '🚀',
            'BREAKDOWN': '💥',
            'VOLUME_SPIKE': '📊',
            'VOLATILITY': '⚡'
        }

        message = f"""
{alert_emoji.get(alert_type, '⚪')} **MARKET {alert_type}**

📈 {symbol}
💵 Price: ${current_price:,.4f}
{change_emoji} Change: {change_pct:+.2f}%

⏰ {datetime.now().strftime('%H:%M:%S')}
        """
        
        await self._broadcast_message(message)

    async def send_daily_summary(self, 
                               summary_data: Dict):
        """Send end-of-day trading summary"""
        if not self.bot:
            return

        trades = summary_data.get('trades', 0)
        pnl = summary_data.get('pnl', 0)
        win_rate = summary_data.get('win_rate', 0)
        best_trade = summary_data.get('best_trade', {})
        worst_trade = summary_data.get('worst_trade', {})

        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        
        message = f"""
📅 **DAILY TRADING SUMMARY**

📊 Trades Executed: {trades}
{pnl_emoji} P&L: ${pnl:,.2f}
🎯 Win Rate: {win_rate:.1f}%

🏆 Best Trade: {best_trade.get('symbol', 'N/A')} 
   ${best_trade.get('pnl', 0):,.2f}

📉 Worst Trade: {worst_trade.get('symbol', 'N/A')}
   ${worst_trade.get('pnl', 0):,.2f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self._broadcast_message(message)

    async def _broadcast_message(self, message: str):
        """Send message to all authorized users"""
        if not self.bot or not self.chat_ids:
            logger.warning("Telegram bot or chat IDs not configured")
            return

        for chat_id in self.chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Failed to send message to {chat_id}: {e}")

# Global notification instance
notifications = TradingNotifications()

# Convenience functions for easy import
async def notify_trade(action: str, symbol: str, side: str, size: float, price: float, reason: str = ""):
    await notifications.send_trade_alert(action, symbol, side, size, price, reason)

async def notify_risk(alert_type: str, message: str, severity: str = "WARNING"):
    await notifications.send_risk_alert(alert_type, message, severity)

async def notify_pnl(total_pnl: float, daily_pnl: float, portfolio_value: float, positions: List[Dict]):
    await notifications.send_pnl_update(total_pnl, daily_pnl, portfolio_value, positions)

async def notify_prediction(symbol: str, prediction: str, confidence: float, features: Dict):
    await notifications.send_ml_prediction(symbol, prediction, confidence, features)

async def notify_system(alert_type: str, message: str):
    await notifications.send_system_alert(alert_type, message)

async def notify_market(symbol: str, alert_type: str, current_price: float, change_pct: float):
    await notifications.send_market_alert(symbol, alert_type, current_price, change_pct)