#!/usr/bin/env python3
"""
Launcher script for Telegram Trading Bot Controller
Handles both the Telegram bot and notification system
"""

import asyncio
import signal
import sys
import threading
from telegram_bot import TelegramTradingBot
from telegram_notifications import notifications
from loguru import logger

class TelegramBotLauncher:
    def __init__(self):
        self.telegram_bot = TelegramTradingBot()
        self.running = True
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal")
        self.running = False
        sys.exit(0)
    
    def run_notification_system(self):
        """Run notification system in background"""
        try:
            # Send startup notification
            asyncio.run(notifications.send_system_alert(
                "STARTUP", 
                "Telegram bot controller started and ready for commands!"
            ))
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    def run(self):
        """Run the complete Telegram bot system"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("Starting Telegram Bot Controller...")
        
        # Start notification system
        notification_thread = threading.Thread(target=self.run_notification_system)
        notification_thread.start()
        
        # Start main Telegram bot
        try:
            self.telegram_bot.run()
        except KeyboardInterrupt:
            logger.info("Telegram bot stopped by user")
        except Exception as e:
            logger.error(f"Telegram bot error: {e}")
        finally:
            logger.info("Telegram bot controller shutdown")

if __name__ == "__main__":
    launcher = TelegramBotLauncher()
    launcher.run()