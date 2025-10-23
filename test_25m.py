#!/usr/bin/env python3
"""
Quick test for 25m aggregation
"""
import asyncio
import sys
sys.path.insert(0, '.')

from data.binance_fetcher import BinanceFetcher
from data.timeframe_adapter import TimeframeAdapter

async def test_25m():
    print("Testing 25m aggregation...")
    
    # Initialize
    base_fetcher = BinanceFetcher()
    await base_fetcher.initialize()
    adapter = TimeframeAdapter(base_fetcher)
    
    # Test 25m for BTCUSDT
    symbol = 'BTCUSDT'
    print(f"\nFetching 25m candles for {symbol}...")
    df_25m = await adapter.fetch_historical(symbol, '25m', limit=10)
    
    print(f"✓ Received {len(df_25m)} 25m candles")
    print(f"  First: {df_25m.index[0]}")
    print(f"  Last:  {df_25m.index[-1]}")
    print(f"  Last close: ${df_25m['close'].iloc[-1]:,.2f}")
    
    # Check alignment (25m candles should be at :00, :25, :50 of each hour)
    print("\n25m candle times (first 5):")
    for i in range(min(5, len(df_25m))):
        ts = df_25m.index[i]
        print(f"  {ts} (minute: {ts.minute})")
    
    # Verify minutes are multiples of 5 (since 25 % 5 = 0)
    for ts in df_25m.index[:5]:
        minute = ts.minute
        assert minute % 5 == 0, f"25m candle not aligned: {ts}"
    print("✓ All candles properly aligned")
    
    await adapter.close()
    print("\n✅ 25m test PASSED!")

if __name__ == '__main__':
    asyncio.run(test_25m())
