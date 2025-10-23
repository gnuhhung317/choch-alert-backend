"""
Candle Aggregator - Pure logic for aggregating smaller timeframe candles into larger ones
Gộp nến từ timeframe nhỏ (5m) thành timeframe lớn hơn (10m, 20m, 40m, 50m)
"""
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CandleAggregator:
    """
    Pure logic class for candle aggregation.
    Independent of data source (Binance, etc.)
    """
    
    @staticmethod
    def aggregate(df: pd.DataFrame, target_minutes: int, base_minutes: int = 5) -> pd.DataFrame:
        """
        Aggregate smaller timeframe candles into larger timeframe
        
        CRITICAL: Only returns COMPLETE aggregated candles (closed candles only)
        
        Args:
            df: DataFrame with OHLCV data and datetime index (base timeframe, e.g., 5m)
            target_minutes: Target timeframe in minutes (10, 20, 40, 50)
            base_minutes: Base timeframe in minutes (default: 5)
        
        Returns:
            DataFrame with aggregated candles (OHLCV format)
            Only complete candles are returned (incomplete periods are excluded)
        
        Example:
            # Aggregate 100 5m candles → 50 10m candles
            df_5m = fetch_5m_candles(limit=100)  # 100 closed 5m candles
            df_10m = CandleAggregator.aggregate(df_5m, target_minutes=10, base_minutes=5)
            # Result: 50 closed 10m candles (each from 2 × 5m candles)
        """
        if df is None or len(df) == 0:
            logger.warning("[Aggregator] Empty DataFrame provided")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        if target_minutes % base_minutes != 0:
            raise ValueError(f"target_minutes ({target_minutes}) must be divisible by base_minutes ({base_minutes})")
        
        multiplier = target_minutes // base_minutes
        logger.debug(f"[Aggregator] Aggregating {len(df)} {base_minutes}m candles → {target_minutes}m (multiplier={multiplier})")
        
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        
        # Resample to target timeframe
        # Rule: target_minutes in minutes format (e.g., '10min' for 10 minutes)
        rule = f'{target_minutes}min'  # Use 'min' instead of deprecated 'T'
        
        # Aggregation rules for OHLCV
        agg_dict = {
            'open': 'first',    # First open in the period
            'high': 'max',      # Highest high in the period
            'low': 'min',       # Lowest low in the period
            'close': 'last',    # Last close in the period
            'volume': 'sum'     # Total volume in the period
        }
        
        # Resample with label='left' to use the start time of each period
        # closed='left' means the interval is [start, end)
        df_resampled = df.resample(rule, label='left', closed='left').agg(agg_dict)
        
        # ⚠️ CRITICAL: Remove incomplete candles (NaN values)
        # This happens when the last period doesn't have enough base candles
        df_complete = df_resampled.dropna()
        
        # Additional validation: Ensure each aggregated candle has correct number of base candles
        # Count how many base candles contributed to each aggregated candle
        candle_counts = df.resample(rule, label='left', closed='left').size()
        
        # Only keep aggregated candles that have the full multiplier count
        # This ensures we only return COMPLETE candles
        complete_mask = candle_counts == multiplier
        df_validated = df_resampled[complete_mask]
        
        logger.info(f"[Aggregator] ✓ Aggregated {len(df)} {base_minutes}m → {len(df_validated)} {target_minutes}m candles (complete only)")
        
        if len(df_validated) != len(df_complete):
            logger.debug(f"[Aggregator] Filtered out {len(df_complete) - len(df_validated)} incomplete candles")
        
        return df_validated
    
    @staticmethod
    def calculate_required_base_candles(target_candles: int, target_minutes: int, base_minutes: int = 5) -> int:
        """
        Calculate how many base candles are needed to produce target number of aggregated candles
        
        Args:
            target_candles: Desired number of aggregated candles
            target_minutes: Target timeframe in minutes
            base_minutes: Base timeframe in minutes (default: 5)
        
        Returns:
            Number of base candles to fetch
        
        Example:
            # Want 50 10m candles → need 100 5m candles (50 × 2)
            required = calculate_required_base_candles(50, 10, 5)  # returns 100
        """
        if target_minutes % base_minutes != 0:
            raise ValueError(f"target_minutes ({target_minutes}) must be divisible by base_minutes ({base_minutes})")
        
        multiplier = target_minutes // base_minutes
        required = target_candles * multiplier
        
        logger.debug(f"[Aggregator] To get {target_candles} {target_minutes}m candles, need {required} {base_minutes}m candles (×{multiplier})")
        
        return required
    
    @staticmethod
    def validate_aggregation(df_base: pd.DataFrame, df_aggregated: pd.DataFrame, 
                           target_minutes: int, base_minutes: int = 5) -> bool:
        """
        Validate that aggregation was done correctly
        
        Args:
            df_base: Original base timeframe DataFrame
            df_aggregated: Aggregated DataFrame
            target_minutes: Target timeframe in minutes
            base_minutes: Base timeframe in minutes
        
        Returns:
            True if validation passes, False otherwise
        """
        if len(df_base) == 0 or len(df_aggregated) == 0:
            return True  # Empty is valid
        
        multiplier = target_minutes // base_minutes
        expected_max_candles = len(df_base) // multiplier
        
        if len(df_aggregated) > expected_max_candles:
            logger.error(f"[Aggregator] Validation FAILED: Got {len(df_aggregated)} candles, expected max {expected_max_candles}")
            return False
        
        # Check that all aggregated candles have valid OHLCV
        if df_aggregated[['open', 'high', 'low', 'close', 'volume']].isna().any().any():
            logger.error("[Aggregator] Validation FAILED: Found NaN values in aggregated candles")
            return False
        
        # Check OHLC relationship: low <= open,close <= high
        for idx, row in df_aggregated.iterrows():
            if not (row['low'] <= row['open'] <= row['high']):
                logger.error(f"[Aggregator] Validation FAILED: Invalid OHLC at {idx}: low={row['low']}, open={row['open']}, high={row['high']}")
                return False
            if not (row['low'] <= row['close'] <= row['high']):
                logger.error(f"[Aggregator] Validation FAILED: Invalid OHLC at {idx}: low={row['low']}, close={row['close']}, high={row['high']}")
                return False
        
        logger.debug(f"[Aggregator] ✓ Validation passed: {len(df_aggregated)} aggregated candles are valid")
        return True


# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    # Create sample 5m data
    import numpy as np
    from datetime import datetime, timedelta
    
    # Generate 100 5m candles (8 hours 20 minutes of data)
    start_time = datetime(2025, 10, 23, 10, 0, 0)
    timestamps = [start_time + timedelta(minutes=5*i) for i in range(100)]
    
    df_5m = pd.DataFrame({
        'open': np.random.uniform(50000, 51000, 100),
        'high': np.random.uniform(50500, 51500, 100),
        'low': np.random.uniform(49500, 50500, 100),
        'close': np.random.uniform(50000, 51000, 100),
        'volume': np.random.uniform(100, 1000, 100)
    }, index=pd.DatetimeIndex(timestamps))
    
    # Fix OHLC relationship
    df_5m['high'] = df_5m[['open', 'high', 'close']].max(axis=1) + 100
    df_5m['low'] = df_5m[['open', 'low', 'close']].min(axis=1) - 100
    
    print(f"Created {len(df_5m)} 5m candles")
    print(f"Time range: {df_5m.index[0]} to {df_5m.index[-1]}")
    
    # Test aggregation
    aggregator = CandleAggregator()
    
    # Test 10m aggregation
    print("\n=== Test 10m aggregation ===")
    df_10m = aggregator.aggregate(df_5m, target_minutes=10, base_minutes=5)
    print(f"Result: {len(df_10m)} 10m candles")
    print(f"Expected: {100 // 2} = 50 candles")
    assert len(df_10m) == 50, "10m aggregation failed"
    
    # Test 20m aggregation
    print("\n=== Test 20m aggregation ===")
    df_20m = aggregator.aggregate(df_5m, target_minutes=20, base_minutes=5)
    print(f"Result: {len(df_20m)} 20m candles")
    print(f"Expected: {100 // 4} = 25 candles")
    assert len(df_20m) == 25, "20m aggregation failed"
    
    # Test 50m aggregation
    print("\n=== Test 50m aggregation ===")
    df_50m = aggregator.aggregate(df_5m, target_minutes=50, base_minutes=5)
    print(f"Result: {len(df_50m)} 50m candles")
    print(f"Expected: {100 // 10} = 10 candles")
    assert len(df_50m) == 10, "50m aggregation failed"
    
    # Test validation
    print("\n=== Test validation ===")
    assert aggregator.validate_aggregation(df_5m, df_10m, 10, 5), "10m validation failed"
    assert aggregator.validate_aggregation(df_5m, df_20m, 20, 5), "20m validation failed"
    assert aggregator.validate_aggregation(df_5m, df_50m, 50, 5), "50m validation failed"
    
    # Test required candles calculation
    print("\n=== Test required candles calculation ===")
    for target_candles in [50, 25, 10]:
        for target_minutes in [10, 20, 50]:
            required = aggregator.calculate_required_base_candles(target_candles, target_minutes, 5)
            print(f"For {target_candles} {target_minutes}m candles, need {required} 5m candles")
    
    print("\n✅ All tests passed!")
