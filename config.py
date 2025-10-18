"""
Configuration module - loads all settings from environment variables
"""
import os
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()

# Binance Configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET = os.getenv('BINANCE_SECRET', '')

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8452540404:AAHbUhJEHUa0GPvexznJBYdTP3qyIBZeBAU')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '6465176588')

# Trading Configuration
SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')  # Single symbol mode (legacy)
SYMBOLS = os.getenv('SYMBOLS', '')  # Multi-symbol mode: 'BTCUSDT,ETHUSDT,BNBUSDT' or 'ALL' for all coins
TIMEFRAMES = os.getenv('TIMEFRAMES', '5m,15m,30m').split(',')

# Multi-coin Configuration
FETCH_ALL_COINS = os.getenv('FETCH_ALL_COINS', '1') == '1'  # Set to 1 to fetch all Binance coins
MIN_VOLUME_24H = float(os.getenv('MIN_VOLUME_24H', '1000000'))  # Minimum 24h volume in USDT
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
ALLOW_PL1 = bool(int(os.getenv('ALLOW_PL1', '1')))
ALLOW_PL2 = bool(int(os.getenv('ALLOW_PL2', '1')))
ALLOW_PL3 = bool(int(os.getenv('ALLOW_PL3', '1')))

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
