# Candle Aggregation Design - Loose Coupling Architecture

## 🎯 Mục tiêu
Hỗ trợ các khung thời gian m10, m20, m40, m50 bằng cách gộp nến m5, với kiến trúc:
- **Loose coupling**: Không ảnh hưởng đến code hiện tại
- **Transparent**: Phần còn lại của hệ thống không biết nến được gộp hay không
- **Extensible**: Dễ mở rộng cho các timeframe khác

## 🏗️ Kiến trúc đề xuất

### 1. **Candle Aggregator Layer** (Tầng gộp nến - Middleware)

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN APPLICATION                         │
│  (main.py, choch_detector.py - KHÔNG THAY ĐỔI)            │
└─────────────────┬───────────────────────────────────────────┘
                  │ fetch_historical(symbol, "10m", limit=50)
                  ↓
┌─────────────────────────────────────────────────────────────┐
│              TIMEFRAME ADAPTER (New Layer)                  │
│  - Phát hiện timeframe có cần gộp không?                   │
│  - m10, m20, m40, m50 → gọi CandleAggregator               │
│  - Các timeframe khác → passthrough trực tiếp             │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ↓                   ↓
┌──────────────┐    ┌──────────────────┐
│ PASSTHROUGH  │    │ CANDLE AGGREGATOR│
│ (5m,15m,30m) │    │   (10m,20m,40m)  │
│      ↓       │    │        ↓         │
│  Binance     │    │  Fetch 5m → Gộp │
└──────────────┘    └──────────────────┘
        │                   │
        └─────────┬─────────┘
                  ↓
        ┌─────────────────────┐
        │  Return DataFrame   │
        │  (Same interface)   │
        └─────────────────────┘
```

### 2. **File Structure**

```
choch-alert-backend/
├── data/
│   ├── binance_fetcher.py        # Existing - KHÔNG THAY ĐỔI
│   ├── candle_aggregator.py      # NEW - Logic gộp nến
│   └── timeframe_adapter.py      # NEW - Wrapper/Middleware layer
├── utils/
│   └── timeframe_scheduler.py    # Existing - CẬP NHẬT: thêm m10,m20,m40,m50
├── config.py                      # Existing - CẬP NHẬT: cho phép m10,m20,m40,m50
└── main.py                        # Existing - THAY ĐỔI NHỎ: dùng TimeframeAdapter
```

### 3. **Component Design**

#### A. `CandleAggregator` (Logic gộp nến)
```python
class CandleAggregator:
    """
    Pure logic class - Gộp nến m5 thành các timeframe khác
    Không phụ thuộc vào Binance hay bất kỳ data source nào
    """
    
    @staticmethod
    def aggregate(df_5m: pd.DataFrame, target_minutes: int) -> pd.DataFrame:
        """
        Gộp DataFrame 5m thành timeframe khác
        
        Args:
            df_5m: DataFrame với index là timestamp (khung 5m)
            target_minutes: Số phút của timeframe đích (10, 20, 40, 50)
        
        Returns:
            DataFrame với timeframe đã gộp
        """
        # Logic gộp:
        # - open: lấy giá trị đầu tiên
        # - high: lấy max
        # - low: lấy min
        # - close: lấy giá trị cuối cùng
        # - volume: tổng volume
```

#### B. `TimeframeAdapter` (Middleware/Wrapper)
```python
class TimeframeAdapter:
    """
    Adapter pattern - Wrapper around BinanceFetcher
    Tự động gộp nến cho các timeframe không native
    """
    
    # Mapping: Timeframe không native → (base_timeframe, multiplier)
    AGGREGATION_MAP = {
        '10m': ('5m', 2),   # 10m = 2 × 5m
        '20m': ('5m', 4),   # 20m = 4 × 5m
        '40m': ('5m', 8),   # 40m = 8 × 5m
        '50m': ('5m', 10),  # 50m = 10 × 5m
    }
    
    def __init__(self, binance_fetcher: BinanceFetcher):
        self.fetcher = binance_fetcher
        self.aggregator = CandleAggregator()
    
    async def fetch_historical(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """
        Interface giống hệt BinanceFetcher.fetch_historical
        Tự động gộp nến nếu cần
        """
        if timeframe in self.AGGREGATION_MAP:
            # Timeframe cần gộp
            base_tf, multiplier = self.AGGREGATION_MAP[timeframe]
            
            # Tính số nến base cần fetch
            # Ví dụ: cần 50 nến 10m → fetch 50 × 2 = 100 nến 5m
            base_limit = limit * multiplier
            
            # Fetch base timeframe
            df_base = await self.fetcher.fetch_historical(symbol, base_tf, base_limit)
            
            # Gộp nến
            df_aggregated = self.aggregator.aggregate(df_base, multiplier * 5)
            
            # Đảm bảo đúng limit
            return df_aggregated.tail(limit)
        else:
            # Timeframe native - passthrough
            return await self.fetcher.fetch_historical(symbol, timeframe, limit)
```

#### C. Update `TimeframeScheduler`
```python
# Thêm vào TF_TO_MINUTES
TF_TO_MINUTES = {
    # ... existing ...
    '10m': 10,  # NEW
    '20m': 20,  # NEW
    '40m': 40,  # NEW
    '50m': 50,  # NEW
}
```

### 4. **Integration Pattern**

#### Trong `main.py` - Thay đổi tối thiểu:

```python
# OLD:
self.fetcher = BinanceFetcher(api_key=..., secret=...)

# NEW:
base_fetcher = BinanceFetcher(api_key=..., secret=...)
self.fetcher = TimeframeAdapter(base_fetcher)  # Wrap với adapter

# Phần còn lại KHÔNG ĐỔI - vẫn dùng self.fetcher.fetch_historical()
```

### 5. **Closed Candle Logic**

**QUAN TRỌNG**: Đảm bảo logic "chỉ dùng nến đã đóng" vẫn hoạt động:

```python
def aggregate(df_5m: pd.DataFrame, target_minutes: int) -> pd.DataFrame:
    """
    Gộp nến 5m → nến lớn hơn
    
    CRITICAL: Chỉ gộp các nến ĐÃ ĐÓNG
    - Input: df_5m đã loại bỏ nến đang mở (từ BinanceFetcher)
    - Output: Chỉ trả về các nến lớn ĐÃ HOÀN CHỈNH
    
    Example: 
    - 10:00-10:05 (closed) ┐
    - 10:05-10:10 (closed) ┴→ 10:00-10:10 (closed 10m candle)
    - 10:10-10:15 (open)   → KHÔNG gộp (vì chưa đóng)
    """
    # Logic gộp với resample
    # Chỉ trả về các group hoàn chỉnh
```

## 📊 Ví dụ cụ thể

### Scenario: Fetch 10m candles

```python
# User code (trong main.py):
df = await fetcher.fetch_historical("BTCUSDT", "10m", limit=50)

# Internally:
# 1. TimeframeAdapter nhận thấy "10m" cần gộp
# 2. Fetch 100 nến 5m (50 × 2) từ Binance
# 3. BinanceFetcher loại bỏ nến 5m đang mở → 99 nến 5m closed
# 4. CandleAggregator gộp 99 nến 5m → 49 nến 10m closed
# 5. Trả về 49 nến 10m (hoặc 50 nếu đủ data)
```

### Timeline cho 10m:

```
Binance 5m candles:
09:50-09:55 ✓ closed
09:55-10:00 ✓ closed  }→ 09:50-10:00 (10m closed)
10:00-10:05 ✓ closed
10:05-10:10 ✓ closed  }→ 10:00-10:10 (10m closed)
10:10-10:15 ✓ closed
10:15-10:20 ⏳ OPEN    }→ KHÔNG gộp (chưa đủ 2 nến closed)

