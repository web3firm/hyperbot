#!/usr/bin/env python3
"""
Quick Start Guide for Hyperbot Telegram Controller
Complete setup verification and launch script
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv()

def print_banner():
    print("🤖 " + "="*60)
    print("🚀 HYPERBOT TELEGRAM CONTROLLER")
    print("📱 Complete Remote Trading Control")
    print("🤖 " + "="*60)
    print()

def check_config():
    """Check if Telegram is configured"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    users = os.getenv('TELEGRAM_AUTHORIZED_USERS')
    
    return bool(bot_token) and bool(users)

def main():
    print_banner()
    
    if not check_config():
        print("❌ Telegram bot not configured.")
        print("🔧 Run: python setup_telegram.py")
        return
    
    print("✅ Telegram bot configured!")
    print("🎯 Available commands:")
    print()
    print("1. 🧪 Test Connection:    python test_telegram.py")
    print("2. 🚀 Start Bot:         python telegram_launcher.py")
    print("3. ⚙️ Reconfigure:       python setup_telegram.py")
    print()
    
    choice = input("Choose action (1-3) or press Enter to start bot: ").strip()
    
    if choice == '1':
        print("\n🧪 Testing connection...")
        os.system("python test_telegram.py")
    elif choice == '2' or choice == '':
        print("\n🚀 Starting Telegram bot controller...")
        os.system("python telegram_launcher.py")
    elif choice == '3':
        print("\n⚙️ Opening configuration...")
        os.system("python setup_telegram.py")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()