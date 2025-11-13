#!/usr/bin/env python3
"""
Telegram Bot Configuration Helper
Interactive setup for Telegram bot credentials and settings
"""

import os
import sys
from pathlib import Path

def print_header():
    print("🤖 " + "="*60)
    print("🚀 HYPERBOT TELEGRAM CONTROLLER SETUP")
    print("🤖 " + "="*60)
    print()

def print_step(step_num, title):
    print(f"\n📋 Step {step_num}: {title}")
    print("-" * 40)

def get_env_path():
    """Get the path to .env file"""
    return Path("/workspaces/hyperbot/.env")

def read_env_file():
    """Read current .env file content"""
    env_path = get_env_path()
    if env_path.exists():
        with open(env_path, 'r') as f:
            return f.read()
    return ""

def update_env_var(content, var_name, var_value):
    """Update or add environment variable"""
    lines = content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith(f"{var_name}="):
            lines[i] = f"{var_name}={var_value}"
            updated = True
            break
    
    if not updated:
        lines.append(f"{var_name}={var_value}")
    
    return '\n'.join(lines)

def save_env_file(content):
    """Save content to .env file"""
    env_path = get_env_path()
    with open(env_path, 'w') as f:
        f.write(content)
    print(f"✅ Configuration saved to {env_path}")

