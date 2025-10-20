#!/usr/bin/env python3
"""
Test CHoCH detection với confirmation logic
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from detectors.choch_detector import ChochDetector
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_choch_confirmation_data():
    """Tạo data với CHoCH pattern và test confirmation"""
    base_time = datetime(2025, 1, 1)
    
    # Scenario 1: CHoCH Up với confirmation thành công
    data = [
        # Pre-trend bars
        [95, 97, 94, 96],     # Bar 0
        [96, 98, 95, 97],     # Bar 1
        [97, 99, 96, 98],     # Bar 2
        [94, 96, 93, 95],     # Bar 3 - Pivot Low
        [95, 97, 94, 96],     # Bar 4
        [98, 100, 97, 99],    # Bar 5 - Pivot High
        [99, 101, 98, 100],   # Bar 6
        [96, 98, 95, 97],     # Bar 7 - Pivot Low (higher)
        [97, 99, 96, 98],     # Bar 8
        [100, 102, 99, 101],  # Bar 9 - Pivot High (higher)
        [101, 103, 100, 102], # Bar 10
        [98, 100, 97, 99],    # Bar 11 - Pivot Low (higher) 
        [99, 101, 98, 100],   # Bar 12
        [102, 104, 101, 103], # Bar 13 - Pivot High (highest for 6-pattern)
        [103, 105, 102, 104], # Bar 14
        
        # Downtrend phase (cần để tạo 6-pattern downtrend)
        [104, 105, 100, 101], # Bar 15 - Start break down
        [101, 102, 98, 99],   # Bar 16 - Lower low
        [99, 101, 97, 100],   # Bar 17 - Bounce
        [100, 101, 95, 96],   # Bar 18 - Lower low
        [96, 98, 94, 97],     # Bar 19 - Bounce  
        [97, 98, 92, 93],     # Bar 20 - Lowest (for 6-pattern)
        
        # CHoCH Up setup
        [93, 94, 91, 92],     # Bar 21 - Pre-CHoCH bar (H=94)
        [92, 99, 91, 98],     # Bar 22 - CHoCH bar: low(91) > low(91), close(98) > high(94), close > pivot4
        [98, 105, 97, 104],   # Bar 23 - Confirmation: low(97) > high(94) của pre-CHoCH ✅
        [104, 106, 103, 105], # Bar 24 - Continue up
    ]
    
    df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close'])
    df['timestamp'] = [base_time + timedelta(minutes=5*i) for i in range(len(df))]
    df = df.set_index('timestamp')
    df['volume'] = 1000  # Dummy volume
    
    return df

def test_choch_confirmation():
    """Test CHoCH confirmation logic"""
    logger.info("=== CHoCH CONFIRMATION TEST ===")
    
    # Tạo data với CHoCH confirmation pattern
    df = create_choch_confirmation_data()
    logger.info(f"Created {len(df)} bars with CHoCH confirmation pattern")
    
    # Print data để kiểm tra
    print("\nPrice data:")
    for i, (ts, row) in enumerate(df.iterrows()):
        print(f"Bar {i:2d} ({ts.strftime('%H:%M')}): O={row['open']:6.1f} H={row['high']:6.1f} L={row['low']:6.1f} C={row['close']:6.1f}")
    
    # Initialize detector
    detector = ChochDetector(
        left=1,  # Pivot length = 1
        right=1,
        keep_pivots=50
    )
    
    print(f"\nProcessing bars sequentially...")
    
    # Process từng bar một để theo dõi
    for i in range(10, len(df)):  # Start từ bar 10 để có đủ history
        current_df = df.iloc[:i+1].copy()
        
        print(f"\n--- Processing bar {i} ({df.index[i].strftime('%H:%M')}) ---")
        print(f"Price: O={df.iloc[i]['open']} H={df.iloc[i]['high']} L={df.iloc[i]['low']} C={df.iloc[i]['close']}")
        
        # Rebuild pivots first, then check CHoCH
        detector.rebuild_pivots("5m", current_df)
        result = detector.process_new_bar("5m", current_df)
        
        if result and (result.get('choch_up') or result.get('choch_down')):
            logger.info(f"🔥 CHoCH DETECTED! Type: {result['signal_type']} at bar {i}")
            logger.info(f"   Direction: {result['direction']}")
            logger.info(f"   Price: {result['price']}")
            logger.info(f"   ✅ Confirmation successful!")
            break
        else:
            print("✅ No signal")

if __name__ == "__main__":
    test_choch_confirmation()