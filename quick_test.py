#!/usr/bin/env python3
"""
Quick test với main application - 1 symbol only
"""

import asyncio
import logging
from data.binance_fetcher import BinanceFetcher
from detectors.choch_detector import ChochDetector

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def quick_test():
    """Test nhanh CHoCH confirmation với 1 symbol"""
    logger.info("=== QUICK CHOCH CONFIRMATION TEST ===")
    
    # Initialize components
    fetcher = BinanceFetcher()
    detector = ChochDetector(left=1, right=1, keep_pivots=200)
    
    symbol = "BTCUSDT"
    timeframe = "5m"
    
    try:
        # Fetch recent data
        logger.info(f"Fetching data for {symbol} {timeframe}...")
        df = await fetcher.fetch_historical(symbol, timeframe, limit=100)
        logger.info(f"Fetched {len(df)} bars")
        
        # Rebuild pivots
        logger.info("Rebuilding pivots...")
        pivot_count = detector.rebuild_pivots(timeframe, df)
        logger.info(f"Built {pivot_count} pivots")
        
        # Check for CHoCH with confirmation
        logger.info("Checking for CHoCH with confirmation...")
        result = detector.process_new_bar(timeframe, df)
        
        if result and (result.get('choch_up') or result.get('choch_down')):
            logger.info(f"🔥 CHoCH DETECTED!")
            logger.info(f"   Type: {result['signal_type']}")
            logger.info(f"   Direction: {result['direction']}")
            logger.info(f"   Price: {result['price']}")
            logger.info(f"   Timestamp: {result['timestamp']}")
            logger.info(f"   ✅ Confirmation successful!")
        else:
            logger.info("✅ No CHoCH signal detected")
        
        # Show last few bars for context
        logger.info("\nLast 5 bars for context:")
        for i in range(-5, 0):
            bar = df.iloc[i]
            ts = df.index[i]
            logger.info(f"  Bar {i}: {ts} | O:{bar['open']:.4f} H:{bar['high']:.4f} L:{bar['low']:.4f} C:{bar['close']:.4f}")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
    finally:
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(quick_test())