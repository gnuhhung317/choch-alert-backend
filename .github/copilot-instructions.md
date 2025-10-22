# CHoCH Alert Backend - AI Coding Instructions

## System Overview
This is a **cryptocurrency trading signal detection system** that identifies CHoCH (Change of Character) patterns using pivot point analysis. The system monitors multiple crypto pairs across different timeframes, detects specific 8-pivot patterns, and sends real-time alerts via Telegram and web dashboard.

## Architecture & Core Components

### Main Application Flow (`main.py`)
- **ChochAlertSystem**: Orchestrates the entire system with two modes:
  - `mode_realtime()`: Continuous monitoring with Telegram alerts
  - `mode_history()`: Historical analysis with chart generation
- **Sequential Processing**: Fetches 50 closed candles → rebuilds pivots → checks CHoCH → sends alerts
- **3-Candle Confirmation Logic**: Pre-CHoCH → CHoCH → Confirmation (all must be closed candles)

### CHoCH Detection Engine (`detectors/choch_detector.py`)
- **8-Pivot Pattern**: Requires alternating high/low structure with specific breakout conditions
- **State Management**: Per-timeframe state tracking with `TimeframeState` class
- **Pivot Classification**: PH1/PH2/PH3 and PL1/PL2/PL3 variants with filtering
- **Key Method**: `rebuild_pivots()` - Always rebuilds from fresh 50-bar window (not incremental)
- **Confirmation Logic**: CHoCH must be confirmed by next candle meeting specific price conditions

### Data Fetching (`data/binance_fetcher.py`)
- **Closed Candles Only**: Excludes open/current candle to prevent false signals
- **Symbol Management**: Dynamic fetching of all USDT pairs, random selection of 100 per scan
- **Rate Limiting**: 50ms between requests with proper ccxt async handling

### Scheduling (`utils/timeframe_scheduler.py`)
- **Candle-Aligned Scanning**: Scans at candle close times (5m at :05, :10, etc.)
- **Multi-Timeframe**: Each timeframe scanned independently based on its interval
- **Prevents Duplicate Scans**: Tracks last scanned close per timeframe

## Configuration Patterns

### Environment-Based Config (`config.py`)
```python
# Key settings that affect behavior:
SYMBOLS = 'ALL'  # or 'BTCUSDT,ETHUSDT' for specific pairs
TIMEFRAMES = '5m,15m,30m,1h'
ENABLE_CHART = '1'  # Enables matplotlib chart generation
CHART_MODE = 'realtime'  # vs 'history' for batch processing
```

### State Management
- **Per-Timeframe States**: Each symbol_timeframe gets independent pivot state
- **State Reset**: `state.reset()` clears all pivots when rebuilding from fresh data
- **CHoCH Locking**: Prevents duplicate signals until pattern resets

## Development Workflows

### Testing CHoCH Logic
```bash
python test_choch_confirmation.py  # Test 3-candle confirmation
python test_confirmation_logic.py  # Test specific scenarios
pytest tests/  # Run full test suite
```

### Running Modes
```bash
# Realtime monitoring (default)
python main.py

# History mode (chart generation only)
CHART_MODE=history python main.py

# Background service
./run_background.sh
```

### Debugging
- **Extensive Logging**: CHoCH detection logs every step with bar details
- **Chart Generation**: Visual debugging via matplotlib charts and Pine Script export
- **Web Dashboard**: Real-time monitoring at `http://localhost:5000`

## Critical Patterns & Conventions

### Data Flow Architecture
1. **Fetch** → 50 closed candles per symbol/timeframe
2. **Rebuild** → Complete pivot state reconstruction (not incremental)
3. **Detect** → 8-pivot pattern validation with breakout conditions
4. **Confirm** → 3-candle confirmation (pre-CHoCH, CHoCH, confirmation)
5. **Alert** → Telegram message + web broadcast + database storage

### CHoCH Validation Logic
```python
# CHoCH Up requires:
choch_up = (prev['low'] > pre_prev['low'] and 
           prev['close'] > pre_prev['high'] and 
           prev['close'] > state.pivot6)

# Confirmation requires:
confirm_up = current['low'] > pre_prev['high']
```

### Database Schema (`database/models.py`)
- **Alert Table**: Stores all signals with symbol, timeframe, direction, price, timestamps
- **SQLAlchemy ORM**: Simple session management with automatic cleanup
- **Web API**: REST endpoints for alert history and statistics

### Pine Script Integration
- **Exact Logic Match**: Python detector replicates Pine Script behavior
- **Variant Classification**: PH1/PH2/PH3 logic matches TradingView exactly
- **Chart Export**: Generates Pine Script code for TradingView validation

## Key Dependencies & Integration Points

### External Services
- **Binance Futures API**: CCXT library for market data
- **Telegram Bot API**: Direct HTTP requests for alerts
- **TradingView**: Chart links with symbol/timeframe routing

### Web Stack
- **Flask + SocketIO**: Real-time web dashboard with WebSocket updates
- **SQLite**: Embedded database for alert storage
- **Matplotlib**: Chart generation for debugging/analysis

## Common Development Tasks

### Adding New Detection Logic
1. Modify `ChochDetector.check_choch()` method
2. Update test cases in `tests/` directory
3. Verify Pine Script equivalence in `source.pine`

### Adding New Timeframes
1. Update `TimeframeScheduler.TF_TO_MINUTES` mapping
2. Test scheduler alignment with `test_scheduler.py`
3. Verify Binance API compatibility

### Debugging False Signals
1. Enable `ENABLE_CHART=1` for visual debugging
2. Check logs for 3-candle confirmation details
3. Compare with Pine Script output using exported scripts

### Deployment Options
- **Docker**: `docker-compose up` for containerized deployment
- **Systemd**: `choch-alert.service` for Linux service management
- **Background Scripts**: Platform-specific `.sh/.bat` files

This system prioritizes accuracy over speed - it rebuilds pivot state from scratch each scan to ensure reliable signals, making it suitable for production trading alerts.