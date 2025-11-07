"""
TradingView URL helper utilities
"""
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)


def get_tradingview_symbol(symbol: str, is_futures: bool = True) -> str:
    """
    Convert Binance symbol to TradingView format
    
    Args:
        symbol: Binance symbol (e.g., 'BTCUSDT', 'ETHUSDT')
        is_futures: If True, adds .P suffix for futures
    
    Returns:
        TradingView symbol (e.g., 'BINANCE:BTCUSDT.P', 'BINANCE:ETHUSDT.P')
    """
    exchange = "BINANCE"
    if is_futures:
        # Futures symbol with .P suffix
        tv_symbol = f"{exchange}:{symbol}.P"
    else:
        # Spot symbol
        tv_symbol = f"{exchange}:{symbol}"
    
    return tv_symbol


def get_tradingview_interval(timeframe: str) -> str:
    """
    Convert Binance timeframe to TradingView interval
    
    Args:
        timeframe: Binance timeframe (e.g., '1m', '5m', '10m', '15m', '1h', '4h', '1d')
    
    Returns:
        TradingView interval (e.g., '1', '5', '10', '15', '60', '240', 'D')
    """
    mapping = {
        '1m': '1',
        '3m': '3',
        '5m': '5',
        '10m': '10',     # Aggregated timeframe
        '15m': '15',
        '20m': '20',     # Aggregated timeframe
        '25m': '25',     # Aggregated timeframe
        '30m': '30',
        '40m': '40',     # Aggregated timeframe
        '45m': '45',     # Aggregated timeframe
        '50m': '50',     # Aggregated timeframe
        '1h': '60',
        '2h': '120',
        '4h': '240',
        '6h': '360',
        '8h': '480',
        '12h': '720',
        '1d': 'D',
        '3d': '3D',
        '1w': 'W',
        '1M': 'M'
    }
    
    return mapping.get(timeframe, timeframe)


def generate_tradingview_link(
    symbol: str,
    timeframe: str,
    is_futures: bool = True,
    region: str = 'in',  # 'in', 'us', 'uk', 'vn', etc.
) -> str:
    """
    Generate TradingView chart link for a symbol and timeframe
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Timeframe (e.g., '5m', '1h', '4h')
        is_futures: If True, generates futures link with .P suffix
        region: TradingView region (default: 'in' for India)
    
    Returns:
        Full TradingView URL
        Example: https://in.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT.P&interval=5
    """
    tv_symbol = get_tradingview_symbol(symbol, is_futures)
    tv_interval = get_tradingview_interval(timeframe)
    
    # URL encode the symbol (: becomes %3A)
    encoded_symbol = quote(tv_symbol, safe='')
    
    # Build URL
    url = f"https://{region}.tradingview.com/chart/?symbol={encoded_symbol}&interval={tv_interval}"
    
    return url


def add_tradingview_link_to_alert(alert_data: dict, is_futures: bool = True, region: str = 'in') -> dict:
    """
    Add TradingView link to alert data
    
    Args:
        alert_data: Alert data dictionary
        is_futures: If True, generates futures link
        region: TradingView region
    
    Returns:
        Alert data with tradingview_link added
    """
    try:
        symbol = alert_data.get('symbol', '')
        timeframe = alert_data.get('khung', '')  # Vietnamese for 'timeframe'
        
        if symbol and timeframe:
            tv_link = generate_tradingview_link(
                symbol=symbol,
                timeframe=timeframe,
                is_futures=is_futures,
                region=region
            )
            alert_data['tradingview_link'] = tv_link
            logger.debug(f"Generated TradingView link: {tv_link}")
        
        return alert_data
    
    except Exception as e:
        logger.error(f"Error generating TradingView link: {e}")
        return alert_data


# Test the helper
if __name__ == '__main__':
    # Test examples
    test_cases = [
        ('BTCUSDT', '5m'),
        ('ETHUSDT', '10m'),   # Aggregated timeframe
        ('BNBUSDT', '15m'),
        ('XRPUSDT', '20m'),   # Aggregated timeframe
        ('AVNTUSDT', '30m'),
        ('SOLUSDT', '1h'),
        ('ADAUSDT', '4h'),
    ]
    
    print("=" * 80)
    print("TradingView Link Generator Test")
    print("=" * 80)
    
    for symbol, timeframe in test_cases:
        link = generate_tradingview_link(symbol, timeframe, is_futures=True, region='in')
        print(f"{symbol:12} | {timeframe:5} | {link}")
    
    print("\n" + "=" * 80)
