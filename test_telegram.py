#!/usr/bin/env python3
"""
Simple Telegram Bot Test
Basic test to ensure Telegram bot is working
"""

import os
import asyncio
from telegram import Bot
from telegram.constants import ParseMode

async def test_bot():
    """Test basic bot functionality"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    user_id = os.getenv('TELEGRAM_AUTHORIZED_USERS')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return False
        
    if not user_id:
        print("❌ TELEGRAM_AUTHORIZED_USERS not found in .env")
        return False
    
    try:
        bot = Bot(bot_token)
        
        # Test bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot connected: @{bot_info.username}")
        
        # Send test message
        message = """
🤖 **HYPERBOT TELEGRAM CONTROLLER**

✅ Bot successfully connected!
🔗 All systems operational
📊 Ready to monitor your trading bot

Send /start to begin using the controller.
        """
        
        user_ids = [uid.strip() for uid in user_id.split(',') if uid.strip()]
        
        for uid in user_ids:
            try:
                await bot.send_message(
                    chat_id=uid,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
                print(f"✅ Test message sent to user {uid}")
            except Exception as e:
                print(f"❌ Failed to send to user {uid}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Bot test failed: {e}")
        return False

if __name__ == "__main__":
    print("🤖 Testing Telegram Bot Connection...")
    print("=" * 50)
    
    success = asyncio.run(test_bot())
    
    if success:
        print("\n✅ Test completed successfully!")
        print("🚀 You can now start the full bot with: python telegram_launcher.py")
    else:
        print("\n❌ Test failed. Please check your configuration.")
        print("🔧 Run: python setup_telegram.py to configure the bot")