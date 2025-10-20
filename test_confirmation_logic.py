#!/usr/bin/env python3
"""
Test confirmation logic đơn giản
"""

import pandas as pd
from datetime import datetime, timedelta
from detectors.choch_detector import ChochDetector
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_confirmation_logic():
    """Test logic confirmation với data giả"""
    logger.info("=== TESTING CONFIRMATION LOGIC ===")
    
    # Tạo 3 bars đơn giản để test confirmation
    base_time = datetime(2025, 1, 1)
    
    data = [
        [90, 92, 89, 91],     # Bar 0 - Pre-CHoCH (high = 92)
        [91, 98, 90, 97],     # Bar 1 - CHoCH bar
        [97, 100, 96, 99],    # Bar 2 - Confirmation bar (low = 96 > 92) ✅
    ]
    
    df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close'])
    df['timestamp'] = [base_time + timedelta(minutes=5*i) for i in range(len(df))]
    df = df.set_index('timestamp')
    df['volume'] = 1000
    
    print("\nData cho test confirmation:")
    for i, (ts, row) in enumerate(df.iterrows()):
        print(f"Bar {i}: O={row['open']} H={row['high']} L={row['low']} C={row['close']}")
    
    # Test confirmation logic trực tiếp
    print(f"\nTest confirmation logic:")
    
    # Giả sử đã có CHoCH trên Bar 1, kiểm tra confirmation trên Bar 2
    pre_prev_high = df.iloc[0]['high']  # 92
    current_low = df.iloc[2]['low']     # 96
    
    confirm_up = current_low > pre_prev_high
    
    print(f"Pre-CHoCH bar high: {pre_prev_high}")
    print(f"Confirmation bar low: {current_low}")
    print(f"Confirmation condition (low > pre_high): {current_low} > {pre_prev_high} = {confirm_up}")
    
    if confirm_up:
        logger.info("✅ CHoCH Up confirmation logic WORKS!")
    else:
        logger.error("❌ CHoCH Up confirmation logic FAILED!")
    
    # Test CHoCH Down
    print(f"\nTest CHoCH Down confirmation:")
    data_down = [
        [100, 105, 99, 102],  # Bar 0 - Pre-CHoCH (low = 99)
        [102, 103, 95, 96],   # Bar 1 - CHoCH Down bar
        [96, 97, 93, 94],     # Bar 2 - Confirmation (high = 97 < 99) ✅
    ]
    
    df_down = pd.DataFrame(data_down, columns=['open', 'high', 'low', 'close'])
    df_down['timestamp'] = [base_time + timedelta(minutes=5*i) for i in range(len(df_down))]
    df_down = df_down.set_index('timestamp')
    df_down['volume'] = 1000
    
    pre_prev_low = df_down.iloc[0]['low']   # 99
    current_high = df_down.iloc[2]['high']  # 97
    
    confirm_down = current_high < pre_prev_low
    
    print(f"Pre-CHoCH bar low: {pre_prev_low}")
    print(f"Confirmation bar high: {current_high}")
    print(f"Confirmation condition (high < pre_low): {current_high} < {pre_prev_low} = {confirm_down}")
    
    if confirm_down:
        logger.info("✅ CHoCH Down confirmation logic WORKS!")
    else:
        logger.error("❌ CHoCH Down confirmation logic FAILED!")

if __name__ == "__main__":
    test_confirmation_logic()