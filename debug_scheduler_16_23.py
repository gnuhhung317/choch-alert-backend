#!/usr/bin/env python3
"""
Debug scheduler logic at 16:23 for 20m timeframe
"""
from utils.timeframe_scheduler import TimeframeScheduler
from datetime import datetime
import logging
import unittest.mock

logging.basicConfig(level=logging.DEBUG)

scheduler = TimeframeScheduler(['10m', '20m', '25m'])

# Test at 16:23 (current time from log)
test_time = datetime(2025, 10, 23, 16, 23, 34)
print(f'Testing at time: {test_time.strftime("%H:%M:%S")}')

with unittest.mock.patch('utils.timeframe_scheduler.datetime') as mock_dt:
    mock_dt.now.return_value = test_time
    mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    
    for tf in ['10m', '20m', '25m']:
        prev_close = scheduler.get_prev_candle_close_time(tf)
        next_close = scheduler.get_next_candle_close_time(tf)
        should_scan = scheduler.should_scan(tf)
        
        print(f'\n{tf}:')
        print(f'  Prev close: {prev_close.strftime("%H:%M:%S")}')
        print(f'  Next close: {next_close.strftime("%H:%M:%S")}')
        print(f'  Should scan: {should_scan}')
        
        # For 20m at 16:23:
        # - Candles close at: 16:00, 16:20, 16:40
        # - Prev close should be: 16:20 (just closed 3 minutes ago)
        # - Next close should be: 16:40
        # - Should scan: False (need to wait until 16:20:30)
        
        if tf == '20m':
            print(f'  Expected prev: 16:20:00')
            print(f'  Expected next: 16:40:00')
            print(f'  Expected should_scan: False (wait until 16:20:30)')
