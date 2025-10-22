#!/usr/bin/env python3
"""
Debug CHoCH Timing Analysis
===========================

Phân tích timing delay trong CHoCH detection để hiểu tại sao alert muộn 2 candles.

VẤN ĐỀ CHÍNH:
1. CHoCH xảy ra tại candle N
2. Cần confirmation tại candle N+1  
3. Alert chỉ fire sau khi candle N+1 đóng + 30s buffer
4. Kết quả: Alert muộn ~1.5-2 candles so với CHoCH thực tế

"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.binance_fetcher import BinanceFetcher
from detectors.choch_detector import ChochDetector
from utils.timeframe_scheduler import TimeframeScheduler
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def simulate_choch_timing_delay():
    """
    Simulate CHoCH detection timing để hiểu delay pattern
    """
    print("=" * 80)
    print("🕐 CHoCH TIMING DELAY ANALYSIS")
    print("=" * 80)
    
    # Initialize components
    fetcher = BinanceFetcher()
    detector = ChochDetector()
    scheduler = TimeframeScheduler(['15m'])
    
    symbol = "BTCUSDT"
    timeframe = "15m"
    
    print(f"\n📊 Fetching recent data for {symbol} {timeframe}...")
    
    # Fetch recent data
    try:
        df = fetcher.fetch_historical(symbol, timeframe, limit=200)
        if df is None or df.empty:
            print("❌ No data fetched")
            return
            
        print(f"✅ Fetched {len(df)} candles")
        print(f"📅 Data range: {df.index[0]} to {df.index[-1]}")
        
        # Show last few candles
        print(f"\n🕯️ LAST 5 CANDLES:")
        for i in range(-5, 0):
            candle = df.iloc[i]
            candle_time = df.index[i]
            print(f"  {candle_time} | O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f}")
        
        # Analyze scheduler timing
        print(f"\n⏰ SCHEDULER TIMING ANALYSIS:")
        now = datetime.now()
        prev_close = scheduler.get_prev_candle_close_time(timeframe)
        next_close = scheduler.get_next_candle_close_time(timeframe)
        buffer_ready = prev_close + timedelta(seconds=30)
        
        print(f"  Current time: {now.strftime('%H:%M:%S')}")
        print(f"  Previous candle close: {prev_close.strftime('%H:%M:%S')}")
        print(f"  Next candle close: {next_close.strftime('%H:%M:%S')}")
        print(f"  Buffer ready time: {buffer_ready.strftime('%H:%M:%S')} (+30s)")
        
        # Calculate delays
        time_since_prev_close = (now - prev_close).total_seconds()
        time_to_next_close = (next_close - now).total_seconds()
        
        print(f"  Time since previous close: {time_since_prev_close:.1f}s")
        print(f"  Time to next close: {time_to_next_close:.1f}s")
        
        should_scan = scheduler.should_scan(timeframe)
        print(f"  Should scan now: {should_scan}")
        
        # Simulate CHoCH detection on current data
        print(f"\n🔍 RUNNING CHoCH DETECTION:")
        choch_up, choch_down = detector.check_choch(df, symbol, timeframe)
        
        if choch_up or choch_down:
            print(f"🚨 CHoCH DETECTED: {'UP' if choch_up else 'DOWN'}")
        else:
            print("⏳ No CHoCH detected in current data")
            
        # Explain timing delay
        print(f"\n📝 TIMING DELAY EXPLANATION:")
        print(f"   1. CHoCH occurs at candle N (structure break)")
        print(f"   2. Confirmation needed at candle N+1 (must wait for close)")
        print(f"   3. Detection runs after N+1 closes + 30s buffer")
        print(f"   4. Alert fires ~1.5-2 candles after actual CHoCH")
        print(f"   5. For {timeframe}: ~22.5-30 minutes delay from actual CHoCH")
        
        # Show potential solutions
        print(f"\n💡 POTENTIAL SOLUTIONS:")
        print(f"   A. Reduce buffer from 30s to 10s (faster but risk incomplete data)")
        print(f"   B. Add 'early warning' mode (fire on structure break, confirm later)")
        print(f"   C. Use shorter confirmation (1 candle instead of 2)")
        print(f"   D. Real-time monitoring with WebSocket (detect during candle formation)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate_choch_timing_delay()