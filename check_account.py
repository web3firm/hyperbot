#!/usr/bin/env python3
"""
Quick account status check for Hyperliquid bot
"""
import os
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

def main():
    load_dotenv()
    
    try:
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Get main account address (the one with funds)
        main_account = os.getenv('MAIN_ACCOUNT_ADDRESS')
        api_wallet = os.getenv('WALLET_ADDRESS')
        
        if not main_account:
            main_account = api_wallet  # Fallback
            
        if not main_account:
            print("❌ MAIN_ACCOUNT_ADDRESS or WALLET_ADDRESS not found in .env file")
            return
            
        print(f"🔍 Checking main account: {main_account}")
        if main_account != api_wallet:
            print(f"🤖 API wallet: {api_wallet}")
        print("=" * 50)
        
        # Get user state
        user_state = info.user_state(main_account)
        
        if not user_state:
            print("❌ Could not retrieve account data")
            return
            
        margin_summary = user_state.get('marginSummary', {})
        
        print(f"💰 Account Value: ${margin_summary.get('accountValue', '0')}")
        print(f"💵 Available Balance: ${user_state.get('withdrawable', '0')}")
        print(f"📊 Cross Margin Used: ${margin_summary.get('totalMarginUsed', '0')}")
        print(f"📈 Total Position Value: ${margin_summary.get('totalNtlPos', '0')}")
        
        # Check positions
        positions = user_state.get('assetPositions', [])
        print(f"\n🔢 Active Positions: {len(positions)}")
        
        if positions:
            print("\n📋 Position Details:")
            for pos in positions:
                position = pos.get('position', {})
                coin = position.get('coin', 'Unknown')
                size = position.get('szi', '0')
                pnl = position.get('unrealizedPnl', '0')
                print(f"  • {coin}: Size {size}, PnL ${pnl}")
        else:
            print("  No active positions")
            
        print("\n✅ Account check complete!")
        print("\n🚀 Your bot is ready for live trading!")
        print("💡 Tip: The bot will trade automatically when strong signals are detected")
        
    except Exception as e:
        print(f"❌ Error checking account: {e}")
        print("🔧 Make sure your PRIVATE_KEY and WALLET_ADDRESS are correct in .env")

if __name__ == "__main__":
    main()