"""
Timeframe Adapter - Middleware layer for automatic candle aggregation
Wraps BinanceFetcher to support non-native timeframes (10m, 20m, 40m, 50m)
through automatic aggregation from 5m base candles
"""
import pandas as pd
import logging
from typing import Optional

from data.binance_fetcher import BinanceFetcher
from data.candle_aggregator import CandleAggregator
from data.aligned_candle_aggregator import AlignedCandleAggregator

logger = logging.getLogger(__name__)


class TimeframeAdapter:
    """
    Adapter pattern - Transparent wrapper around BinanceFetcher
    
    Automatically aggregates candles for non-native timeframes:
    - Native timeframes (5m, 15m, 30m, 1h, etc.) → passthrough to Binance
    - Custom timeframes (10m, 20m, 40m, 50m) → fetch 5m and aggregate
    
    Interface is identical to BinanceFetcher, so it's a drop-in replacement.
    """
    
    # Mapping: Custom timeframe → (base_timeframe, multiplier)
    # These timeframes will be aggregated from base_timeframe
    AGGREGATION_MAP = {
        '10m': ('5m', 2),   # 10m = 2 × 5m
        '20m': ('5m', 4),   # 20m = 4 × 5m
        '25m': ('5m', 5),   # 25m = 5 × 5m
        '40m': ('5m', 8),   # 40m = 8 × 5m
        '45m': ('5m', 9),   # 45m = 9 × 5m
        '50m': ('5m', 10),  # 50m = 10 × 5m
    }
    
    def __init__(self, binance_fetcher: BinanceFetcher):
        """
        Initialize adapter with a BinanceFetcher instance
        
        Args:
            binance_fetcher: BinanceFetcher instance to wrap
        """
        self.fetcher = binance_fetcher
        self.aggregator = CandleAggregator()  # Legacy aggregator (for fallback)
        self.aligned_aggregator = AlignedCandleAggregator()  # New aligned aggregator
        
        logger.info(f"[TimeframeAdapter] Initialized with support for: {', '.join(self.AGGREGATION_MAP.keys())}")
    
    async def initialize(self):
        """Initialize the underlying fetcher - passthrough method"""
        await self.fetcher.initialize()
    
    async def close(self):
        """Close the underlying fetcher - passthrough method"""
        await self.fetcher.close()
    
    async def get_all_usdt_pairs(self, min_volume_24h: float = 100000, quote: str = 'USDT', 
                                max_pairs: int = 100) -> list:
        """Get all trading pairs - passthrough method"""
        return await self.fetcher.get_all_usdt_pairs(min_volume_24h, quote, max_pairs)
    
    async def fetch_historical(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """
        Fetch historical OHLCV data with automatic aggregation for custom timeframes
        
        CRITICAL: For aggregated timeframes, fetches MORE base candles to ensure
        we get the requested number of aggregated candles after aggregation.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '5m', '10m', '20m')
            limit: Number of candles to return
        
        Returns:
            DataFrame with CLOSED candles only (OHLCV format)
        
        Example:
            # Request 50 10m candles
            df = await adapter.fetch_historical("BTCUSDT", "10m", limit=50)
            
            # Internally:
            # 1. Detects "10m" needs aggregation (2 × 5m)
            # 2. Fetches 100 5m candles (50 × 2) from Binance
            # 3. Aggregates 100 5m candles → 50 10m candles
            # 4. Returns 50 10m CLOSED candles
        """
        if timeframe in self.AGGREGATION_MAP:
            # Custom timeframe - needs aggregation
            base_tf, multiplier = self.AGGREGATION_MAP[timeframe]
            
            # ⚠️ CRITICAL: Fetch MORE base candles to account for aggregation
            # To get N aggregated candles, we need N × multiplier base candles
            base_limit = limit * multiplier
            
            logger.info(f"[TimeframeAdapter] {symbol} {timeframe}: Fetching {base_limit} {base_tf} candles (×{multiplier}) to produce {limit} aggregated candles")
            
            # Fetch base timeframe data
            df_base = await self.fetcher.fetch_historical(symbol, base_tf, base_limit)
            
            if len(df_base) == 0:
                logger.warning(f"[TimeframeAdapter] No base data received for {symbol} {base_tf}")
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            # Calculate target minutes for aggregation
            base_minutes = self._timeframe_to_minutes(base_tf)
            target_minutes = base_minutes * multiplier
            
            logger.debug(f"[TimeframeAdapter] Aggregating {len(df_base)} {base_tf} candles → {timeframe} ({target_minutes} minutes)")
            
            # Use AlignedCandleAggregator for accurate alignment
            df_aggregated = AlignedCandleAggregator.aggregate(
                df=df_base,
                target_timeframe=timeframe,
                base_minutes=base_minutes
            )
            
            # Verify alignment
            is_aligned = AlignedCandleAggregator.verify_alignment(
                df=df_aggregated,
                target_timeframe=timeframe
            )
            
            if not is_aligned:
                logger.error(f"[TimeframeAdapter] Alignment verification FAILED for {symbol} {timeframe}")
            
            # Ensure we don't return more than requested limit
            if len(df_aggregated) > limit:
                df_aggregated = df_aggregated.tail(limit)
                logger.debug(f"[TimeframeAdapter] Trimmed to {limit} candles (had {len(df_aggregated)})")
            
            logger.info(f"[TimeframeAdapter] ✓ {symbol} {timeframe}: Aggregated {len(df_base)} {base_tf} → {len(df_aggregated)} {timeframe} candles")
            
            return df_aggregated
        
        else:
            # Native timeframe - passthrough directly to Binance
            logger.debug(f"[TimeframeAdapter] {symbol} {timeframe}: Native timeframe, passthrough to Binance")
            return await self.fetcher.fetch_historical(symbol, timeframe, limit)
    
    @staticmethod
    def _timeframe_to_minutes(timeframe: str) -> int:
        """
        Convert timeframe string to minutes
        
        Args:
            timeframe: Timeframe string (e.g., '5m', '1h')
        
        Returns:
            Number of minutes
        """
        mapping = {
            '1m': 1, '3m': 3, '5m': 5, '10m': 10, '15m': 15, '20m': 20, '25m': 25, '30m': 30, '40m': 40, '45m': 45, '50m': 50,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720,
            '1d': 1440, '1w': 10080, '1M': 43200
        }
        return mapping.get(timeframe, 60)
    
    @staticmethod
    def convert_tf_to_tradingview(timeframe: str) -> str:
        """
        Convert timeframe to TradingView interval format
        Supports both native and custom timeframes
        
        Args:
            timeframe: Timeframe string (e.g., '5m', '10m', '1h')
        
        Returns:
            TradingView format (e.g., '5', '10', '60')
        """
        # For custom minute-based timeframes, just extract the number
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            if minutes < 60:
                return str(minutes)
            else:
                # Convert to hours if >= 60 minutes
                return str(minutes)
        
        # Use standard mapping for other formats
        mapping = {
            '1h': '60',
            '2h': '120',
            '4h': '240',
            '12h': '720',
            '1d': 'D',
            '1w': 'W',
            '1M': 'M'
        }
        
        return mapping.get(timeframe, timeframe.upper().replace('M', ''))
    
    @staticmethod
    def is_aggregated_timeframe(timeframe: str) -> bool:
        """
        Check if a timeframe requires aggregation
        
        Args:
            timeframe: Timeframe string
        
        Returns:
            True if timeframe needs aggregation, False if native
        """
        return timeframe in TimeframeAdapter.AGGREGATION_MAP
    
    @staticmethod
    def get_base_timeframe(timeframe: str) -> str:
        """
        Get base timeframe for aggregation
        
        Args:
            timeframe: Target timeframe
        
        Returns:
            Base timeframe to fetch (e.g., '5m' for '10m')
            Returns same timeframe if native
        """
        if timeframe in TimeframeAdapter.AGGREGATION_MAP:
            return TimeframeAdapter.AGGREGATION_MAP[timeframe][0]
        return timeframe
    
    @staticmethod
    def get_multiplier(timeframe: str) -> int:
        """
        Get aggregation multiplier for a timeframe
        
        Args:
            timeframe: Target timeframe
        
        Returns:
            Multiplier (e.g., 2 for '10m', 1 for native timeframes)
        """
        if timeframe in TimeframeAdapter.AGGREGATION_MAP:
            return TimeframeAdapter.AGGREGATION_MAP[timeframe][1]
        return 1


# Example usage and testing
if __name__ == '__main__':
    import asyncio
    
    logging.basicConfig(level=logging.DEBUG)
    
    async def test_adapter():
        """Test the TimeframeAdapter"""
        
        # Initialize fetcher
        fetcher = BinanceFetcher()
        await fetcher.initialize()
        
        # Wrap with adapter
        adapter = TimeframeAdapter(fetcher)
        
        symbol = 'BTCUSDT'
        
        # Test native timeframe (passthrough)
        print("\n=== Test 1: Native timeframe (5m) ===")
        df_5m = await adapter.fetch_historical(symbol, '5m', limit=50)
        print(f"Received {len(df_5m)} 5m candles")
        print(df_5m.head())
        
        # Test aggregated timeframe (10m)
        print("\n=== Test 2: Aggregated timeframe (10m) ===")
        df_10m = await adapter.fetch_historical(symbol, '10m', limit=50)
        print(f"Received {len(df_10m)} 10m candles")
        print(df_10m.head())
        
        # Test aggregated timeframe (20m)
        print("\n=== Test 3: Aggregated timeframe (20m) ===")
        df_20m = await adapter.fetch_historical(symbol, '20m', limit=25)
        print(f"Received {len(df_20m)} 20m candles")
        print(df_20m.head())
        
        # Test helper methods
        print("\n=== Test 4: Helper methods ===")
        print(f"Is '10m' aggregated? {adapter.is_aggregated_timeframe('10m')}")
        print(f"Is '5m' aggregated? {adapter.is_aggregated_timeframe('5m')}")
        print(f"Base for '10m': {adapter.get_base_timeframe('10m')}")
        print(f"Multiplier for '20m': {adapter.get_multiplier('20m')}")
        print(f"TradingView format for '10m': {adapter.convert_tf_to_tradingview('10m')}")
        
        # Close
        await adapter.close()
        print("\n✅ All tests completed!")
    
    # Run test
    # asyncio.run(test_adapter())
    print("TimeframeAdapter module loaded successfully")
    print(f"Supported aggregated timeframes: {', '.join(TimeframeAdapter.AGGREGATION_MAP.keys())}")
