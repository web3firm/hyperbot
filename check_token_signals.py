#!/usr/bin/env python3
"""
Token Signal Analyzer - Check which tokens are ready to trade
Analyzes ADX, RSI, volatility, and signal scores for multiple symbols
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from app.hl.hl_client import HyperLiquidClient
from app.strategies.rule_based.swing_trader import SwingTradingStrategy


class TokenAnalyzer:
    """Analyze multiple tokens for trading readiness"""
    
    def __init__(self):
        self.client = HyperLiquidClient(
            account_address=os.getenv('ACCOUNT_ADDRESS'),
            api_key=os.getenv('ACCOUNT_ADDRESS'),
            api_secret=os.getenv('API_SECRET'),
            testnet=os.getenv('TESTNET', 'false').lower() == 'true'
        )
        
    def analyze_token(self, symbol: str) -> Dict[str, Any]:
        """Analyze a single token for trading readiness"""
        try:
            # Fetch candles
            candles = self.client.get_candles(symbol, '1m', 150)
            
            if not candles or len(candles) < 100:
                return {
                    'symbol': symbol,
                    'error': 'Insufficient data',
                    'ready': False
                }
            
            # Extract prices and volumes
            prices = [Decimal(str(c['close'])) for c in candles]
            volumes = [Decimal(str(c['volume'])) for c in candles if c['volume'] > 0]
            
            # Current price (convert to float for formatting)
            current_price = float(prices[-1])
            
            # Calculate indicators using swing strategy methods
            strategy = SwingTradingStrategy(symbol)
            
            # RSI
            rsi = strategy._calculate_rsi(prices, 14)
            rsi = float(rsi) if rsi else None
            
            # EMA
            ema_fast = strategy._calculate_ema(prices, 21)
            ema_slow = strategy._calculate_ema(prices, 50)
            ema_fast = float(ema_fast) if ema_fast else None
            ema_slow = float(ema_slow) if ema_slow else None
            
            # MACD
            macd = strategy._calculate_macd(prices)
            if macd:
                macd = {k: float(v) if v else None for k, v in macd.items()}
            
            # ADX
            adx = strategy._calculate_adx(prices, 14)
            adx = float(adx) if adx else None
            
            # ATR
            atr = strategy._calculate_atr(prices, 14)
            atr = float(atr) if atr else None
            atr_pct = (atr / current_price * 100) if atr and current_price else None
            
            # Volume (convert to float)
            avg_volume = sum(volumes) / len(volumes) if volumes else Decimal('0')
            current_volume = Decimal(str(candles[-1]['volume']))
            volume_ratio = float(current_volume / avg_volume) if avg_volume > 0 else 0.0
            
            # 24h change (convert to float)
            price_24h_ago = float(prices[-min(60, len(prices))]) if len(prices) >= 60 else float(prices[0])
            change_24h = ((current_price - price_24h_ago) / price_24h_ago * 100) if price_24h_ago else 0.0
            
            # Trend direction
            trend = 'UP' if ema_fast and ema_slow and ema_fast > ema_slow else 'DOWN'
            
            # Trading readiness score
            score = 0
            max_score = 8
            reasons = []
            
            # Check ADX (trend strength)
            if adx and adx >= 25:
                score += 2
                reasons.append(f"✅ Strong trend (ADX {adx:.1f})")
            elif adx and adx >= 20:
                score += 1
                reasons.append(f"⚠️ Moderate trend (ADX {adx:.1f})")
            else:
                adx_display = adx if adx else 0
                reasons.append(f"❌ Weak trend (ADX {adx_display:.1f})")
            
            # Check RSI
            if rsi:
                if (30 <= rsi <= 45) or (55 <= rsi <= 70):
                    score += 2
                    reasons.append(f"✅ RSI in entry zone ({rsi:.1f})")
                elif rsi < 30:
                    score += 1
                    reasons.append(f"⚠️ RSI oversold ({rsi:.1f})")
                elif rsi > 70:
                    score += 1
                    reasons.append(f"⚠️ RSI overbought ({rsi:.1f})")
                else:
                    reasons.append(f"❌ RSI neutral ({rsi:.1f})")
            
            # Check ATR (volatility)
            if atr_pct and atr_pct >= 0.2:
                score += 2
                reasons.append(f"✅ Good volatility (ATR {atr_pct:.2f}%)")
            elif atr_pct and atr_pct >= 0.15:
                score += 1
                reasons.append(f"⚠️ Moderate volatility (ATR {atr_pct:.2f}%)")
            else:
                atr_display = atr_pct if atr_pct else 0
                reasons.append(f"❌ Low volatility (ATR {atr_display:.2f}%)")
            
            # Check volume
            if volume_ratio >= 1.5:
                score += 1
                reasons.append(f"✅ High volume ({volume_ratio:.1f}x)")
            elif volume_ratio >= 1.0:
                score += 0.5
                reasons.append(f"⚠️ Average volume ({volume_ratio:.1f}x)")
            else:
                reasons.append(f"❌ Low volume ({volume_ratio:.1f}x)")
            
            # MACD confirmation
            if macd and macd['macd'] > macd['signal']:
                score += 0.5
                reasons.append(f"✅ MACD bullish")
            elif macd:
                reasons.append(f"❌ MACD bearish")
            
            # Determine readiness
            ready = score >= 5  # Need at least 5/8 points
            
            return {
                'symbol': symbol,
                'ready': ready,
                'score': f"{float(score):.1f}/{max_score}",
                'score_pct': f"{(float(score)/max_score)*100:.0f}%",
                'price': current_price,
                'change_24h': f"{change_24h:+.2f}%" if change_24h else 'N/A',
                'trend': trend,
                'adx': adx,
                'rsi': rsi,
                'atr_pct': atr_pct,
                'volume_ratio': volume_ratio,
                'reasons': reasons,
                'error': None
            }
            
        except Exception as e:
            return {
                'symbol': symbol,
                'error': str(e),
                'ready': False
            }
    
    async def analyze_multiple(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple tokens"""
        results = []
        for symbol in symbols:
            print(f"Analyzing {symbol}...", flush=True)
            result = self.analyze_token(symbol)
            results.append(result)
            await asyncio.sleep(0.5)  # Rate limiting
        
        return results


