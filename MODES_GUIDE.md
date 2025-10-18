# CHoCH Alert System - 2 Modes Guide

Hệ thống có 2 modes hoàn toàn khác nhau:

## 🎨 Mode 1: HISTORY MODE (Vẽ Chart)

**Mục đích**: Vẽ chart đàng hoàng cho toàn bộ lịch sử dữ liệu

**Cách hoạt động**:
- Load toàn bộ dữ liệu lịch sử (theo `HISTORICAL_LIMIT`)
- Detect tất cả pivot points
- Vẽ chart với các pivot được nối liên tục
- Lưu chart dạng PNG vào thư mục `charts/`
- Nếu có CHoCH, cũng tạo Pine Script
- **Chạy 1 lần xong thoát** (không chạy liên tục)

### Cách sử dụng:

```bash
# Trong file .env:
ENABLE_CHART=1
CHART_MODE=history

# Rồi chạy:
python main.py
```

**Output**:
```
[HISTORY] Starting history mode...
[BTCUSDT][5m] Fetching historical data...
[BTCUSDT][5m] Processing 500 bars...
[BTCUSDT][5m] Built 45 pivots
[CHART] 📊 Saved: charts/BTCUSDT_5m_20251018_120530.png
...
[HISTORY] ✓ Done! All charts plotted.
```

**Khi nào dùng**:
- Muốn vẽ chart để phân tích
- Muốn kiểm tra pivot detection
- Muốn xuất chart cho mục đích khác

---

## ⚡ Mode 2: REALTIME MODE (Alert Telegram)

**Mục đích**: Chạy liên tục, gửi alert Telegram khi phát hiện CHoCH

**Cách hoạt động**:
- Chạy **liên tục** (loop vô tận)
- Quét data theo interval **của từng timeframe**:
  - Timeframe 5m → quét **5 phút 1 lần**
  - Timeframe 15m → quét **15 phút 1 lần**
  - Timeframe 1h → quét **60 phút 1 lần**
- Khi phát hiện CHoCH:
  - Gửi **alert Telegram** ngay lập tức
  - Broadcast lên **web dashboard**
- **Không vẽ chart** (hoặc vẽ chart tối giản)
- Chạy cho đến khi bạn nhấn `Ctrl+C`

### Cách sử dụng:

```bash
# Trong file .env:
ENABLE_CHART=0
# (CHART_MODE không quan trọng khi ENABLE_CHART=0)

# Rồi chạy:
python main.py
```

**Output**:
```
[REALTIME] Starting realtime mode...
Testing Telegram connection...
Starting web dashboard...
[WEB] Web dashboard available at http://0.0.0.0:5000

============================================================
Loop #1 - Processing 50 symbols × 4 timeframes
============================================================
[BTCUSDT][5m] Fetching data...
[BTCUSDT][5m] ✓ New bar: 2025-10-18 12:00:00 | Close: 67234.50

[SIGNAL] 🎯 CHoCH detected on BTCUSDT 5m: CHoCH Up
[Telegram] Alert sent!
[Web] Alert broadcast to all clients

...

============================================================
Loop #1 Summary:
  Processed: 200/200
  Signals detected: 5
  Duration: 45.2s
  Waiting: 300.0s until next cycle
============================================================
```

**Khi nào dùng**:
- Muốn monitoring 24/7
- Muốn nhận alert khi có CHoCH
- Chạy bot trên server/VPS

---

## 📊 Bảng so sánh

| Tiêu chí | History Mode | Realtime Mode |
|---------|-------------|---------------|
| **ENABLE_CHART** | 1 | 0 |
| **CHART_MODE** | history | realtime (bất kỳ) |
| **Thời gian chạy** | 1 lần, rồi thoát | Vô tận (loop) |
| **Quét interval** | Tất cả một lúc | Theo timeframe |
| **Gửi Telegram** | ❌ Không | ✅ Có |
| **Vẽ chart** | ✅ Có | ❌ Không |
| **Web dashboard** | ❌ Không | ✅ Có |
| **Output** | Thư mục `charts/` | Console + Telegram |

---

## 🔧 Cấu hình chi tiết

### History Mode Config
```ini
ENABLE_CHART=1
CHART_MODE=history
HISTORICAL_LIMIT=500        # Số bars lịch sử để vẽ
TIMEFRAMES=5m,15m,30m,1h   # Timeframes cần vẽ
SYMBOLS=BTCUSDT,ETHUSDT     # Coins cần vẽ (hoặc ALL)
```

### Realtime Mode Config
```ini
ENABLE_CHART=0
# CHART_MODE không quan trọng khi ENABLE_CHART=0
HISTORICAL_LIMIT=500        # Để detect pivots
TIMEFRAMES=5m,15m,30m,1h   # Các timeframe monitor
SYMBOLS=BTCUSDT,ETHUSDT     # Coins monitor (hoặc ALL)
UPDATE_INTERVAL=60          # Minimum interval (seconds)
FLASK_PORT=5000             # Port web dashboard
```

---

## 💡 Ví dụ thực tế

### Scenario 1: Muốn vẽ chart để phân tích
```bash
# .env
ENABLE_CHART=1
CHART_MODE=history
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
TIMEFRAMES=1h
HISTORICAL_LIMIT=500

# Chạy
python main.py

# Result: 
# - 3 coins × 1 timeframe = 3 charts
# - Lưu vào charts/
```

### Scenario 2: Monitoring 24/7
```bash
# .env
ENABLE_CHART=0
SYMBOLS=ALL
TIMEFRAMES=5m,15m,1h
MIN_VOLUME_24H=1000000

# Chạy
python main.py

# Result:
# - Monitor tất cả coins
# - Gửi Telegram khi có CHoCH
# - Web dashboard ở http://localhost:5000
```

### Scenario 3: Monitoring từng coin
```bash
# .env
ENABLE_CHART=0
SYMBOLS=BTCUSDT
TIMEFRAMES=15m,1h,4h

# Chạy
python main.py

# Result:
# - Chỉ BTC, 3 timeframes
# - Quét 15m, 1h, 4h
```

---

## 🚀 Tips & Tricks

### Quét nhiều timeframe với interval khác nhau
Realtime mode tự động:
- 5m timeframe → quét 5 min 1 lần
- 15m timeframe → quét 15 min 1 lần
- 1h timeframe → quét 60 min 1 lần

Hệ thống sẽ đợi đủ thời gian rồi mới quét lần tiếp theo.

### Vẽ chart nhanh
Chỉ vẽ timeframe chính:
```ini
TIMEFRAMES=1h
```

### Monitor tất cả coins
```ini
ENABLE_CHART=0
SYMBOLS=ALL
MIN_VOLUME_24H=5000000   # Volume tối thiểu
```

---

## ⚠️ Lưu ý

- **History mode**: Nếu có nhiều coins/timeframes, sẽ mất thời gian. Nên chỉ vẽ vài coins/timeframes cần thiết.
- **Realtime mode**: Cần Telegram bot token và chat ID để gửi alert
- **Realtime mode**: Web dashboard chạy trên port 5000, có thể thay đổi trong `.env`
