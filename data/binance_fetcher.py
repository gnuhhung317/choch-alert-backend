"""
Binance Data Fetcher - Simple Sequential Fetching for Futures
No WebSocket, no concurrent tasks, just simple loop
"""
import ccxt.async_support as ccxt
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BinanceFetcher:
    """Simple Binance futures data fetcher"""
    
    def __init__(self, api_key: str = '', secret: str = '', testnet: bool = False):
        """
        Initialize Binance fetcher
        
        Args:
            api_key: Binance API key (optional for public data)
            secret: Binance API secret (optional for public data)
            testnet: Use testnet instead of production
        """
        self.api_key = api_key
        self.secret = secret
        self.testnet = testnet
        self.exchange: Optional[ccxt.binance] = None
        
        # Data storage per symbol_timeframe key
        self.dataframes: Dict[str, pd.DataFrame] = {}
    
    async def initialize(self):
        """Initialize exchange connection"""
        config = {
            'enableRateLimit': True,
            'rateLimit': 50,  # 50ms between requests
            'options': {
                'defaultType': 'future',
            }
        }
        
        if self.api_key and self.secret:
            config['apiKey'] = self.api_key
            config['secret'] = self.secret
        
        self.exchange = ccxt.binance(config) #TODO
                # Enable testnet/sandbox mode if requested
        self.exchange.enable_demo_trading(True)
        if self.testnet:
            self.exchange.enable_demo_trading(True)
            logger.info("🧪 Testnet mode enabled for data fetcher")
        
        # Load markets first
        await self.exchange.load_markets()
        

        logger.info(f"Binance Futures exchange initialized (testnet={self.testnet})")
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()
            logger.info("Binance exchange connection closed")
    
    async def get_all_usdt_pairs(self, min_volume_24h: float = 1000000, quote: str = 'USDT', 
                               max_pairs: int = 100) -> List[str]:
        """
        Get all FUTURES trading pairs with specified quote currency and minimum volume
        Always includes BTC, ETH, BNB as fixed coins + random selection of others
        
        Args:
            min_volume_24h: Minimum 24h volume in quote currency
            quote: Quote currency (e.g., 'USDT', 'BUSD')
            max_pairs: Maximum number of pairs to return (0 = unlimited)
        
        Returns:
            List of FUTURES symbol strings (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        if not self.exchange:
            await self.initialize()
        
        # Fixed coins to always monitor
        FIXED_COINS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        try:
            # Fetch all tickers
            tickers = await self.exchange.fetch_tickers()
            
            # Start with fixed coins
            valid_pairs = FIXED_COINS.copy()
            
            # Add other coins (skip if already in fixed list)
            for symbol, ticker in tickers.items():
                # For futures, symbols are like 'BTC/USDT:USDT' (perpetual)
                # Only process futures symbols (with colon)
                if ':' in symbol:
                    # Format: BTC/USDT:USDT (perpetual)
                    base_quote, settle = symbol.split(':')
                    if settle == quote and quote in base_quote:
                        # Check 24h volume
                        volume_24h = ticker.get('quoteVolume', 0)
                        if volume_24h and volume_24h >= min_volume_24h:
                            # Return in format BTCUSDT (without slash)
                            clean_symbol = base_quote.replace('/', '')
                            if clean_symbol not in valid_pairs:  # Skip duplicates
                                valid_pairs.append(clean_symbol)
                # Skip spot symbols (without colon) to ensure futures only
            
            # Shuffle and limit pairs based on max_pairs
            import random
            fixed_count = len(FIXED_COINS)
            others = valid_pairs[fixed_count:]
            random.shuffle(others)
            
            if max_pairs == 0:
                # Return ALL pairs (fixed + all others) - unlimited mode
                final_pairs = valid_pairs[:fixed_count] + others
                logger.info(f"Selected ALL {len(final_pairs)} FUTURES pairs: {fixed_count} fixed + {len(others)} others (UNLIMITED mode)")
            else:
                # Take fixed + random up to max_pairs total
                final_pairs = valid_pairs[:fixed_count] + others[:max_pairs-fixed_count]
                logger.info(f"Selected {len(final_pairs)} FUTURES pairs: {fixed_count} fixed + {len(final_pairs)-fixed_count} others (LIMITED to {max_pairs})")
            
            return final_pairs
        
        except Exception as e:
            logger.error(f"Error fetching trading pairs: {e}")
            return FIXED_COINS  # Return at least fixed coins on error
    
    async def fetch_historical(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """
        Fetch historical OHLCV FUTURES data (CLOSED CANDLES ONLY)
        
        Args:
            symbol: Trading pair in Binance Futures format (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '5m', '1h')
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with CLOSED FUTURES candles only, excluding the currently forming candle
        """
        if not self.exchange:
            await self.initialize()
        
        try:
            # Convert BTCUSDT to BTC/USDT:USDT for CCXT futures
            ccxt_symbol = self._convert_to_ccxt_format(symbol)
            
            # Fetch one extra candle to account for the currently forming candle
            fetch_limit = limit + 1
            ohlcv = await self.exchange.fetch_ohlcv(ccxt_symbol, timeframe, limit=fetch_limit)
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime and set as index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # ⚠️ CRITICAL FIX: Remove the last candle (currently forming/open candle)
            # Only return CLOSED candles to ensure CHoCH confirmation accuracy
            if len(df) > 0:
                df = df.iloc[:-1]  # Remove last candle (open/forming candle)
            
            # Ensure we don't return more than requested limit
            if len(df) > limit:
                df = df.tail(limit)
            
            logger.info(f"Fetched {len(df)} CLOSED bars for {symbol} {timeframe} (excluded open candle)")
            return df
        
        except Exception as e:
            logger.error(f"Error fetching {symbol} {timeframe}: {e}")
            # Return empty DataFrame on error
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
    
    def _convert_to_ccxt_format(self, symbol: str) -> str:
        """
        Convert Binance symbol to CCXT format
        BTCUSDT -> BTC/USDT:USDT
        """
        if '/' in symbol or ':' in symbol:
            return symbol
        
        # Find the quote currency
        for quote in ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB']:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                # Format for futures: BTC/USDT:USDT
                return f"{base}/{quote}:{quote}"
        
        return symbol
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        mapping = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720,
            '1d': 1440, '1w': 10080, '1M': 43200
        }
        return mapping.get(timeframe, 60)
    
    @staticmethod
    def convert_tf_to_tradingview(timeframe: str) -> str:
        """
        Convert CCXT timeframe to TradingView interval format
        
        Args:
            timeframe: CCXT format (e.g., '5m', '1h', '1d')
        
        Returns:
            TradingView format (e.g., '5', '60', 'D')
        """
        mapping = {
            '1m': '1',
            '5m': '5',
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '2h': '120',
            '4h': '240',
            '12h': '720',
            '1d': 'D',
            '1w': 'W',
            '1M': 'M'
        }
        
        return mapping.get(timeframe, timeframe.upper().replace('M', ''))
