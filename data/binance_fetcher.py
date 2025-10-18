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
        
        if self.testnet:
            config['options']['defaultType'] = 'future'
            config['urls'] = {
                'api': {
                    'public': 'https://testnet.binancefuture.com',
                    'private': 'https://testnet.binancefuture.com',
                }
            }
        
        self.exchange = ccxt.binance(config)
        await self.exchange.load_markets()
        logger.info(f"Binance Futures exchange initialized (testnet={self.testnet})")
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()
            logger.info("Binance exchange connection closed")
    
    async def get_all_usdt_pairs(self, min_volume_24h: float = 1000000, quote: str = 'USDT') -> List[str]:
        """
        Get all trading pairs with specified quote currency and minimum volume
        
        Args:
            min_volume_24h: Minimum 24h volume in quote currency
            quote: Quote currency (e.g., 'USDT', 'BUSD')
        
        Returns:
            List of symbol strings for futures (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        if not self.exchange:
            await self.initialize()
        
        try:
            # Fetch all tickers
            tickers = await self.exchange.fetch_tickers()
            
            # Filter by quote currency and volume
            valid_pairs = []
            for symbol, ticker in tickers.items():
                # For futures, symbols are like 'BTC/USDT:USDT' (perpetual)
                if ':' in symbol:
                    # Format: BTC/USDT:USDT (perpetual)
                    base_quote, settle = symbol.split(':')
                    if settle == quote and quote in base_quote:
                        # Check 24h volume
                        volume_24h = ticker.get('quoteVolume', 0)
                        if volume_24h and volume_24h >= min_volume_24h:
                            # Return in format BTCUSDT (without slash)
                            clean_symbol = base_quote.replace('/', '')
                            valid_pairs.append(clean_symbol)
                elif '/' in symbol and symbol.endswith(f'/{quote}'):
                    # Spot format: BTC/USDT
                    volume_24h = ticker.get('quoteVolume', 0)
                    if volume_24h and volume_24h >= min_volume_24h:
                        # Convert to BTCUSDT format
                        clean_symbol = symbol.replace('/', '')
                        valid_pairs.append(clean_symbol)
            
            logger.info(f"Found {len(valid_pairs)} futures pairs with {quote} quote and volume >= ${min_volume_24h:,.0f}")
            return sorted(valid_pairs)
        
        except Exception as e:
            logger.error(f"Error fetching trading pairs: {e}")
            return []
    
    async def fetch_historical(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """
        Fetch historical OHLCV data
        
        Args:
            symbol: Trading pair in Binance Futures format (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '5m', '1h')
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if not self.exchange:
            await self.initialize()
        
        try:
            # Convert BTCUSDT to BTC/USDT:USDT for CCXT futures
            ccxt_symbol = self._convert_to_ccxt_format(symbol)
            
            ohlcv = await self.exchange.fetch_ohlcv(ccxt_symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime and set as index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"Fetched {len(df)} bars for {symbol} {timeframe}")
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
