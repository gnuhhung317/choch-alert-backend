"""
Aligned Candle Aggregator - Aggregates candles with FIXED alignment to reference times

This module solves the alignment problem for custom timeframes (10m, 20m, 25m, 40m)
by using FIXED REFERENCE POINTS.

PROBLEM: 
- Pandas resample() may not align correctly with exchange candle times
- Some timeframes (25m) don't divide evenly into 24h, so can't use midnight alignment
- Need exact alignment with exchange candles

SOLUTION:
- Use FIXED REFERENCE DATETIME for each timeframe
- Calculate all candle periods relative to this reference
- For timeframes that divide 24h evenly (10m, 20m, 40m): can use midnight
- For 25m: must use absolute reference point (e.g., 2025-10-24 17:05:00)

REFERENCE TIMES (provided by user):
- 10m: 2025-10-24 17:10 UTC -> Can use midnight (1440 % 10 == 0)
- 20m: 2025-10-24 17:20 UTC -> Can use midnight (1440 % 20 == 0)
- 25m: 2025-10-24 17:05 UTC -> MUST use fixed ref (1440 % 25 != 0)
- 40m: 2025-10-24 16:40 UTC -> Can use midnight (1440 % 40 == 0)

ALGORITHM:
1. For each timestamp, calculate: periods_from_ref = (timestamp - reference) / interval
2. Round down to get period_index
3. Period start = reference + (period_index × interval)
"""
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class AlignedCandleAggregator:
    """
    Candle aggregator with fixed alignment to reference times.
    
    Uses ABSOLUTE REFERENCE POINTS to ensure perfect alignment.
    """
    
    # Configuration: timeframe -> reference datetime
    # These are the EXACT opening times of candles provided by the user
    TIMEFRAME_REFERENCES = {
        '10m': datetime(2025, 10, 24, 17, 10, 0),  # Can use any midnight, but use this for consistency
        '20m': datetime(2025, 10, 24, 17, 20, 0),  # Can use any midnight, but use this for consistency
        '25m': datetime(2025, 10, 24, 17, 5, 0),   # MUST use this specific time (doesn't align to midnight)
        '40m': datetime(2025, 10, 24, 16, 40, 0),  # Can use any midnight, but use this for consistency
        '50m': datetime(2025, 10, 20, 0, 0, 0),    # Generic Monday midnight
    }
    
    @staticmethod
    def get_candle_period_start(timestamp: datetime, interval_minutes: int, reference_time: datetime) -> datetime:
        """
        Calculate the start time of the candle period that contains this timestamp.
        
        Uses FIXED REFERENCE POINT approach:
        - Calculate how many complete periods exist between reference and timestamp
        - Period start = reference + (period_index × interval)
        
        Args:
            timestamp: The timestamp to check
            interval_minutes: Candle interval in minutes (e.g., 25 for 25m)
            reference_time: Fixed reference datetime (a known candle opening time)
        
        Returns:
            Start time of the candle period
        
        Example:
            For 25m timeframe with reference=2025-10-24 17:05:00:
            - timestamp: 2025-10-24 17:15 -> returns 2025-10-24 17:05 (period 0)
            - timestamp: 2025-10-24 17:30 -> returns 2025-10-24 17:30 (period 1)
            - timestamp: 2025-10-24 16:50 -> returns 2025-10-24 16:40 (period -1)
        """
        # Calculate time difference in minutes
        diff_seconds = (timestamp - reference_time).total_seconds()
        diff_minutes = diff_seconds / 60
        
        # Calculate which period this timestamp falls into
        # Use floor division to always round down
        period_index = int(diff_minutes // interval_minutes)
        
        # Calculate the start of this period
        period_start = reference_time + timedelta(minutes=period_index * interval_minutes)
        
        return period_start
    
    @staticmethod
    def aggregate(df: pd.DataFrame, target_timeframe: str, base_minutes: int = 5) -> pd.DataFrame:
        """
        Aggregate 5m candles into custom timeframe with fixed alignment.
        
        Args:
            df: DataFrame with OHLCV data and datetime index (5m candles)
            target_timeframe: Target timeframe string (e.g., '10m', '25m', '40m')
            base_minutes: Base timeframe in minutes (default: 5)
        
        Returns:
            DataFrame with aggregated candles (OHLCV format)
            Only complete candles are returned
        
        Example:
            df_5m = ... # 100 5m candles
            df_25m = AlignedCandleAggregator.aggregate(df_5m, '25m')
            # Returns 25m candles aligned to reference point
        """
        if df is None or len(df) == 0:
            logger.warning("[AlignedAggregator] Empty DataFrame provided")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        # Parse target timeframe
        if not target_timeframe.endswith('m'):
            raise ValueError(f"Invalid timeframe format: {target_timeframe}")
        
        target_minutes = int(target_timeframe[:-1])
        
        if target_minutes % base_minutes != 0:
            raise ValueError(f"target_minutes ({target_minutes}) must be divisible by base_minutes ({base_minutes})")
        
        # Get reference time for this timeframe
        if target_timeframe not in AlignedCandleAggregator.TIMEFRAME_REFERENCES:
            raise ValueError(f"No reference time configured for {target_timeframe}")
        
        reference_time = AlignedCandleAggregator.TIMEFRAME_REFERENCES[target_timeframe]
        
        logger.info(f"[AlignedAggregator] Aggregating {len(df)} {base_minutes}m candles -> {target_timeframe} "
                   f"(interval={target_minutes}m, reference={reference_time.strftime('%Y-%m-%d %H:%M')})")
        
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        
        # Assign each 5m candle to its target period
        # Each period is identified by its start time
        df_with_period = df.copy()
        df_with_period['period_start'] = df_with_period.index.map(
            lambda ts: AlignedCandleAggregator.get_candle_period_start(ts, target_minutes, reference_time)
        )
        
        # Debug: Show period assignments for first few candles
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[AlignedAggregator] Period assignments (first 10):")
            for i, (idx, row) in enumerate(df_with_period.head(10).iterrows()):
                logger.debug(f"  {idx.strftime('%H:%M')} -> period starts at {row['period_start'].strftime('%H:%M')}")
        
        # Group by period and aggregate
        grouped = df_with_period.groupby('period_start')
        
        agg_dict = {
            'open': 'first',    # First open in the period
            'high': 'max',      # Highest high in the period
            'low': 'min',       # Lowest low in the period
            'close': 'last',    # Last close in the period
            'volume': 'sum'     # Total volume in the period
        }
        
        df_aggregated = grouped.agg(agg_dict)
        
        # Filter: Only keep complete periods
        # A complete period should have exactly (target_minutes / base_minutes) candles
        expected_candles_per_period = target_minutes // base_minutes
        period_counts = grouped.size()
        complete_periods = period_counts[period_counts == expected_candles_per_period].index
        
        df_complete = df_aggregated.loc[complete_periods].copy()
        
        incomplete_count = len(df_aggregated) - len(df_complete)
        if incomplete_count > 0:
            logger.debug(f"[AlignedAggregator] Filtered out {incomplete_count} incomplete periods")
        
        logger.info(f"[AlignedAggregator] ✓ Aggregated {len(df)} {base_minutes}m -> {len(df_complete)} {target_timeframe} candles (complete only)")
        
        # Validate OHLC relationships
        if not AlignedCandleAggregator.validate_ohlc(df_complete):
            logger.error(f"[AlignedAggregator] OHLC validation FAILED!")
        
        return df_complete
    
    @staticmethod
    def validate_ohlc(df: pd.DataFrame) -> bool:
        """
        Validate OHLC relationships: low <= open, close <= high
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            True if valid, False otherwise
        """
        if len(df) == 0:
            return True
        
        # Check low <= open <= high
        invalid_open = ((df['low'] > df['open']) | (df['open'] > df['high'])).sum()
        
        # Check low <= close <= high
        invalid_close = ((df['low'] > df['close']) | (df['close'] > df['high'])).sum()
        
        if invalid_open > 0 or invalid_close > 0:
            logger.error(f"[AlignedAggregator] OHLC validation failed: "
                        f"{invalid_open} invalid open, {invalid_close} invalid close")
            return False
        
        return True
    
    @staticmethod
    def verify_alignment(df: pd.DataFrame, target_timeframe: str) -> bool:
        """
        Verify that aggregated candles are aligned correctly.
        
        Checks that candle timestamps match expected pattern based on reference point.
        
        Args:
            df: Aggregated DataFrame
            target_timeframe: Target timeframe (e.g., '25m')
        
        Returns:
            True if alignment is correct, False otherwise
        """
        if len(df) == 0:
            return True
        
        if target_timeframe not in AlignedCandleAggregator.TIMEFRAME_REFERENCES:
            logger.warning(f"[AlignedAggregator] No reference configured for {target_timeframe}")
            return True
        
        target_minutes = int(target_timeframe[:-1])
        reference_time = AlignedCandleAggregator.TIMEFRAME_REFERENCES[target_timeframe]
        
        logger.debug(f"[AlignedAggregator] Verifying alignment for {target_timeframe} "
                    f"(reference={reference_time.strftime('%Y-%m-%d %H:%M')})")
        
        misaligned_count = 0
        for timestamp in df.index:
            # Calculate expected period start for this timestamp
            expected_start = AlignedCandleAggregator.get_candle_period_start(
                timestamp, target_minutes, reference_time
            )
            
            # The timestamp should match the expected period start
            if timestamp != expected_start:
                logger.warning(f"[AlignedAggregator] Misaligned candle at {timestamp.strftime('%Y-%m-%d %H:%M')}: "
                             f"expected {expected_start.strftime('%Y-%m-%d %H:%M')}")
                misaligned_count += 1
        
        if misaligned_count > 0:
            logger.error(f"[AlignedAggregator] Alignment verification FAILED: {misaligned_count}/{len(df)} candles misaligned")
            return False
        
        logger.debug(f"[AlignedAggregator] ✓ Alignment verification PASSED: all {len(df)} candles aligned correctly")
        return True


# Testing and validation
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    import numpy as np
    
    print("=" * 80)
    print("ALIGNED CANDLE AGGREGATOR - TEST")
    print("=" * 80)
    
    # Create sample 5m data for one day
    # Starting from midnight 2025-10-24 00:00
    start_time = datetime(2025, 10, 24, 0, 0, 0)
    
    # Generate 288 5m candles (24 hours)
    num_candles = 288
    timestamps = [start_time + timedelta(minutes=5*i) for i in range(num_candles)]
    
    df_5m = pd.DataFrame({
        'open': np.random.uniform(50000, 51000, num_candles),
        'high': np.random.uniform(50500, 51500, num_candles),
        'low': np.random.uniform(49500, 50500, num_candles),
        'close': np.random.uniform(50000, 51000, num_candles),
        'volume': np.random.uniform(100, 1000, num_candles)
    }, index=pd.DatetimeIndex(timestamps))
    
    # Fix OHLC relationship
    df_5m['high'] = df_5m[['open', 'high', 'close']].max(axis=1) + 100
    df_5m['low'] = df_5m[['open', 'low', 'close']].min(axis=1) - 100
    
    print(f"\n✓ Created {len(df_5m)} 5m candles")
    print(f"  Time range: {df_5m.index[0]} to {df_5m.index[-1]}")
    
    # Test each timeframe
    timeframes_to_test = ['10m', '20m', '25m', '40m']
    
    for tf in timeframes_to_test:
        print(f"\n{'=' * 80}")
        print(f"Testing {tf.upper()} aggregation")
        print('=' * 80)
        
        df_agg = AlignedCandleAggregator.aggregate(df_5m, tf)
        
        print(f"\nResult: {len(df_agg)} {tf} candles")
        
        # Expected count
        minutes = int(tf[:-1])
        expected = (24 * 60) // minutes  # 24 hours worth of candles
        print(f"Expected: {expected} candles")
        
        # Show first 5 candle times
        print(f"\nFirst 5 {tf} candle opening times:")
        for i, timestamp in enumerate(df_agg.index[:5]):
            print(f"  {i+1}. {timestamp.strftime('%Y-%m-%d %H:%M')} (minute: {timestamp.minute})")
        
        # Verify alignment
        is_aligned = AlignedCandleAggregator.verify_alignment(df_agg, tf)
        print(f"\nAlignment verification: {'✓ PASSED' if is_aligned else '✗ FAILED'}")
        
        # Verify against reference times
        reference_times = {
            '25m': datetime(2025, 10, 24, 17, 5),
            '40m': datetime(2025, 10, 24, 16, 40),
            '10m': datetime(2025, 10, 24, 17, 10),
            '20m': datetime(2025, 10, 24, 17, 20),
        }
        
        if tf in reference_times:
            ref_time = reference_times[tf]
            if ref_time in df_agg.index:
                print(f"✓ Reference time {ref_time.strftime('%H:%M')} found in aggregated candles")
            else:
                # Find nearest candle
                nearest_idx = df_agg.index.get_indexer([ref_time], method='nearest')[0]
                nearest = df_agg.index[nearest_idx]
                print(f"✗ Reference time {ref_time.strftime('%H:%M')} NOT found")
                print(f"  Nearest candle: {nearest.strftime('%H:%M')}")
    
    print(f"\n{'=' * 80}")
    print("✅ All tests completed!")
    print('=' * 80)
