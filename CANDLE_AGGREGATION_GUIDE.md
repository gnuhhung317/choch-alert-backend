# Candle Aggregation Feature - User Guide

## 🎯 Overview

The CHoCH Alert System now supports **aggregated timeframes** (10m, 20m, 40m, 50m) by automatically combining 5m candles. This feature is implemented using a **loose coupling architecture** that doesn't affect existing functionality.

## ✅ What's New

### Supported Aggregated Timeframes

- **10m** - Aggregated from 2 × 5m candles
- **20m** - Aggregated from 4 × 5m candles  
- **40m** - Aggregated from 8 × 5m candles
- **50m** - Aggregated from 10 × 5m candles

### Native Timeframes (unchanged)

- 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d (direct from Binance)

## 📖 Usage

### 1. Configuration

Simply add the new timeframes to your `config.py` or environment variables:

```python
# In config.py or .env
TIMEFRAMES = '5m,10m,15m,20m,30m,1h'
```

### 2. Running the System

No code changes needed! The system automatically detects and aggregates:

```bash
python main.py
```

### 3. Example Output

```
[TimeframeAdapter] BTCUSDT 10m: Fetching 100 5m candles (×2) to produce 50 aggregated candles
[Aggregator] ✓ Aggregated 100 5m → 50 10m candles (complete only)
[TimeframeAdapter] ✓ BTCUSDT 10m: Aggregated 100 5m → 50 10m candles
```

## 🔧 How It Works

### Architecture

```
Application (main.py)
    ↓ fetch_historical("BTCUSDT", "10m", 50)
TimeframeAdapter (middleware)
    ↓ detects "10m" needs aggregation
    ↓ fetches 100 5m candles (50 × 2)
BinanceFetcher → Binance API
    ↓ returns 100 5m candles
CandleAggregator
    ↓ aggregates 100 5m → 50 10m
    ↓ validates and filters incomplete candles
TimeframeAdapter
    ↓ returns 50 complete 10m candles
Application receives data
```

### Key Features

1. **Transparent**: Existing code doesn't know candles are aggregated
2. **Accurate**: Only complete candles are returned (closed candles only)
3. **Validated**: OHLCV relationships are checked
4. **Efficient**: Automatically fetches correct number of base candles

## 📊 Scheduler Integration

The scheduler automatically handles aggregated timeframes:

### 10m Schedule

- Candles close at: **:00, :10, :20, :30, :40, :50**
- Scanner runs 30s after close: **:00:30, :10:30, :20:30, ...**

### 20m Schedule

- Candles close at: **:00, :20, :40**
- Scanner runs 30s after close: **:00:30, :20:30, :40:30**

### 50m Schedule

- Candles close every 50 minutes
- Scanner runs 30s after each close

### Example Scheduler Output

```
[Scheduler Status - Candle Close Times]
  5m    → 10:05:00  [READY]
  10m   → 10:10:00  [WAIT 240s]
  20m   → 10:20:00  [WAIT 840s]
  30m   → 10:30:00  [WAIT 1440s]
```

## 🧪 Testing

### Run Aggregation Tests

```bash
python test_candle_aggregation.py
```

### Test Output

```
✅ All CandleAggregator tests PASSED!
✅ All TimeframeAdapter mock tests PASSED!
✅ All TimeframeAdapter live tests PASSED!
🎉 All tests PASSED or SKIPPED!
```

## 💡 Advanced Usage

### Check if Timeframe is Aggregated

```python
from data.timeframe_adapter import TimeframeAdapter

is_agg = TimeframeAdapter.is_aggregated_timeframe('10m')  # True
is_agg = TimeframeAdapter.is_aggregated_timeframe('5m')   # False
```

### Get Base Timeframe

```python
base = TimeframeAdapter.get_base_timeframe('10m')  # Returns '5m'
base = TimeframeAdapter.get_base_timeframe('1h')   # Returns '1h' (native)
```

### Get Multiplier

```python
mult = TimeframeAdapter.get_multiplier('20m')  # Returns 4 (20m = 4 × 5m)
mult = TimeframeAdapter.get_multiplier('5m')   # Returns 1 (native)
```

## ⚠️ Important Notes

### 1. Closed Candles Only

The system only uses **closed candles**. For aggregated timeframes:

- **10m**: Requires 2 complete 5m candles
- **50m**: Requires 10 complete 5m candles

If not enough base candles are available, fewer aggregated candles are returned.

### 2. Data Fetching Multiplier

When you request N aggregated candles, the system fetches `N × multiplier` base candles:

| Requested | Timeframe | Multiplier | Base Candles Fetched |
|-----------|-----------|------------|---------------------|
| 50 candles | 10m      | ×2         | 100 5m candles      |
| 50 candles | 20m      | ×4         | 200 5m candles      |
| 50 candles | 40m      | ×8         | 400 5m candles      |
| 50 candles | 50m      | ×10        | 500 5m candles      |

### 3. Rate Limiting

Fetching more base candles means more API calls. The system automatically:
- Uses 50ms delay between requests (Binance rate limit)
- Fetches exact number of candles needed

### 4. Historical Limit

In `main.py`, the default `HISTORICAL_LIMIT=50` means:
- **Native timeframes**: Fetch 50 candles directly
- **10m**: Fetch 100 5m candles → aggregate to 50 10m
- **50m**: Fetch 500 5m candles → aggregate to 50 50m

## 🔍 Validation

The system performs automatic validation:

1. **OHLC Relationship**: `low ≤ open, close ≤ high`
2. **Complete Candles**: Only full periods are returned
3. **Count Verification**: Ensures correct number of base candles per aggregated candle

### Example Validation Log

```
[Aggregator] ✓ Validation passed: 50 aggregated candles are valid
[TimeframeAdapter] ✓ BTCUSDT 10m: Aggregated 100 5m → 50 10m candles
```

## 🐛 Troubleshooting

### Issue: Fewer candles than expected

**Cause**: Not enough complete base candles available

**Solution**: This is normal. For example:
- Request 50 10m candles
- Fetch 100 5m candles from Binance
- But only 99 are complete (1 is forming)
- Result: 49 10m candles (not 50)

### Issue: Candles not aligned

**Cause**: Base candles might not start at perfect boundary

**Solution**: System automatically handles this with `resample()`. Candles will align to:
- 10m: :00, :10, :20, :30, :40, :50
- 20m: :00, :20, :40
- 50m: Every 50 minutes from start

## 📈 Performance

### Memory Usage

- Minimal increase (only stores aggregated result)
- Base candles are discarded after aggregation

### API Calls

- **Native timeframes**: 1 API call per symbol
- **10m**: 1 API call (fetches more candles)
- **50m**: 1 API call (fetches 10× candles)

Same number of API calls, just different limit values.

## 🚀 Future Enhancements

Potential additions (not yet implemented):

1. **More aggregation sources**:
   - 25m from 5m (5 × 5m)
   - 45m from 15m (3 × 15m)

2. **Caching**:
   - Cache aggregated candles to reduce API calls

3. **Multi-level aggregation**:
   - 1h from 20m (3 × 20m) instead of from 5m

## 📞 Support

For issues or questions:
1. Check logs for `[TimeframeAdapter]` and `[Aggregator]` messages
2. Run `python test_candle_aggregation.py` to verify setup
3. Review this documentation

---

**Version**: 1.0.0  
**Last Updated**: October 23, 2025  
**Status**: ✅ Production Ready
