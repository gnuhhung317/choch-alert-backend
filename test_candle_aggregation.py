#!/usr/bin/env python3
"""
Test candle aggregation functionality
Tests both CandleAggregator and TimeframeAdapter
"""
import asyncio
import logging
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, '.')

from data.candle_aggregator import CandleAggregator
from data.binance_fetcher import BinanceFetcher
from data.timeframe_adapter import TimeframeAdapter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_5m_data(num_candles: int = 100) -> pd.DataFrame:
    """Create sample 5m OHLCV data for testing"""
    start_time = datetime(2025, 10, 23, 10, 0, 0)
    timestamps = [start_time + timedelta(minutes=5*i) for i in range(num_candles)]
    
    df = pd.DataFrame({
        'open': np.random.uniform(50000, 51000, num_candles),
        'high': np.random.uniform(50500, 51500, num_candles),
        'low': np.random.uniform(49500, 50500, num_candles),
        'close': np.random.uniform(50000, 51000, num_candles),
        'volume': np.random.uniform(100, 1000, num_candles)
    }, index=pd.DatetimeIndex(timestamps))
    
    # Fix OHLC relationship
    df['high'] = df[['open', 'high', 'close']].max(axis=1) + 100
    df['low'] = df[['open', 'low', 'close']].min(axis=1) - 100
    
    return df


def test_candle_aggregator():
    """Test CandleAggregator with sample data"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: CandleAggregator - Pure Logic Test")
    logger.info("="*80)
    
    aggregator = CandleAggregator()
    
    # Create 100 5m candles
    df_5m = create_sample_5m_data(100)
    logger.info(f"✓ Created {len(df_5m)} sample 5m candles")
    logger.info(f"  Time range: {df_5m.index[0]} to {df_5m.index[-1]}")
    
    # Test 10m aggregation (2:1)
    logger.info("\n--- Test 10m aggregation (100 5m → 50 10m) ---")
    df_10m = aggregator.aggregate(df_5m, target_minutes=10, base_minutes=5)
    logger.info(f"✓ Result: {len(df_10m)} 10m candles (expected 50)")
    assert len(df_10m) == 50, f"Expected 50, got {len(df_10m)}"
    assert aggregator.validate_aggregation(df_5m, df_10m, 10, 5), "Validation failed"
    
    # Test 20m aggregation (4:1)
    logger.info("\n--- Test 20m aggregation (100 5m → 25 20m) ---")
    df_20m = aggregator.aggregate(df_5m, target_minutes=20, base_minutes=5)
    logger.info(f"✓ Result: {len(df_20m)} 20m candles (expected 25)")
    assert len(df_20m) == 25, f"Expected 25, got {len(df_20m)}"
    assert aggregator.validate_aggregation(df_5m, df_20m, 20, 5), "Validation failed"
    
    # Test 40m aggregation (8:1)
    logger.info("\n--- Test 40m aggregation (100 5m → 12 40m) ---")
    df_40m = aggregator.aggregate(df_5m, target_minutes=40, base_minutes=5)
    logger.info(f"✓ Result: {len(df_40m)} 40m candles (expected 12)")
    assert len(df_40m) == 12, f"Expected 12, got {len(df_40m)}"  # 100/8 = 12.5, only complete = 12
    assert aggregator.validate_aggregation(df_5m, df_40m, 40, 5), "Validation failed"
    
    # Test 50m aggregation (10:1)
    logger.info("\n--- Test 50m aggregation (100 5m → 10 50m) ---")
    df_50m = aggregator.aggregate(df_5m, target_minutes=50, base_minutes=5)
    logger.info(f"✓ Result: {len(df_50m)} 50m candles (expected 10)")
    assert len(df_50m) == 10, f"Expected 10, got {len(df_50m)}"
    assert aggregator.validate_aggregation(df_5m, df_50m, 50, 5), "Validation failed"
    
    # Test required candles calculation
    logger.info("\n--- Test required candles calculation ---")
    test_cases = [
        (50, 10, 100),  # 50 10m needs 100 5m
        (50, 20, 200),  # 50 20m needs 200 5m
        (50, 40, 400),  # 50 40m needs 400 5m
        (50, 50, 500),  # 50 50m needs 500 5m
    ]
    
    for target_candles, target_minutes, expected in test_cases:
        required = aggregator.calculate_required_base_candles(target_candles, target_minutes, 5)
        logger.info(f"  {target_candles} {target_minutes}m candles → need {required} 5m candles (expected {expected})")
        assert required == expected, f"Expected {expected}, got {required}"
    
    logger.info("\n✅ All CandleAggregator tests PASSED!")
    return True


async def test_timeframe_adapter_mock():
    """Test TimeframeAdapter with mock data (no real Binance connection)"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: TimeframeAdapter - Mock Data Test")
    logger.info("="*80)
    
    # Test helper methods
    logger.info("\n--- Test helper methods ---")
    assert TimeframeAdapter.is_aggregated_timeframe('10m') == True
    assert TimeframeAdapter.is_aggregated_timeframe('5m') == False
    logger.info("✓ is_aggregated_timeframe() works correctly")
    
    assert TimeframeAdapter.get_base_timeframe('10m') == '5m'
    assert TimeframeAdapter.get_base_timeframe('15m') == '15m'
    logger.info("✓ get_base_timeframe() works correctly")
    
    assert TimeframeAdapter.get_multiplier('10m') == 2
    assert TimeframeAdapter.get_multiplier('20m') == 4
    assert TimeframeAdapter.get_multiplier('5m') == 1
    logger.info("✓ get_multiplier() works correctly")
    
    assert TimeframeAdapter.convert_tf_to_tradingview('10m') == '10'
    assert TimeframeAdapter.convert_tf_to_tradingview('1h') == '60'
    logger.info("✓ convert_tf_to_tradingview() works correctly")
    
    logger.info("\n✅ All TimeframeAdapter mock tests PASSED!")
    return True