Result: Trả về 2 nến 10m đã đóng
```

## 🔄 Scheduler Integration

### Quét m10 theo đúng timing:

```python
# m10 nến đóng lúc: :00, :10, :20, :30, :40, :50
# Scheduler sẽ quét ở :00:30, :10:30, :20:30, ... (30s buffer)

scheduler = TimeframeScheduler(['5m', '10m', '15m', '30m'])

# Lúc 10:10:30 (30s sau khi nến 10m đóng):
scannable = scheduler.get_scannable_timeframes()  
# → ['5m', '10m']  (cả 5m và 10m đều đóng lúc 10:10)
```

## ✅ Ưu điểm của kiến trúc này

1. **Loose Coupling**:
   - `main.py`, `choch_detector.py` không biết về gộp nến
   - Chỉ thêm 1 dòng wrap: `TimeframeAdapter(fetcher)`

2. **Transparent**:
   - Interface `fetch_historical()` giống hệt
   - Trả về cùng format DataFrame

3. **Testable**:
   - `CandleAggregator` pure logic, dễ test
   - Mock `BinanceFetcher` để test `TimeframeAdapter`

4. **Extensible**:
   - Muốn thêm m25? → Thêm vào `AGGREGATION_MAP`
   - Muốn gộp từ m15? → Đổi base_timeframe

5. **No Breaking Changes**:
   - Hệ thống cũ vẫn hoạt động bình thường
   - Timeframe native (5m, 15m, 30m) không ảnh hưởng

## 📝 Implementation Checklist

- [ ] Tạo `data/candle_aggregator.py` với logic gộp nến
- [ ] Tạo `data/timeframe_adapter.py` với adapter pattern
- [ ] Test `CandleAggregator` với data mẫu
- [ ] Update `TimeframeScheduler.TF_TO_MINUTES`
- [ ] Update `main.py` wrap fetcher với adapter
- [ ] Test end-to-end với m10, m20, m40, m50
- [ ] Verify closed candle logic vẫn đúng
- [ ] Test scheduler timing cho các timeframe mới

## 🧪 Test Cases

```python
# Test 1: Gộp 10 nến 5m → 50m
df_5m = fetch_5m_data(limit=10)  # 50 phút data
df_50m = aggregator.aggregate(df_5m, 50)
assert len(df_50m) == 1  # 1 nến 50m

# Test 2: Gộp không đủ nến → trả về empty
df_5m = fetch_5m_data(limit=9)  # Thiếu 1 nến
df_50m = aggregator.aggregate(df_5m, 50)
assert len(df_50m) == 0  # Không đủ để tạo nến 50m hoàn chỉnh

# Test 3: Verify OHLCV correctness
# Open = first 5m open
# High = max of all 5m highs
# Low = min of all 5m lows
# Close = last 5m close
# Volume = sum of all 5m volumes
```

## 🚀 Migration Path

### Phase 1: Setup (không ảnh hưởng production)
- Tạo `CandleAggregator` và test riêng
- Tạo `TimeframeAdapter` và test với mock

### Phase 2: Integration (soft rollout)
- Deploy với config chỉ dùng timeframe native
- Monitor để đảm bảo không breaking changes

### Phase 3: Enable new timeframes
- Thêm m10, m20, m40, m50 vào config
- Monitor scheduler và alert accuracy

### Phase 4: Optimize (optional)
- Cache aggregated candles nếu cần
- Optimize memory usage cho large datasets
