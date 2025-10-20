#!/usr/bin/env python3
"""
Quick test script to verify scheduler timing logic
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.timeframe_scheduler import TimeframeScheduler
from datetime import datetime
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_scheduler():
    """Test scheduler timing calculations"""
    print("🔍 Testing TimeframeScheduler timing logic...")
    
    scheduler = TimeframeScheduler(['5m', '15m', '30m', '1h'])
    
    now = datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    for timeframe in ['5m', '15m', '30m', '1h']:
        print(f"\n📊 {timeframe} timeframe:")
        
        # Test prev/next close calculations
        prev_close = scheduler.get_prev_candle_close_time(timeframe)
        next_close = scheduler.get_next_candle_close_time(timeframe)
        
        print(f"  Previous close: {prev_close.strftime('%H:%M:%S')}")
        print(f"  Next close:     {next_close.strftime('%H:%M:%S')}")
        
        # Test should_scan
        should_scan = scheduler.should_scan(timeframe)
        print(f"  Should scan:    {should_scan}")
        
        # Test wait time
        wait_time = scheduler.get_wait_time(timeframe)
        print(f"  Wait time:      {wait_time:.0f}s")
        
        # Mark as scanned and test again
        scheduler.mark_scanned(timeframe)
        should_scan_after = scheduler.should_scan(timeframe)
        print(f"  After mark:     {should_scan_after}")
    
    print("\n" + "=" * 60)
    print("✅ Scheduler test completed")

if __name__ == "__main__":
    test_scheduler()