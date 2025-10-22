#!/usr/bin/env python3
"""
Test script to validate unlimited pairs functionality with max_pairs=0
"""

import asyncio
import sys
import os
import logging

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.binance_fetcher import BinanceFetcher
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_unlimited_pairs():
    """Test unlimited pairs functionality"""
    logger.info("Testing unlimited pairs functionality...")
    
    fetcher = BinanceFetcher()
    
    # Test with max_pairs=0 (unlimited)
    logger.info("\n=== Testing UNLIMITED mode (max_pairs=0) ===")
    unlimited_pairs = await fetcher.get_all_usdt_pairs(max_pairs=0)
    logger.info(f"Unlimited mode returned {len(unlimited_pairs)} pairs")
    
    # Test with max_pairs=10 (limited)
    logger.info("\n=== Testing LIMITED mode (max_pairs=10) ===")
    limited_pairs = await fetcher.get_all_usdt_pairs(max_pairs=10)
    logger.info(f"Limited mode returned {len(limited_pairs)} pairs")
    
    # Test with max_pairs=100 (current default)
    logger.info("\n=== Testing LIMITED mode (max_pairs=100) ===")
    default_pairs = await fetcher.get_all_usdt_pairs(max_pairs=100)
    logger.info(f"Default mode returned {len(default_pairs)} pairs")
    
    # Verify unlimited is actually more than limited
    logger.info(f"\n=== COMPARISON ===")
    logger.info(f"Unlimited (max_pairs=0): {len(unlimited_pairs)} pairs")
    logger.info(f"Limited (max_pairs=10): {len(limited_pairs)} pairs")
    logger.info(f"Limited (max_pairs=100): {len(default_pairs)} pairs")
    
    # Show some examples
    logger.info(f"\nUnlimited pairs (first 20): {unlimited_pairs[:20]}")
    logger.info(f"Limited pairs (all 10): {limited_pairs}")
    
    # Validation
    assert len(unlimited_pairs) > len(limited_pairs), "Unlimited should have more pairs than limited"
    assert len(limited_pairs) <= 10, "Limited should respect max_pairs"
    assert len(default_pairs) <= 100, "Default should respect max_pairs"
    
    logger.info("\n✅ All tests passed! Unlimited pairs functionality works correctly.")

if __name__ == "__main__":
    asyncio.run(test_unlimited_pairs())