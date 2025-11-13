#!/usr/bin/env python3
"""
Configuration helper for Hyperliquid bot
"""
import os
from dotenv import load_dotenv, set_key

def get_hyperliquid_config():
    """Get Hyperliquid configuration from environment"""
    load_dotenv()
    
    return {
        "private_key": os.getenv("PRIVATE_KEY"),
        "api_url": os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz"),
        "main_account": os.getenv("MAIN_ACCOUNT_ADDRESS"),
        "wallet_address": os.getenv("WALLET_ADDRESS")
    }


def main():
    load_dotenv()
    
    print("🔧 Hyperliquid Bot Configuration Helper")
    print("=" * 50)
    
    current_api_wallet = os.getenv('WALLET_ADDRESS', 'Not set')
    current_main_account = os.getenv('MAIN_ACCOUNT_ADDRESS', 'Not set')
    
    print(f"Current API wallet: {current_api_wallet}")
    print(f"Current main account: {current_main_account}")
    print()
    
    print("📝 Please provide your main account address (the one with $39.5 balance):")
    print("💡 This should be the address where your funds are located")
    print("💡 The API wallet will trade on behalf of this account")
    print()
    
    main_account = input("Enter your main account address (0x...): ").strip()
    
    if main_account and main_account.startswith('0x') and len(main_account) == 42:
        # Update the .env file
        set_key('.env', 'MAIN_ACCOUNT_ADDRESS', main_account)
        print(f"✅ Updated MAIN_ACCOUNT_ADDRESS to: {main_account}")
        print()
        print("🚀 Configuration updated! Now run:")
        print("   python check_account.py  # To verify your account")
        print("   python main.py          # To start trading")
    else:
        print("❌ Invalid address format. Please use format: 0x...")

if __name__ == "__main__":
    main()