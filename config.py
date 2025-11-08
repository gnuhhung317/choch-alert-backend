"""
Configuration module - loads all settings from environment variables
"""
import os
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()

# Binance Configuration - Realtime Data (for market analysis)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET = os.getenv('BINANCE_SECRET', '')

# Binance Configuration - Demo/Live Trading (for order execution)
# If not set, will fallback to BINANCE_API_KEY/BINANCE_SECRET
BINANCE_API_KEY_DEMO = os.getenv('BINANCE_API_KEY_DEMO', os.getenv('BINANCE_API_KEY', ''))
BINANCE_SECRET_DEMO = os.getenv('BINANCE_SECRET_DEMO', os.getenv('BINANCE_SECRET', ''))

# Trading Bot Configuration
ENABLE_TRADING = bool(int(os.getenv('ENABLE_TRADING', '0')))  # 0 = disabled (simulation), 1 = enabled (real trading)
DEMO_TRADING = bool(int(os.getenv('DEMO_TRADING', '1')))  # 1 = use testnet (default), 0 = live trading
POSITION_SIZE = float(os.getenv('POSITION_SIZE', '100.0'))  # Position size in USDT
LEVERAGE = int(os.getenv('LEVERAGE', '20'))  # Leverage multiplier

# Data Fetcher Configuration
USE_REALTIME_DATA = bool(int(os.getenv('USE_REALTIME_DATA', '1')))  # 1 = use production market data (default), 0 = use testnet data
# NOTE: Even in demo trading mode, we typically want real market data for accurate signals

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8452540404:AAHbUhJEHUa0GPvexznJBYdTP3qyIBZeBAU')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-4848555942')

# Trading Configuration
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')  # Single symbol mode (legacy)
SYMBOLS = os.getenv('SYMBOLS', '')  # Multi-symbol mode: 'BTCUSDT,ETHUSDT,BNBUSDT' or 'ALL' for all coins
TIMEFRAMES = os.getenv('TIMEFRAMES', '10m,20m,40m,25m,45m,15m,30m,1h').split(',')

# Multi-coin Configuration
FETCH_ALL_COINS = os.getenv('FETCH_ALL_COINS', '1') == '1'  # Set to 1 to fetch all Binance coins
MIN_VOLUME_24H = float(os.getenv('MIN_VOLUME_24H', '10000'))  # Minimum 24h volume in USDT
MAX_PAIRS = int(os.getenv('MAX_PAIRS', '0'))  # Maximum number of pairs to monitor (0 = unlimited)
QUOTE_CURRENCY = os.getenv('QUOTE_CURRENCY', 'USDT')  # Filter by quote currency

# Pivot Configuration
PIVOT_LEFT = int(os.getenv('PIVOT_LEFT', '1'))
PIVOT_RIGHT = int(os.getenv('PIVOT_RIGHT', '1'))
KEEP_PIVOTS = int(os.getenv('KEEP_PIVOTS', '500'))

# Variant Filter Configuration
USE_VARIANT_FILTER = bool(int(os.getenv('USE_VARIANT_FILTER', '1')))
ALLOW_PH1 = bool(int(os.getenv('ALLOW_PH1', '1')))
ALLOW_PH2 = bool(int(os.getenv('ALLOW_PH2', '1')))
ALLOW_PH3 = bool(int(os.getenv('ALLOW_PH3', '1')))
ALLOW_PH4 = bool(int(os.getenv('ALLOW_PH4', '1')))
ALLOW_PH5 = bool(int(os.getenv('ALLOW_PH5', '1')))
ALLOW_PL1 = bool(int(os.getenv('ALLOW_PL1', '1')))
ALLOW_PL2 = bool(int(os.getenv('ALLOW_PL2', '1')))
ALLOW_PL3 = bool(int(os.getenv('ALLOW_PL3', '1')))
ALLOW_PL4 = bool(int(os.getenv('ALLOW_PL4', '1')))
ALLOW_PL5 = bool(int(os.getenv('ALLOW_PL5', '1')))

# Flask Configuration
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
FLASK_DEBUG = bool(int(os.getenv('FLASK_DEBUG', '0')))

# Data Fetching Configuration
HISTORICAL_LIMIT = int(os.getenv('HISTORICAL_LIMIT', '500'))
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '60'))  # seconds

# Chart Configuration
ENABLE_CHART = bool(int(os.getenv('ENABLE_CHART', '0')))  # 0 = disabled (default), 1 = enabled
CHART_MODE = os.getenv('CHART_MODE', 'realtime')  # 'history' = vẽ chart toàn bộ lịch sử, 'realtime' = chạy liên tục và gửi alert

# Validation
def validate_config():
    """Validate critical configuration values"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is required")
    
    if not TELEGRAM_CHAT_ID:
        errors.append("TELEGRAM_CHAT_ID is required")
    
    if not FETCH_ALL_COINS and not SYMBOLS and not SYMBOL:
        errors.append("SYMBOL or SYMBOLS or FETCH_ALL_COINS is required")
    
    if not TIMEFRAMES:
        errors.append("At least one TIMEFRAME is required")
    
    if PIVOT_LEFT < 1 or PIVOT_RIGHT < 1:
        errors.append("PIVOT_LEFT and PIVOT_RIGHT must be >= 1")
    
    if ENABLE_CHART and CHART_MODE not in ['history', 'realtime']:
        errors.append("CHART_MODE must be 'history' or 'realtime'")
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"- {e}" for e in errors))

def get_symbols_list():
    """Get list of symbols to monitor"""
    if FETCH_ALL_COINS:
        return 'ALL'
    elif SYMBOLS:
        return [s.strip() for s in SYMBOLS.split(',') if s.strip()]
    else:
        return [SYMBOL]

# Validate on import
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"⚠️  Warning: {e}")
        print("Please check your .env file")
