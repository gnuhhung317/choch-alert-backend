# Multi-Coin Monitoring Guide - Binance Futures

## 🚀 Tính năng mới

Hệ thống hỗ trợ monitoring **nhiều futures** cùng lúc với **nhiều timeframes**!

## 📋 Cấu hình trong file `.env`

### Option 1: Single Future (Mặc định)
```env
SYMBOL=BTCUSDT
```

### Option 2: Multiple Specific Futures
```env
# Bỏ comment dòng SYMBOLS và comment SYMBOL
# SYMBOL=BTCUSDT
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,ADAUSDT,SOLUSDT,DOGEUSDT,XRPUSDT
```

### Option 3: ALL Binance Futures (Recommended)
```env
# Monitor TẤT CẢ futures trên Binance có đủ volume
FETCH_ALL_COINS=1
MIN_VOLUME_24H=1000000
QUOTE_CURRENCY=USDT
```

## ⚙️ Cấu hình nâng cao

### Volume Filter
```env
# Chỉ monitor futures có volume 24h >= $1M
MIN_VOLUME_24H=1000000

# Hoặc $10M cho top futures
MIN_VOLUME_24H=10000000
```

### Historical Data
```env
# Số bars để phân tích pivot (khuyến nghị 500)
HISTORICAL_LIMIT=500
```

### Timeframes
```env
# Các timeframes cần monitor (tách bằng dấu phẩy)
TIMEFRAMES=5m,15m,30m,1h,4h
```

## 🎯 Polling Strategy

Hệ thống tự động tối ưu polling:
- **5m**: Poll mỗi 5 phút (đúng khi nến đóng)
- **15m**: Poll mỗi 15 phút
- **30m**: Poll mỗi 30 phút
- **1h**: Poll mỗi 60 phút

## 📊 Ví dụ Setup

### Setup 1: Top 10 Futures
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,AVAXUSDT,DOTUSDT,MATICUSDT
TIMEFRAMES=5m,15m,1h
HISTORICAL_LIMIT=500
```

### Setup 2: All High Volume Futures
```env
FETCH_ALL_COINS=1
MIN_VOLUME_24H=5000000
QUOTE_CURRENCY=USDT
TIMEFRAMES=15m,30m,1h
HISTORICAL_LIMIT=500
```

### Setup 3: Quick Scalping
```env
SYMBOLS=BTCUSDT,ETHUSDT
TIMEFRAMES=1m,5m,15m
HISTORICAL_LIMIT=200
```

## 🔍 Monitoring Output

Khi chạy, bạn sẽ thấy:
```
==================================================================================
CHoCH ALERT SYSTEM - MULTI-COIN MONITORING
==================================================================================
Found 150 futures to monitor
Timeframes: 5m, 15m, 30m, 1h
Pivot Settings: Left=1, Right=1
Historical Bars: 500
Total watchers: 150 symbols × 4 timeframes = 600
==================================================================================
[BTCUSDT][5m] New bar: 2025-10-18 13:00:00 | Close: 106630.60
[ETHUSDT][5m] New bar: 2025-10-18 13:00:00 | Close: 2450.30
[SIGNAL] CHoCH detected on BTCUSDT 15m: CHoCH Up
```

## ⚡ Performance Tips

1. **Giảm số timeframes** nếu monitor nhiều futures:
   ```env
   # Thay vì 5 timeframes, dùng 2-3
   TIMEFRAMES=15m,1h
   ```

2. **Tăng volume filter** để giảm số futures:
   ```env
   MIN_VOLUME_24H=10000000  # Chỉ top futures
   ```

3. **Dùng VPS/Server** để chạy 24/7 không bị gián đoạn

## 🎨 Rate Limiting

- Hệ thống tự động delay 0.1s giữa mỗi future để tránh rate limit
- CCXT có built-in rate limiting
- Polling interval tối ưu dựa trên timeframe

## 📝 Notes

- Mỗi future + timeframe = 1 watcher độc lập
- 100 futures × 4 timeframes = 400 watchers concurrent
- Memory usage: ~500KB per watcher
- API calls: 1 call per candle close (rất tiết kiệm!)
- **Format**: Dùng format Binance Futures `BTCUSDT` (không có dấu `/`)

## 🚨 Alerts

Mỗi CHoCH signal sẽ:
1. ✅ Log ra console
2. 📱 Gửi Telegram alert
3. 🌐 Broadcast tới web dashboard

Alert format:
```
[SIGNAL] CHoCH detected on BTCUSDT 15m: CHoCH Up
Price: 67,450.30
Time: 2025-10-18 13:00:00
```
