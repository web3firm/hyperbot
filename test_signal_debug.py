#!/usr/bin/env python3
"""
Test signal generation with detailed debugging
"""
import asyncio
import os
from dotenv import load_dotenv
from decimal import Decimal
from app.hl.hl_client import HyperLiquidClient
from app.strategies.rule_based.swing_trader import SwingTradingStrategy

async def main():
    load_dotenv()
    
    client = HyperLiquidClient(
        account_address=os.getenv('ACCOUNT_ADDRESS'),
        api_key=os.getenv('ACCOUNT_ADDRESS'),
        api_secret=os.getenv('API_SECRET')
    )
    
    strategy = SwingTradingStrategy('HYPE')
    
    # Get candles
    print("Fetching candles...")
    candles = client.get_candles('HYPE', '1m', 150)
    print(f"✅ Fetched {len(candles)} candles")
    
    # Extract prices for manual indicator calculation
    prices = [Decimal(str(c['close'])) for c in candles]
    current_price = prices[-1]
    
    print(f"\n📊 Current Price: ${current_price}")
    
    # Calculate indicators manually
    rsi = strategy._calculate_rsi(prices, 14)
    ema_fast = strategy._calculate_ema(prices, 21)
    ema_slow = strategy._calculate_ema(prices, 50)
    adx = strategy._calculate_adx(prices, 14)
    atr = strategy._calculate_atr(prices, 14)
    macd = strategy._calculate_macd(prices)
    
    print(f"\n📈 Technical Indicators:")
    print(f"   RSI: {float(rsi):.1f}")
    print(f"   EMA Fast (21): ${float(ema_fast):.2f}")
    print(f"   EMA Slow (50): ${float(ema_slow):.2f}")
    print(f"   Trend: {'UP' if ema_fast > ema_slow else 'DOWN'}")
    print(f"   ADX: {float(adx):.1f}")
    print(f"   ATR: ${float(atr):.4f} ({float(atr/current_price*100):.2f}%)")
    if macd:
        print(f"   MACD: {float(macd['macd']):.4f}")
        print(f"   MACD Signal: {float(macd['signal']):.4f}")
        print(f"   MACD Hist: {float(macd['histogram']):.4f}")
    
    print(f"\n🎯 Strategy Thresholds:")
    print(f"   Min ADX: {strategy.min_adx}")
    print(f"   Min Signal Score: {strategy.min_signal_score}/8")
    print(f"   Min ATR %: {strategy.min_atr_pct}%")
    print(f"   RSI Oversold: < {strategy.rsi_oversold}")
    print(f"   RSI Overbought: > {strategy.rsi_overbought}")
    
    # Check conditions
    print(f"\n✅ Condition Checks:")
    trend = 'up' if ema_fast > ema_slow else 'down'
    atr_pct = atr / current_price * 100
    
    print(f"   ADX >= {strategy.min_adx}: {'✅' if adx >= strategy.min_adx else '❌'} ({float(adx):.1f})")
    print(f"   ATR >= {strategy.min_atr_pct}%: {'✅' if atr_pct >= strategy.min_atr_pct else '❌'} ({float(atr_pct):.2f}%)")
    print(f"   Trend: {trend}")
    
    # Check signal conditions
    print(f"\n🔍 Signal Conditions:")
    if trend == 'up':
        print(f"   LONG conditions:")
        print(f"      RSI < {strategy.rsi_oversold}: {'✅' if rsi < strategy.rsi_oversold else '❌'} (RSI {float(rsi):.1f})")
        print(f"      RSI in pullback (35-45): {'✅' if 35 <= rsi <= 45 else '❌'}")
    else:
        print(f"   SHORT conditions:")
        print(f"      RSI < 35 AND ADX > 30 (dump): {'✅' if rsi < 35 and adx > 30 else '❌'} (RSI {float(rsi):.1f}, ADX {float(adx):.1f})")
        print(f"      RSI > {strategy.rsi_overbought}: {'✅' if rsi > strategy.rsi_overbought else '❌'}")
        print(f"      RSI in pullback (55-65): {'✅' if 55 <= rsi <= 65 else '❌'}")
    
    # Prepare market data
    market_data = {
        'price': float(current_price),
        'volume': candles[-1]['volume'],
        'candles': candles
    }
    
    account_state = {
        'account_value': 100,
        'positions': []
    }
    
    print(f"\n🤖 Generating signal...")
    signal = await strategy.generate_signal(market_data, account_state)
    
    if signal:
        print(f"\n✅ SIGNAL GENERATED!")
        print(f"   Action: {signal['action'].upper()}")
        print(f"   Entry: ${signal['entry_price']}")
        print(f"   Size: {signal['quantity']}")
        print(f"   SL: ${signal['stop_loss']}")
        print(f"   TP: ${signal['take_profit']}")
    else:
        print(f"\n❌ NO SIGNAL")
        print(f"   Check bot logs for: '⏭️ No signal - Trend: ...'")

if __name__ == '__main__':
    asyncio.run(main())
