#!/usr/bin/env python3
"""
Enhanced Multi-Symbol Trading Bot Monitor
Tracks performance across all trading symbols with real-time analytics
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from hyperliquid.utils import constants
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from eth_account import Account
from loguru import logger
import json

class MultiSymbolMonitor:
    """Enhanced monitoring for multi-symbol trading bot"""
    
    def __init__(self):
        """Initialize the monitor"""
        self.setup_logging()
        self.setup_hyperliquid()
        self.symbols = self.get_trading_symbols()
        self.start_time = datetime.utcnow()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logger.add(
            "logs/multi_symbol_monitor_{time}.log",
            rotation="1 day",
            retention="30 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        
    def setup_hyperliquid(self):
        """Setup Hyperliquid connection"""
        try:
            private_key = os.getenv('PRIVATE_KEY')
            main_account = os.getenv('MAIN_ACCOUNT_ADDRESS', '').strip("'"'"').strip()
            
            if not private_key or not main_account:
                raise ValueError("Missing PRIVATE_KEY or MAIN_ACCOUNT_ADDRESS in environment")
            
            # Create account for signing
            account = Account.from_key(private_key)
            
            # Initialize exchange and info
            self.exchange = Exchange(account, constants.MAINNET_API_URL, account_address=main_account)
            self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
            
            logger.info("✅ Hyperliquid connection established")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Hyperliquid: {e}")
            sys.exit(1)
            
    def get_trading_symbols(self) -> List[str]:
        """Get the list of trading symbols from main.py config"""
        return [
            # Major tokens (highest volume)
            'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'DOGE-USD',
            # High-volume alts
            'HYPE-USD', 'FARTCOIN-USD', 'POPCAT-USD', 'PUMP-USD', 'VIRTUAL-USD',
            'TRUMP-USD', 'ASTER-USD', 'ZEC-USD', 'PAXG-USD', 'XPL-USD',
            # Medium-high volume
            'UNI-USD', 'LTC-USD', 'LINK-USD', 'ADA-USD', 'AAVE-USD',
            'NEAR-USD', 'TON-USD', 'RENDER-USD', 'TAO-USD', 'ENA-USD',
            'STRK-USD', 'WIF-USD', 'ONDO-USD', 'ARB-USD', 'SUI-USD',
            # Volatile meme tokens
            'kPEPE-USD', 'kBONK-USD', 'kFLOKI-USD', 'BRETT-USD', 'MEW-USD',
            'PNUT-USD', 'GOAT-USD', 'MOODENG-USD', 'PENGU-USD', 'AIXBT-USD',
            # DeFi tokens
            'JUP-USD', 'JTO-USD', 'EIGEN-USD', 'ETHFI-USD', 'PENDLE-USD',
            'CRV-USD', 'LDO-USD', 'SUSHI-USD', 'COMP-USD', 'MKR-USD',
            # Layer 1/2 tokens
            'AVAX-USD', 'DOT-USD', 'ATOM-USD', 'TIA-USD', 'MNT-USD',
            'POL-USD', 'FIL-USD', 'AR-USD', 'HBAR-USD', 'ICP-USD',
            # Gaming/AI tokens
            'IMX-USD', 'SAND-USD', 'GALA-USD', 'SUPER-USD', 'FET-USD',
            'ZRO-USD', 'W-USD', 'IO-USD', 'ZK-USD', 'TURBO-USD'
        ]
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get comprehensive account information"""
        try:
            user_state = self.info.user_state(
                os.getenv('MAIN_ACCOUNT_ADDRESS', '').strip("'"'"').strip()
            )
            
            if not user_state:
                return {"error": "Failed to get account state"}
                
            # Extract key information
            account_info = {
                "balance": float(user_state.get("marginSummary", {}).get("accountValue", 0)),
                "positions": len(user_state.get("assetPositions", [])),
                "pnl": float(user_state.get("marginSummary", {}).get("totalRawUsd", 0)),
                "margin_used": float(user_state.get("marginSummary", {}).get("totalMarginUsed", 0)),
                "withdrawable": float(user_state.get("withdrawable", 0))
            }
            
            return account_info
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"error": str(e)}
    
    async def get_symbol_performance(self) -> List[Dict[str, Any]]:
        """Get performance data for all symbols"""
        symbol_data = []
        
        for symbol in self.symbols[:20]:  # Monitor top 20 for performance
            try:
                # Get market data
                meta = self.info.meta()
                universe = meta.get("universe", [])
                
                symbol_info = None
                for token in universe:
                    if f"{token['name']}-USD" == symbol:
                        symbol_info = token
                        break
                
                if symbol_info:
                    symbol_data.append({
                        "symbol": symbol,
                        "price": float(symbol_info.get("markPx", 0)),
                        "change_24h": float(symbol_info.get("dayNtlVlm", 0)) / 1000000,  # Convert to millions
                        "volume_24h": float(symbol_info.get("dayNtlVlm", 0)),
                        "max_leverage": int(symbol_info.get("maxLeverage", 1)),
                        "margin_only": symbol_info.get("onlyIsolated", False)
                    })
                else:
                    symbol_data.append({
                        "symbol": symbol,
                        "price": 0,
                        "change_24h": 0,
                        "volume_24h": 0,
                        "max_leverage": 1,
                        "margin_only": True,
                        "status": "Not found"
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to get data for {symbol}: {e}")
                symbol_data.append({
                    "symbol": symbol,
                    "status": f"Error: {e}",
                    "price": 0,
                    "volume_24h": 0
                })
                
        return symbol_data
    
    def display_dashboard(self, account_info: Dict, symbol_data: List[Dict], positions: List):
        """Display the monitoring dashboard"""
        print("\n" + "="*80)
        print("🚀 HYPERLIQUID MULTI-SYMBOL TRADING BOT MONITOR")
        print("="*80)
        
        # Account Overview
        print(f"\n💰 ACCOUNT OVERVIEW")
        print(f"│ Balance:      ${account_info.get('balance', 0):.2f}")
        print(f"│ PnL:          ${account_info.get('pnl', 0):.2f}")
        print(f"│ Margin Used:  ${account_info.get('margin_used', 0):.2f}")
        print(f"│ Withdrawable: ${account_info.get('withdrawable', 0):.2f}")
        print(f"│ Positions:    {account_info.get('positions', 0)} active")
        
        # Positions
        if positions:
            print(f"\n📊 ACTIVE POSITIONS ({len(positions)})")
            for pos in positions[:5]:  # Show top 5
                pnl = float(pos.get("unrealizedPnl", 0))
                size = float(pos.get("szi", 0))
                symbol = pos.get("coin", "Unknown")
                print(f"│ {symbol:12} Size: {size:8.4f} PnL: ${pnl:8.2f}")
        
        # Top Symbols by Volume
        if symbol_data:
            print(f"\n📈 TOP SYMBOLS BY VOLUME")
            sorted_symbols = sorted(symbol_data, key=lambda x: x.get('volume_24h', 0), reverse=True)
            for i, symbol in enumerate(sorted_symbols[:10]):
                volume_mil = symbol.get('volume_24h', 0) / 1000000
                price = symbol.get('price', 0)
                leverage = symbol.get('max_leverage', 1)
                print(f"│ {i+1:2}. {symbol['symbol']:12} ${price:8.4f} Vol: ${volume_mil:6.1f}M Lev: {leverage:2}x")
        
        # Runtime Stats
        uptime = datetime.utcnow() - self.start_time
        print(f"\n⏱️  RUNTIME STATS")
        print(f"│ Uptime:       {str(uptime).split('.')[0]}")
        print(f"│ Symbols:      {len(self.symbols)} configured")
        print(f"│ Last Update:  {datetime.utcnow().strftime('%H:%M:%S UTC')}")
        print("="*80)
    
    async def run_monitor(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Multi-Symbol Trading Bot Monitor")
        
        while True:
            try:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Get account info
                account_info = await self.get_account_info()
                
                # Get positions
                try:
                    user_state = self.info.user_state(
                        os.getenv('MAIN_ACCOUNT_ADDRESS', '').strip("'"'"').strip()
                    )
                    positions = user_state.get("assetPositions", []) if user_state else []
                except Exception as e:
                    logger.error(f"Failed to get positions: {e}")
                    positions = []
                
                # Get symbol data
                symbol_data = await self.get_symbol_performance()
                
                # Display dashboard
                self.display_dashboard(account_info, symbol_data, positions)
                
                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except KeyboardInterrupt:
                print("\n👋 Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)

async def main():
    """Main function"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    monitor = MultiSymbolMonitor()
    await monitor.run_monitor()

if __name__ == "__main__":
    asyncio.run(main())