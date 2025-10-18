# API Documentation

## Table of Contents

- [ChochDetector API](#chochdetector-api)
- [BinanceFetcher API](#binancefetcher-api)
- [TelegramSender API](#telegramsender-api)
- [Web SocketIO Events](#web-socketio-events)

---

## ChochDetector API

### Class: `ChochDetector`

Main detector for CHoCH signals with multi-timeframe support.

#### Constructor

```python
ChochDetector(
    left: int = 1,
    right: int = 1,
    keep_pivots: int = 200,
    use_variant_filter: bool = True,
    allow_ph1: bool = True,
    allow_ph2: bool = True,
    allow_ph3: bool = True,
    allow_pl1: bool = True,
    allow_pl2: bool = True,
    allow_pl3: bool = True
)
```

**Parameters:**
- `left`: Number of bars to the left of pivot
- `right`: Number of bars to the right of pivot
- `keep_pivots`: Maximum number of pivots to store per timeframe
- `use_variant_filter`: Enable variant classification filtering
- `allow_ph1/ph2/ph3`: Enable specific Pivot High variants
- `allow_pl1/pl2/pl3`: Enable specific Pivot Low variants

#### Methods

##### `process_new_bar(timeframe: str, df: pd.DataFrame) -> Dict`

Process a new bar and detect CHoCH signals.

**Parameters:**
- `timeframe`: Timeframe identifier (e.g., '5m')
- `df`: DataFrame with OHLCV data, columns=['open', 'high', 'low', 'close', 'volume']

**Returns:**
```python
{
    'choch_up': bool,           # CHoCH Up detected
    'choch_down': bool,         # CHoCH Down detected
    'signal_type': str | None,  # 'CHoCH Up' or 'CHoCH Down'
    'direction': str | None,    # 'Long' or 'Short'
    'price': float | None,      # Signal price
    'timestamp': pd.Timestamp | None
}
```

**Example:**
```python
detector = ChochDetector(left=1, right=1)
df = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})
df.index = pd.DatetimeIndex([...])

result = detector.process_new_bar('5m', df)
if result['choch_up']:
    print(f"CHoCH Up detected at {result['price']}")
```

##### `detect_pivots(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]`

Detect pivot points in the dataframe.

**Returns:**
- Tuple of (pivot_high_series, pivot_low_series)

##### `classify_variant(df: pd.DataFrame, pivot_idx: int, is_high: bool) -> str`

Classify pivot variant type.

**Returns:**
- Variant string: 'PH1', 'PH2', 'PH3', 'PL1', 'PL2', 'PL3', or 'NA'

---

## BinanceFetcher API

### Class: `BinanceFetcher`

Async Binance data fetcher with multi-timeframe support.

#### Constructor

```python
BinanceFetcher(
    api_key: str = '',
    secret: str = '',
    testnet: bool = False
)
```

**Parameters:**
- `api_key`: Binance API key (optional for public data)
- `secret`: Binance API secret
- `testnet`: Use testnet instead of production

#### Methods

##### `async initialize()`

Initialize exchange connection.

**Example:**
```python
fetcher = BinanceFetcher(api_key='...', secret='...')
await fetcher.initialize()
```

##### `async fetch_historical(symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame`

Fetch historical OHLCV data.

**Parameters:**
- `symbol`: Trading pair (e.g., 'BTC/USDT')
- `timeframe`: Timeframe (e.g., '5m', '1h')
- `limit`: Number of candles to fetch

**Returns:**
- DataFrame with columns: ['open', 'high', 'low', 'close', 'volume']
- Index: DatetimeIndex

**Example:**
```python
df = await fetcher.fetch_historical('BTC/USDT', '5m', limit=100)
print(df.tail())
```

##### `async start_watching(symbol: str, timeframes: List[str], callback: callable, limit: int = 500) -> List[asyncio.Task]`

Start watching multiple timeframes concurrently.

**Parameters:**
- `symbol`: Trading pair
- `timeframes`: List of timeframes
- `callback`: Async callback function with signature:
  ```python
  async def callback(timeframe: str, df: pd.DataFrame, is_new_bar: bool)
  ```
- `limit`: Max bars to keep per timeframe

**Returns:**
- List of asyncio tasks

**Example:**
```python
async def on_data(tf, df, is_new):
    if is_new:
        print(f"[{tf}] New bar: {df.index[-1]}")

tasks = await fetcher.start_watching(
    symbol='BTC/USDT',
    timeframes=['5m', '15m'],
    callback=on_data
)
await asyncio.gather(*tasks)
```

##### `get_dataframe(timeframe: str) -> Optional[pd.DataFrame]`

Get current dataframe for a timeframe.

##### `stop_watching(timeframe: Optional[str] = None)`

Stop watching specific or all timeframes.

##### `async close()`

Close exchange connection.

---

## TelegramSender API

### Class: `TelegramSender`

Send alerts to Telegram.

#### Constructor

```python
TelegramSender(
    bot_token: str,
    chat_id: str
)
```

**Parameters:**
- `bot_token`: Telegram Bot API token
- `chat_id`: Telegram chat ID

#### Methods

##### `send_alert(alert_data: Dict) -> bool`

Send alert to Telegram.

**Parameters:**
- `alert_data`: Dictionary with keys:
  ```python
  {
      'time_date': str,      # '2025-10-18 14:30:00'
      'mã': str,             # 'BTCUSDT'
      'khung': str,          # '5m'
      'hướng': str,          # 'Long' or 'Short'
      'loại': str,           # 'CHoCH Up' or 'CHoCH Down'
      'price': float,        # 67432.50
      'link': str            # TradingView URL
  }
  ```

**Returns:**
- `True` if sent successfully, `False` otherwise

**Example:**
```python
sender = TelegramSender(bot_token='...', chat_id='...')

alert = {
    'time_date': '2025-10-18 14:30:00',
    'mã': 'BTCUSDT',
    'khung': '5m',
    'hướng': 'Long',
    'loại': 'CHoCH Up',
    'price': 67432.50,
    'link': 'https://...'
}

success = sender.send_alert(alert)
```

##### `test_connection() -> bool`

Test Telegram bot connection.

**Returns:**
- `True` if connection successful

### Helper Functions

##### `create_alert_data(symbol: str, timeframe: str, signal_type: str, direction: str, price: float, timestamp: datetime) -> Dict`

Create alert data dictionary.

**Example:**
```python
from datetime import datetime
from alert.telegram_sender import create_alert_data

alert = create_alert_data(
    symbol='BTC/USDT',
    timeframe='5m',
    signal_type='CHoCH Up',
    direction='Long',
    price=67432.50,
    timestamp=datetime.now()
)
```

---

## Web SocketIO Events

### Server Events (Emit)

#### `alert`

Broadcasted when new CHoCH signal is detected.

**Data:**
```javascript
{
    time_date: "2025-10-18 14:30:00",
    mã: "BTCUSDT",
    khung: "5m",
    hướng: "Long",
    loại: "CHoCH Up",
    price: 67432.50,
    link: "https://www.tradingview.com/chart/..."
}
```

**Client listener:**
```javascript
socket.on('alert', (data) => {
    console.log('New alert:', data);
    // Update UI
});
```

#### `alerts_history`

Sent to client on connection with recent alerts.

**Data:**
```javascript
[
    {
        time_date: "...",
        mã: "...",
        // ... same structure as 'alert'
    },
    // ... more alerts
]
```

**Client listener:**
```javascript
socket.on('alerts_history', (alerts) => {
    alerts.forEach(alert => {
        // Populate table
    });
});
```

### Client Events (Listen)

#### `connect`

Client connected to server.

**Server handler:**
```python
@socketio.on('connect')
def handle_connect():
    emit('alerts_history', alerts_history)
```

#### `disconnect`

Client disconnected.

#### `request_history`

Request alert history.

**Client emit:**
```javascript
socket.emit('request_history');
```

### REST Endpoints

#### `GET /`

Serve the main dashboard page.

**Response:**
- HTML page

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
    "status": "ok",
    "alerts_count": 42
}
```

---

## Configuration API

### Environment Variables

All configuration is via environment variables or `.env` file.

```python
import config

# Access configuration
symbol = config.SYMBOL              # str: 'BTCUSDT'
timeframes = config.TIMEFRAMES      # List[str]: ['5m', '15m', ...]
pivot_left = config.PIVOT_LEFT      # int: 1
use_variant = config.USE_VARIANT_FILTER  # bool: True

# Validate configuration
config.validate_config()  # Raises ValueError if invalid
```

### Available Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SYMBOL` | str | 'BTCUSDT' | Trading symbol |
| `TIMEFRAMES` | str | '5m,15m,30m,1h' | Comma-separated timeframes |
| `PIVOT_LEFT` | int | 1 | Pivot left bars |
| `PIVOT_RIGHT` | int | 1 | Pivot right bars |
| `KEEP_PIVOTS` | int | 200 | Max pivots to store |
| `USE_VARIANT_FILTER` | bool | True | Enable variant filtering |
| `ALLOW_PH1/2/3` | bool | True | Enable PH variants |
| `ALLOW_PL1/2/3` | bool | True | Enable PL variants |
| `TELEGRAM_BOT_TOKEN` | str | Required | Bot token |
| `TELEGRAM_CHAT_ID` | str | Required | Chat ID |
| `BINANCE_API_KEY` | str | Optional | API key |
| `BINANCE_SECRET` | str | Optional | API secret |
| `FLASK_HOST` | str | '0.0.0.0' | Flask host |
| `FLASK_PORT` | int | 5000 | Flask port |
| `HISTORICAL_LIMIT` | int | 500 | Historical bars |
| `UPDATE_INTERVAL` | int | 60 | Polling interval (seconds) |

---

## Usage Examples

### Complete Example

```python
import asyncio
import pandas as pd
from data.binance_fetcher import BinanceFetcher
from detectors.choch_detector import ChochDetector
from alert.telegram_sender import TelegramSender, create_alert_data

async def main():
    # Initialize components
    fetcher = BinanceFetcher()
    detector = ChochDetector(left=1, right=1)
    telegram = TelegramSender(bot_token='...', chat_id='...')
    
    await fetcher.initialize()
    
    # Callback for new data
    async def on_new_data(tf, df, is_new_bar):
        if is_new_bar:
            result = detector.process_new_bar(tf, df)
            
            if result['choch_up'] or result['choch_down']:
                alert = create_alert_data(
                    symbol='BTC/USDT',
                    timeframe=tf,
                    signal_type=result['signal_type'],
                    direction=result['direction'],
                    price=result['price'],
                    timestamp=result['timestamp']
                )
                telegram.send_alert(alert)
    
    # Start watching
    tasks = await fetcher.start_watching(
        symbol='BTC/USDT',
        timeframes=['5m', '15m'],
        callback=on_new_data
    )
    
    await asyncio.gather(*tasks)

asyncio.run(main())
```

### Testing Example

```python
import pytest
from detectors.choch_detector import ChochDetector

def test_choch_detection():
    detector = ChochDetector()
    
    # Create test data
    df = create_test_dataframe()
    
    # Process
    result = detector.process_new_bar('5m', df)
    
    # Assert
    assert 'choch_up' in result
    assert 'choch_down' in result
```

---

## Error Handling

### Common Exceptions

```python
# Configuration errors
try:
    config.validate_config()
except ValueError as e:
    print(f"Config error: {e}")

# CCXT errors
try:
    await fetcher.fetch_historical('BTC/USDT', '5m')
except ccxt.NetworkError as e:
    print(f"Network error: {e}")
except ccxt.ExchangeError as e:
    print(f"Exchange error: {e}")

# Telegram errors
try:
    telegram.send_alert(alert_data)
except requests.RequestException as e:
    print(f"Request error: {e}")
```

---

## Performance Tips

1. **Use WebSocket when available** (faster than polling)
2. **Limit timeframes** (fewer = better performance)
3. **Adjust KEEP_PIVOTS** (lower = less memory)
4. **Increase UPDATE_INTERVAL** if polling (reduce CPU)
5. **Use API keys** for higher rate limits

---

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check State

```python
# Check detector state
state = detector.get_state('5m')
print(f"Pivots: {state.pivot_count()}")
print(f"Last six up: {state.last_six_up}")
print(f"CHoCH locked: {state.choch_locked}")

# Check dataframe
df = fetcher.get_dataframe('5m')
print(df.tail())
```

---

## Support

For issues or questions:
1. Check this documentation
2. Review [README.md](README.md)
3. Check [SETUP_GUIDE.md](SETUP_GUIDE.md)
4. Open an issue on GitHub

---

**Last Updated:** October 18, 2025  
**Version:** 1.0.0
