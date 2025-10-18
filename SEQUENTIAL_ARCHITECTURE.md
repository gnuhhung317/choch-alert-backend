# Sequential Monitoring Architecture

## 🎯 Cách hoạt động mới

### Trước (Concurrent):
```
❌ 100 coins × 4 timeframes = 400 concurrent tasks
❌ 400 × fetch(500 bars) = QUEUE OVERFLOW!
❌ Rate limit exceeded
```

### Sau (Sequential):
```
✅ Loop: For each coin → For each timeframe → Fetch → Process → Next
✅ 1 request tại một thời điểm
✅ Không bao giờ queue overflow
```

## 📊 Flow Diagram

```
START
  ↓
┌─────────────────────────┐
│  Get list of symbols    │
│  (ALL or specific)      │
└─────────┬───────────────┘
          ↓
┌─────────────────────────┐
│  MAIN LOOP (infinite)   │
└─────────┬───────────────┘
          ↓
    ┌─────────────┐
    │ For Symbol  │ ← BTCUSDT
    └─────┬───────┘
          ↓
      ┌───────────┐
      │ For TF    │ ← 5m
      └─────┬─────┘
            ↓
      ┌──────────────┐
      │ Fetch 500    │
      │ bars         │
      └─────┬────────┘
            ↓
      ┌──────────────┐
      │ Is new bar?  │
      └─────┬────────┘
            ↓
      ┌──────────────┐
      │ Detect CHoCH │
      └─────┬────────┘
            ↓
      ┌──────────────┐
      │ Send Alert?  │
      └─────┬────────┘
            ↓
      Next Timeframe (15m, 30m, 1h...)
            ↓
    Next Symbol (ETHUSDT, BNBUSDT...)
          ↓
    ┌─────────────┐
    │ Wait 60s    │
    └─────┬───────┘
          ↓
    Back to MAIN LOOP
```

## ⚙️ Configuration Example

```env
# Option 1: Specific coins (Recommended)
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT
TIMEFRAMES=5m,15m,30m,1h
HISTORICAL_LIMIT=500

# Option 2: Top volume coins
FETCH_ALL_COINS=1
MIN_VOLUME_24H=10000000
QUOTE_CURRENCY=USDT
TIMEFRAMES=15m,1h
```

## 🔢 Performance Calculation

### Example: 10 coins, 4 timeframes

**Per Loop:**
- 10 coins × 4 timeframes = 40 requests
- 40 × 50ms (rate limit) = 2 seconds
- Loop total: ~5-10 seconds

**Detection Frequency:**
- Minimum timeframe: 5m = 300s
- Loop completes in: 10s
- **Checks per candle: 300/10 = 30 times**
- More than enough to catch every new bar!

### Example: 50 coins, 4 timeframes

**Per Loop:**
- 50 coins × 4 timeframes = 200 requests
- 200 × 50ms = 10 seconds
- Loop total: ~15-20 seconds

**Detection Frequency:**
- 5m timeframe: checked every 20s
- **15 checks per 5-minute candle** ✅

## 📈 Benefits

### ✅ Advantages:
1. **Simple** - Easy to understand and debug
2. **Reliable** - No queue overflow, no rate limit issues
3. **Resource Efficient** - Low memory, predictable CPU
4. **Scalable** - Works with 10 or 100 coins
5. **Fast Detection** - Multiple checks per candle

### ⚠️ Trade-offs:
1. **Not Real-time** - Delay of loop duration (5-20s)
2. **Sequential** - One request at a time
3. **Polling-based** - No WebSocket push notifications

### ✨ Why it's still GREAT:
- CHoCH signals are candle-based (not tick-based)
- Loop completes WAY faster than candle duration
- Checking 10-30 times per candle is MORE than enough
- Zero infrastructure complexity

## 🎯 Best Practices

### For 5-10 coins:
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
TIMEFRAMES=5m,15m,30m,1h
HISTORICAL_LIMIT=500
```
**Loop time: ~3-5 seconds**

### For 20-50 coins:
```env
FETCH_ALL_COINS=1
MIN_VOLUME_24H=10000000
TIMEFRAMES=15m,30m,1h
HISTORICAL_LIMIT=500
```
**Loop time: ~10-15 seconds**

### For 100+ coins:
```env
FETCH_ALL_COINS=1
MIN_VOLUME_24H=50000000  # Higher filter
TIMEFRAMES=1h,4h         # Longer timeframes
HISTORICAL_LIMIT=300     # Less history
```
**Loop time: ~30-40 seconds**

## 🚀 Running

```powershell
# 1. Configure .env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
TIMEFRAMES=5m,15m,1h

# 2. Run
python main.py

# Output:
[BTCUSDT][5m] Fetched 500 bars
[BTCUSDT][5m] New bar: 2025-10-18 13:00:00 | Close: 67450.30
[BTCUSDT][15m] Fetched 500 bars
...
[ETHUSDT][5m] Fetched 500 bars
...
[LOOP] Completed in 5.2s. Waiting 60s until next cycle...
```

## 📝 Code Changes

### binance_fetcher.py
- ❌ Removed: `watch_ohlcv_websocket()`
- ❌ Removed: `poll_ohlcv()`
- ❌ Removed: `start_watching()`
- ✅ Kept: `fetch_historical()` (simple fetch)
- ✅ Kept: `get_all_usdt_pairs()` (list coins)

### main.py
- ❌ Removed: Concurrent task management
- ❌ Removed: Callback wrappers
- ✅ Added: `monitor_loop()` - simple sequential loop
- ✅ Added: Smart wait between cycles

## 💡 Summary

**Old way:** Complex, concurrent, prone to overflow
**New way:** Simple loop, reliable, scales perfectly

The key insight: **CHoCH detection doesn't need real-time tick data**. Checking every 5-20 seconds is MORE than enough for candle-based signals!