async def test_timeframe_adapter_live():
    """Test TimeframeAdapter with real Binance data"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: TimeframeAdapter - Live Binance Test")
    logger.info("="*80)
    
    try:
        # Initialize fetcher
        base_fetcher = BinanceFetcher()
        await base_fetcher.initialize()
        
        # Wrap with adapter
        adapter = TimeframeAdapter(base_fetcher)
        
        symbol = 'BTCUSDT'
        
        # Test 1: Native timeframe (passthrough)
        logger.info(f"\n--- Test native timeframe (5m) for {symbol} ---")
        df_5m = await adapter.fetch_historical(symbol, '5m', limit=50)
        logger.info(f"✓ Received {len(df_5m)} 5m candles")
        assert len(df_5m) <= 50, f"Expected ≤50, got {len(df_5m)}"
        logger.info(f"  First candle: {df_5m.index[0]}")
        logger.info(f"  Last candle: {df_5m.index[-1]}")
        
        # Test 2: Aggregated 10m
        logger.info(f"\n--- Test aggregated timeframe (10m) for {symbol} ---")
        df_10m = await adapter.fetch_historical(symbol, '10m', limit=50)
        logger.info(f"✓ Received {len(df_10m)} 10m candles")
        assert len(df_10m) <= 50, f"Expected ≤50, got {len(df_10m)}"
        logger.info(f"  First candle: {df_10m.index[0]}")
        logger.info(f"  Last candle: {df_10m.index[-1]}")
        
        # Verify 10m candle alignment (should be at :00, :10, :20, :30, :40, :50)
        for ts in df_10m.index[:5]:
            minute = ts.minute
            assert minute % 10 == 0, f"10m candle not aligned: {ts}"
        logger.info("✓ 10m candles are properly aligned (:00, :10, :20, ...)")
        
        # Test 3: Aggregated 20m
        logger.info(f"\n--- Test aggregated timeframe (20m) for {symbol} ---")
        df_20m = await adapter.fetch_historical(symbol, '20m', limit=25)
        logger.info(f"✓ Received {len(df_20m)} 20m candles")
        assert len(df_20m) <= 25, f"Expected ≤25, got {len(df_20m)}"
        
        # Verify 20m candle alignment (should be at :00, :20, :40)
        for ts in df_20m.index[:5]:
            minute = ts.minute
            assert minute % 20 == 0, f"20m candle not aligned: {ts}"
        logger.info("✓ 20m candles are properly aligned (:00, :20, :40)")
        
        # Test 4: Aggregated 50m
        logger.info(f"\n--- Test aggregated timeframe (50m) for {symbol} ---")
        df_50m = await adapter.fetch_historical(symbol, '50m', limit=10)
        logger.info(f"✓ Received {len(df_50m)} 50m candles")
        assert len(df_50m) <= 10, f"Expected ≤10, got {len(df_50m)}"
        
        # Verify 50m candle alignment (should be at :00, :50 of each hour)
        # 50m candles start at: 00:00, 00:50, 01:40, 02:30, 03:20, 04:10, 05:00, 05:50...
        # Pattern: minute should be 0, 10, 20, 30, 40, or 50
        for ts in df_50m.index[:5]:
            minute = ts.minute
            assert minute % 10 == 0, f"50m candle not aligned: {ts} (minute={minute})"
        logger.info("✓ 50m candles are properly aligned (starts every 50 minutes)")
        
        # Compare data quality
        logger.info("\n--- Data quality check ---")
        logger.info(f"5m last close: ${df_5m['close'].iloc[-1]:,.2f}")
        logger.info(f"10m last close: ${df_10m['close'].iloc[-1]:,.2f}")
        logger.info(f"20m last close: ${df_20m['close'].iloc[-1]:,.2f}")
        
        # Close connection
        await adapter.close()
        
        logger.info("\n✅ All TimeframeAdapter live tests PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Live test failed: {e}", exc_info=True)
        return False


async def main():
    """Run all tests"""
    logger.info("\n" + "="*80)
    logger.info("CANDLE AGGREGATION FEATURE - COMPREHENSIVE TESTS")
    logger.info("="*80)
    
    results = []
    
    # Test 1: Pure aggregation logic
    try:
        result = test_candle_aggregator()
        results.append(("CandleAggregator", result))
    except Exception as e:
        logger.error(f"❌ CandleAggregator test failed: {e}", exc_info=True)
        results.append(("CandleAggregator", False))
    
    # Test 2: Adapter mock tests
    try:
        result = await test_timeframe_adapter_mock()
        results.append(("TimeframeAdapter Mock", result))
    except Exception as e:
        logger.error(f"❌ TimeframeAdapter mock test failed: {e}", exc_info=True)
        results.append(("TimeframeAdapter Mock", False))
    
    # Test 3: Live Binance test (can be skipped if no connection)
    try:
        logger.info("\nAttempting live Binance test...")
        result = await test_timeframe_adapter_live()
        results.append(("TimeframeAdapter Live", result))
    except Exception as e:
        logger.warning(f"⚠️  Live test skipped/failed: {e}")
        results.append(("TimeframeAdapter Live", None))
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    for test_name, result in results:
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⚠️  SKIPPED"
        logger.info(f"{test_name:30} : {status}")
    
    all_passed = all(r in [True, None] for _, r in results)
    
    if all_passed:
        logger.info("\n🎉 All tests PASSED or SKIPPED!")
        return 0
    else:
        logger.error("\n❌ Some tests FAILED!")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
