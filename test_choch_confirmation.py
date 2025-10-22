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
    """Tạo data với CHoCH pattern và test confirmation (8-pivot pattern)"""
    base_time = datetime(2025, 1, 1)
    
    # Scenario: 8-pivot pattern với các điều kiện breakout
    # P1(L) < P3(L) < P5(L) < P7(L) và P2(H) < P4(H) < P6(H) < P8(H)  
    # Up breakout: low[5] > high[2] và low[3] > low[1]
    data = [
        # Bars để tạo 8-pivot ascending pattern
        [100, 102, 99, 101],  # Bar 0
        [101, 103, 100, 102], # Bar 1  
        [102, 104, 95, 96],   # Bar 2 - P1 (L=95) Pivot Low 1
        [96, 98, 95, 97],     # Bar 3
        [97, 102, 96, 101],   # Bar 4 - P2 (H=102) Pivot High 1
        [101, 103, 100, 102], # Bar 5
        [102, 104, 98, 99],   # Bar 6 - P3 (L=98) Pivot Low 2, low[3]=98 > low[1]=95 ✓
        [99, 101, 98, 100],   # Bar 7
        [100, 106, 99, 105],  # Bar 8 - P4 (H=106) Pivot High 2
        [105, 107, 104, 106], # Bar 9
        [106, 108, 103, 104], # Bar 10 - P5 (L=103) Pivot Low 3, low[5]=103 > high[2]=102 ✓
        [104, 106, 103, 105], # Bar 11
        [105, 110, 104, 109], # Bar 12 - P6 (H=110) Pivot High 3
        [109, 111, 108, 110], # Bar 13
        [110, 112, 105, 106], # Bar 14 - P7 (L=105) Pivot Low 4 (retest P4=106)
        [106, 108, 105, 107], # Bar 15
        [107, 115, 106, 114], # Bar 16 - P8 (H=115) Pivot High 4 (highest)
        
        # Transition bars
        [114, 116, 113, 115], # Bar 17
        [115, 117, 114, 116], # Bar 18
        
        # CHoCH setup - break down then up
        [116, 117, 110, 111], # Bar 19 - Start break down
        [111, 112, 107, 108], # Bar 20 - Lower
        [108, 109, 105, 106], # Bar 21 - Even lower
        [106, 107, 103, 104], # Bar 22 - Lowest point
        [104, 105, 102, 103], # Bar 23 - Pre-CHoCH bar (H=105)
        [103, 118, 102, 117], # Bar 24 - CHoCH bar: close(117) > high(105), close > pivot6
        [117, 120, 116, 119], # Bar 25 - Confirmation: low(116) > high(105) ✅
    ]
    
    df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close'])
    df['timestamp'] = [base_time + timedelta(minutes=5*i) for i in range(len(df))]
    df = df.set_index('timestamp')
    df['volume'] = 1000  # Dummy volume
    
    return df

def test_choch_confirmation():
    """Test CHoCH confirmation logic with 8-pivot pattern"""
    logger.info("=== CHoCH CONFIRMATION TEST (8-PIVOT) ===")
    
    # Tạo data với CHoCH confirmation pattern
    df = create_choch_confirmation_data()
    logger.info(f"Created {len(df)} bars with CHoCH confirmation pattern (8-pivot)")
    
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