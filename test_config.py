#!/usr/bin/env python3
"""
Test config with MAX_PAIRS=0 (unlimited mode)
"""

import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config

def test_config():
    """Test config with MAX_PAIRS=0"""
    print("=== Config Test ===")
    print(f"MAX_PAIRS: {config.MAX_PAIRS}")
    print(f"Type: {type(config.MAX_PAIRS)}")
    
    if config.MAX_PAIRS == 0:
        print("✅ UNLIMITED mode detected (MAX_PAIRS=0)")
    else:
        print(f"✅ LIMITED mode detected (MAX_PAIRS={config.MAX_PAIRS})")
    
    print(f"QUOTE_CURRENCY: {config.QUOTE_CURRENCY}")
    print(f"MIN_VOLUME_24H: {config.MIN_VOLUME_24H}")
    
    # Test the conditional logic
    mode_text = "UNLIMITED" if config.MAX_PAIRS == 0 else f"LIMITED to {config.MAX_PAIRS}"
    print(f"Mode text: {mode_text}")

if __name__ == "__main__":
    test_config()