#!/usr/bin/env python3
"""
Get all available trading symbols from Hyperliquid
"""
import os
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

def main():
    load_dotenv()
    
    print("🔍 Fetching all available Hyperliquid trading symbols...")
    print("=" * 60)
    
    try:
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Get all available perp symbols
        meta = info.meta()
        universe = meta.get('universe', [])
        
        # Get market data to filter active symbols
        meta_and_ctx = info.meta_and_asset_ctxs()
        asset_contexts = meta_and_ctx[1] if len(meta_and_ctx) > 1 else []
        
        print(f"📊 Found {len(universe)} total symbols:")
        print("=" * 60)
        
        active_symbols = []
        for i, asset_info in enumerate(universe):
            symbol = asset_info.get('name', f'Unknown_{i}')
            sz_decimals = asset_info.get('szDecimals', 0)
            max_leverage = asset_info.get('maxLeverage', 1)
            only_isolated = asset_info.get('onlyIsolated', False)
            
            # Get market context if available
            mark_px = "N/A"
            volume = "N/A"
            if i < len(asset_contexts):
                ctx = asset_contexts[i]
                mark_px = ctx.get('markPx', 'N/A')
                volume = ctx.get('dayNtlVlm', 'N/A')
            
            # Filter for active trading symbols
            if mark_px and mark_px != "N/A" and mark_px != 0:
                active_symbols.append(symbol)
                margin_type = "Isolated Only" if only_isolated else "Cross/Isolated"
                print(f"  ✅ {symbol:<8} | Price: ${mark_px:<12} | Vol: {volume:<12} | Max Lev: {max_leverage:<3}x | {margin_type}")
            else:
                print(f"  ❌ {symbol:<8} | Inactive or no price data")
        
        print("=" * 60)
        print(f"🎯 Active trading symbols: {len(active_symbols)}")
        print(f"📝 Symbols list: {', '.join(active_symbols)}")
        
        # Create formatted symbol list for config
        formatted_symbols = [f"'{symbol}-USD'" for symbol in active_symbols]
        symbols_config = f"TRADING_SYMBOLS = [{', '.join(formatted_symbols)}]"
        
        print("\n💡 Configuration for main.py:")
        print(f"   {symbols_config}")
        
        return active_symbols
        
    except Exception as e:
        print(f"❌ Error fetching symbols: {e}")
        return []

if __name__ == "__main__":
    main()