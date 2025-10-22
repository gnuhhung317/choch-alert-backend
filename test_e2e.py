#!/usr/bin/env python3
"""
End-to-end test for unlimited pairs functionality
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

async def test_end_to_end():
    """Test the system with config MAX_PAIRS"""
    logger.info("=== End-to-End Test ===")
    logger.info(f"Config MAX_PAIRS: {config.MAX_PAIRS}")
    
    fetcher = BinanceFetcher()
    
    # Use the config value
    pairs = await fetcher.get_all_usdt_pairs(
        min_volume_24h=config.MIN_VOLUME_24H,
        quote=config.QUOTE_CURRENCY,
        max_pairs=config.MAX_PAIRS
    )
    
    mode_text = "UNLIMITED" if config.MAX_PAIRS == 0 else f"LIMITED to {config.MAX_PAIRS}"
    logger.info(f"Fetched {len(pairs)} pairs in {mode_text} mode")
    
    logger.info(f"First 10 pairs: {pairs[:10]}")
    
    if config.MAX_PAIRS == 0:
        logger.info("✅ UNLIMITED mode working correctly!")
        assert len(pairs) > 100, f"Expected many pairs in unlimited mode, got {len(pairs)}"
    else:
        logger.info(f"✅ LIMITED mode working correctly!")
        assert len(pairs) <= config.MAX_PAIRS, f"Expected <= {config.MAX_PAIRS} pairs, got {len(pairs)}"
    
    logger.info("🎉 End-to-end test passed!")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())