def setup_telegram_bot():
    """Interactive Telegram bot setup"""
    print_header()
    
    print("📱 This wizard will help you set up the Telegram bot controller.")
    print("🎯 You'll need to create a Telegram bot and get your user ID.")
    print()
    
    # Step 1: Create bot
    print_step(1, "Create Telegram Bot")
    print("1. Open Telegram and message @BotFather")
    print("2. Send: /newbot")
    print("3. Choose name: 'Hyperbot Trading Controller'")
    print("4. Choose username: 'your_hyperbot_controller_bot'")
    print("5. Copy the bot token (format: 123456789:ABCdef...)")
    print()
    
    while True:
        bot_token = input("📝 Enter your bot token: ").strip()
        if bot_token and ':' in bot_token and len(bot_token) > 20:
            break
        print("❌ Invalid token format. Please try again.")
    
    # Step 2: Get user ID
    print_step(2, "Get Your User ID")
    print("1. Message @userinfobot on Telegram")
    print("2. Copy your user ID (format: 123456789)")
    print()
    
    while True:
        user_id = input("📝 Enter your user ID: ").strip()
        if user_id.isdigit() and len(user_id) >= 6:
            break
        print("❌ Invalid user ID format. Please try again.")
    
    # Step 3: Additional users
    print_step(3, "Additional Users (Optional)")
    print("Add more authorized users (comma-separated IDs):")
    additional_users = input("📝 Additional user IDs (or press Enter to skip): ").strip()
    
    if additional_users:
        all_users = f"{user_id},{additional_users}"
    else:
        all_users = user_id
    
    # Step 4: Notification preferences
    print_step(4, "Notification Preferences")
    
    notify_trades = input("📊 Enable trade notifications? (Y/n): ").strip().lower()
    notify_trades = "true" if notify_trades != 'n' else "false"
    
    notify_risks = input("⚠️ Enable risk alerts? (Y/n): ").strip().lower()
    notify_risks = "true" if notify_risks != 'n' else "false"
    
    notify_system = input("🔧 Enable system alerts? (Y/n): ").strip().lower()
    notify_system = "true" if notify_system != 'n' else "false"
    
    daily_summary = input("📅 Enable daily summaries? (Y/n): ").strip().lower()
    daily_summary = "true" if daily_summary != 'n' else "false"
    
    # Step 5: Update .env file
    print_step(5, "Saving Configuration")
    
    try:
        content = read_env_file()
        
        # Update Telegram settings
        content = update_env_var(content, "TELEGRAM_BOT_TOKEN", bot_token)
        content = update_env_var(content, "TELEGRAM_AUTHORIZED_USERS", all_users)
        content = update_env_var(content, "TELEGRAM_NOTIFY_TRADES", notify_trades)
        content = update_env_var(content, "TELEGRAM_NOTIFY_RISKS", notify_risks)
        content = update_env_var(content, "TELEGRAM_NOTIFY_SYSTEM", notify_system)
        content = update_env_var(content, "TELEGRAM_DAILY_SUMMARY", daily_summary)
        
        save_env_file(content)
        
        print("\n✅ Configuration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error saving configuration: {e}")
        return False
    
    # Step 6: Test setup
    print_step(6, "Test Your Setup")
    print("🎯 To test your Telegram bot:")
    print("1. Install dependencies: pip install python-telegram-bot psutil")
    print("2. Start bot: python telegram_launcher.py")
    print("3. Message your bot on Telegram")
    print("4. Send /start to begin")
    print()
    
    # Summary
    print("📋 " + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("📋 " + "="*60)
    print(f"🤖 Bot Token: {bot_token[:20]}...")
    print(f"👥 Authorized Users: {all_users}")
    print(f"📊 Trade Notifications: {notify_trades}")
    print(f"⚠️ Risk Alerts: {notify_risks}")
    print(f"🔧 System Alerts: {notify_system}")
    print(f"📅 Daily Summaries: {daily_summary}")
    print()
    print("🚀 Next steps:")
    print("   1. Run: python telegram_launcher.py")
    print("   2. Message your bot on Telegram")
    print("   3. Send /start to activate")
    print("   4. Use /status to check trading bot status")
    print()
    
    return True

def check_current_config():
    """Check current Telegram configuration"""
    print_header()
    print("🔍 Checking current Telegram bot configuration...")
    print()
    
    env_path = get_env_path()
    if not env_path.exists():
        print("❌ No .env file found. Run setup first.")
        return False
    
    # Check for Telegram variables
    content = read_env_file()
    lines = content.split('\n')
    
    telegram_vars = {}
    for line in lines:
        if line.startswith('TELEGRAM_'):
            if '=' in line:
                key, value = line.split('=', 1)
                telegram_vars[key] = value
    
    if not telegram_vars:
        print("❌ No Telegram configuration found in .env file.")
        print("🎯 Run setup to configure Telegram bot.")
        return False
    
    print("📋 Current Telegram Configuration:")
    print("-" * 40)
    
    for key, value in telegram_vars.items():
        if 'TOKEN' in key and value:
            # Mask token for security
            display_value = value[:20] + "..." if len(value) > 20 else value
        else:
            display_value = value or "(not set)"
        
        print(f"✅ {key}: {display_value}")
    
    print()
    
    # Check if properly configured
    required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_AUTHORIZED_USERS']
    missing_vars = []
    
    for var in required_vars:
        if var not in telegram_vars or not telegram_vars[var]:
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required configuration:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n🎯 Run setup to complete configuration.")
        return False
    else:
        print("✅ Telegram bot is properly configured!")
        print("🚀 You can start the bot with: python telegram_launcher.py")
        return True

def install_dependencies():
    """Install required dependencies"""
    print_header()
    print("📦 Installing Telegram bot dependencies...")
    print()
    
    dependencies = [
        "python-telegram-bot>=20.0",
        "psutil>=5.9.0"
    ]
    
    for dep in dependencies:
        print(f"📦 Installing {dep}...")
        result = os.system(f"pip install {dep}")
        if result == 0:
            print(f"✅ {dep} installed successfully")
        else:
            print(f"❌ Failed to install {dep}")
            return False
    
    print("\n✅ All dependencies installed successfully!")
    return True

def main():
    """Main menu"""
    while True:
        print_header()
        print("🎯 Choose an option:")
        print("1. 🛠️  Setup Telegram Bot (First time setup)")
        print("2. 🔍 Check Current Configuration")
        print("3. 📦 Install Dependencies")
        print("4. 🚀 Start Telegram Bot")
        print("5. 📖 View Setup Guide")
        print("6. ❌ Exit")
        print()
        
        choice = input("📝 Enter your choice (1-6): ").strip()
        
        if choice == '1':
            setup_telegram_bot()
            input("\nPress Enter to continue...")
        
        elif choice == '2':
            check_current_config()
            input("\nPress Enter to continue...")
        
        elif choice == '3':
            install_dependencies()
            input("\nPress Enter to continue...")
        
        elif choice == '4':
            print("\n🚀 Starting Telegram bot...")
            os.system("python telegram_launcher.py")
        
        elif choice == '5':
            print("\n📖 Opening setup guide...")
            if os.path.exists("TELEGRAM_SETUP.md"):
                os.system("cat TELEGRAM_SETUP.md")
            else:
                print("❌ Setup guide not found. Check TELEGRAM_SETUP.md file.")
            input("\nPress Enter to continue...")
        
        elif choice == '6':
            print("\n👋 Goodbye!")
            sys.exit(0)
        
        else:
            print("❌ Invalid choice. Please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()