def print_results(results: List[Dict[str, Any]]):
    """Print analysis results in a nice format"""
    
    # Sort by score
    ready_tokens = [r for r in results if r.get('ready')]
    not_ready_tokens = [r for r in results if not r.get('ready') and not r.get('error')]
    error_tokens = [r for r in results if r.get('error')]
    
    print("\n" + "="*80)
    print("🎯 TOKENS READY TO TRADE")
    print("="*80)
    
    if ready_tokens:
        ready_tokens.sort(key=lambda x: float(x['score'].split('/')[0]), reverse=True)
        for r in ready_tokens:
            print(f"\n✅ {r['symbol']}")
            print(f"   Score: {r['score']} ({r['score_pct']})")
            print(f"   Price: ${r['price']:.4f} | 24h: {r['change_24h']} | Trend: {r['trend']}")
            print(f"   ADX: {r['adx']:.1f} | RSI: {r['rsi']:.1f} | ATR: {r['atr_pct']:.2f}% | Vol: {r['volume_ratio']:.1f}x")
            print(f"   Reasons:")
            for reason in r['reasons']:
                print(f"      {reason}")
    else:
        print("\n❌ No tokens meet trading criteria")
    
    print("\n" + "="*80)
    print("⏸️  TOKENS NOT READY")
    print("="*80)
    
    if not_ready_tokens:
        not_ready_tokens.sort(key=lambda x: float(x['score'].split('/')[0]), reverse=True)
        for r in not_ready_tokens:
            adx_str = f"{r['adx']:.1f}" if r['adx'] else 'N/A'
            rsi_str = f"{r['rsi']:.1f}" if r['rsi'] else 'N/A'
            atr_str = f"{r['atr_pct']:.2f}" if r['atr_pct'] else '0.00'
            
            print(f"\n⏸️  {r['symbol']}")
            print(f"   Score: {r['score']} ({r['score_pct']}) - Need 5/8 minimum")
            print(f"   Price: ${r['price']:.4f} | 24h: {r['change_24h']} | Trend: {r['trend']}")
            print(f"   ADX: {adx_str} | RSI: {rsi_str} | ATR: {atr_str}%")
            print(f"   Main issues:")
            failed_reasons = [reason for reason in r['reasons'] if '❌' in reason]
            for reason in failed_reasons[:3]:  # Show top 3 issues
                print(f"      {reason}")
    
    if error_tokens:
        print("\n" + "="*80)
        print("❌ ERRORS")
        print("="*80)
        for r in error_tokens:
            print(f"   {r['symbol']}: {r['error']}")
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"   ✅ Ready to trade: {len(ready_tokens)}")
    print(f"   ⏸️  Not ready: {len(not_ready_tokens)}")
    print(f"   ❌ Errors: {len(error_tokens)}")
    print(f"   📈 Total analyzed: {len(results)}")
    print("="*80)
    print()
    
    # Recommendation
    if ready_tokens:
        best = ready_tokens[0]
        print(f"💡 RECOMMENDATION: Trade {best['symbol']}")
        print(f"   Best score: {best['score']} ({best['score_pct']})")
        print(f"   To use: Update .env with SYMBOL={best['symbol']}")
    else:
        print("💡 RECOMMENDATION: Wait or lower thresholds")
        print("   No tokens meet current trading criteria")
        if not_ready_tokens:
            closest = not_ready_tokens[0]
            print(f"   Closest: {closest['symbol']} with {closest['score']}")


async def main():
    """Main function"""
    
    # Popular trading pairs on HyperLiquid
    symbols = [
        'BTC', 'ETH', 'SOL', 'HYPE',
        'MATIC', 'AVAX', 'ARB', 'OP',
        'DOGE', 'PEPE', 'WIF', 'BONK',
        'SUI', 'APT', 'SEI', 'TIA'
    ]
    
    # Allow custom symbols via command line
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
        print(f"Analyzing custom symbols: {', '.join(symbols)}")
    else:
        print(f"Analyzing {len(symbols)} popular tokens...")
        print("(Usage: python check_token_signals.py BTC ETH SOL)")
    
    print()
    
    analyzer = TokenAnalyzer()
    results = await analyzer.analyze_multiple(symbols)
    
    print_results(results)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis cancelled by user")
        sys.exit(0)
