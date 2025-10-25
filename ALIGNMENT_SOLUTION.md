# Candle Alignment Solution - Fixed Reference Points

## Vấn đề

Các khung thời gian tùy chỉnh (10m, 20m, 25m, 40m) cần được gộp từ nến 5m, nhưng phải **đảm bảo alignment chính xác** với giờ mở cửa thực tế từ sàn.

### Phát hiện quan trọng

**Không phải tất cả timeframe đều chia hết cho 24h:**

```
1440 phút (24h) % 10 = 0  ✓ Có thể align với midnight
1440 phút (24h) % 20 = 0  ✓ Có thể align với midnight  
1440 phút (24h) % 25 = 15 ✗ KHÔNG chia hết!
1440 phút (24h) % 40 = 0  ✓ Có thể align với midnight
```

**25m đặc biệt:** Vì không chia hết 24h, nến 25m không reset tại 00:00 mỗi ngày. Cần dùng **FIXED REFERENCE POINT** để tính toán.

## Giải pháp: Fixed Reference Points

### Reference Times (Thời gian mở cửa nến được cung cấp - UTC)

```python
TIMEFRAME_REFERENCES = {
    '10m': datetime(2025, 10, 24, 17, 10, 0),
    '20m': datetime(2025, 10, 24, 17, 20, 0),
    '25m': datetime(2025, 10, 24, 17, 5, 0),   # CRITICAL!
    '40m': datetime(2025, 10, 24, 16, 40, 0),
}
```

### Thuật toán

Thay vì dùng midnight làm gốc, tính toán từ **reference time cố định**:

```python
def get_candle_period_start(timestamp, interval_minutes, reference_time):
    # Tính số phút từ reference đến timestamp
    diff_minutes = (timestamp - reference_time).total_seconds() / 60
    
    # Tìm period index (làm tròn xuống)
    period_index = int(diff_minutes // interval_minutes)
    
    # Tính thời gian mở cửa của period
    period_start = reference_time + timedelta(minutes=period_index * interval_minutes)
    
    return period_start
```

**Ví dụ cho 25m:**
- Reference: `2025-10-24 17:05:00`
- Nến tiếp theo: `17:05 + 25m = 17:30`
- Nến trước đó: `17:05 - 25m = 16:40`
- Qua midnight: `23:45 + 25m = 00:10` (ngày hôm sau)

## Triển khai

### 1. AlignedCandleAggregator (`data/aligned_candle_aggregator.py`)

Module mới thay thế logic resample cũ:

```python
class AlignedCandleAggregator:
    TIMEFRAME_REFERENCES = {
        '10m': datetime(2025, 10, 24, 17, 10, 0),
        '20m': datetime(2025, 10, 24, 17, 20, 0),
        '25m': datetime(2025, 10, 24, 17, 5, 0),
        '40m': datetime(2025, 10, 24, 16, 40, 0),
        '50m': datetime(2025, 10, 20, 0, 0, 0),
    }
    
    @staticmethod
    def aggregate(df, target_timeframe, base_minutes=5):
        # Gán mỗi nến 5m vào period tương ứng dựa trên reference
        # Group và aggregate OHLCV
        # Chỉ giữ lại complete periods
```

**Ưu điểm:**
- ✓ Perfect alignment với thời gian thực tế từ sàn
- ✓ Hoạt động với cả timeframe chia hết và không chia hết 24h
- ✓ Nhất quán qua nhiều ngày

### 2. TimeframeAdapter (`data/timeframe_adapter.py`)

Cập nhật sử dụng `AlignedCandleAggregator`:

```python
# Old (pandas resample - không chính xác)
df_aggregated = self.aggregator.aggregate(df_base, target_minutes, base_minutes)

# New (fixed reference points - chính xác)
df_aggregated = AlignedCandleAggregator.aggregate(df_base, timeframe, base_minutes)
```

### 3. TimeframeScheduler (`utils/timeframe_scheduler.py`)

Scheduler cũng sử dụng **cùng reference points** để đồng bộ:

```python
class TimeframeScheduler:
    # Same references as AlignedCandleAggregator
    TIMEFRAME_REFERENCES = {
        '10m': datetime(2025, 10, 24, 17, 10, 0),
        '20m': datetime(2025, 10, 24, 17, 20, 0),
        '25m': datetime(2025, 10, 24, 17, 5, 0),
        '40m': datetime(2025, 10, 24, 16, 40, 0),
    }
    
    def get_next_candle_close_time(self, timeframe):
        if timeframe in self.TIMEFRAME_REFERENCES:
            # Tính từ reference thay vì midnight
            ...
```

**Quan trọng:** Aggregator và Scheduler **PHẢI** dùng cùng reference để đảm bảo nhất quán.

## Testing

### Test suite toàn diện (`test_comprehensive_alignment.py`)

```bash
python test_comprehensive_alignment.py
```

**Kết quả:**
```
✅ TEST 1 PASSED: All aggregated candles align with reference times
✅ TEST 2 PASSED: Scheduler has correct reference times
✅ TEST 3 PASSED: 25m candles properly aligned across 3 days

🎉 ALL TESTS PASSED!
```

### Xác minh thủ công

**25m alignment qua midnight:**

```python
# Reference: 2025-10-24 17:05
# Period 0:  2025-10-24 17:05
# Period 1:  2025-10-24 17:30
# Period 2:  2025-10-24 17:55
# Period 3:  2025-10-24 18:20
# ...
# Period 16: 2025-10-24 23:45
# Period 17: 2025-10-25 00:10  ← Qua midnight!
# Period 18: 2025-10-25 00:35
```

Lưu ý: Nến **KHÔNG** bắt đầu tại 00:00 như các timeframe khác!

## Web Dashboard Updates

### 1. Timezone GMT+7

Chuyển đổi thời gian từ UTC sang giờ Việt Nam:

```javascript
function convertToGMT7(utcTimeString) {
    const utcDate = new Date(utcTimeString);
    const gmt7Date = new Date(utcDate.getTime() + (7 * 60 * 60 * 1000));
    
    // Format: DD/MM HH:MM
    return `${day}/${month} ${hours}:${minutes}`;
}
```

### 2. Mobile Optimization

**Cải tiến responsive:**
- Font size nhỏ hơn (12px → 10px trên mobile)
- Padding giảm (30px → 10px)
- Table cells compact hơn
- Ẩn icons không cần thiết trên mobile
- Grid layout responsive cho filters

**Kết quả:**
- Xem được nhiều cột hơn trên điện thoại
- Tải nhanh hơn
- UX tốt hơn trên màn hình nhỏ

## Migration Guide

### Nếu bạn đã có code cũ

1. **Import mới:**
   ```python
   from data.aligned_candle_aggregator import AlignedCandleAggregator
   ```

2. **Thay thế aggregation logic:**
   ```python
   # Old
   df_agg = aggregator.aggregate(df, target_minutes, base_minutes)
   
   # New
   df_agg = AlignedCandleAggregator.aggregate(df, target_timeframe)
   ```

3. **Chạy test:**
   ```bash
   python test_comprehensive_alignment.py
   ```

### Nếu bắt đầu mới

- Sử dụng `TimeframeAdapter` - nó tự động dùng `AlignedCandleAggregator`
- Không cần quan tâm chi tiết, chỉ cần gọi `fetch_historical()`

## Performance

### Memory

- Không tăng đáng kể (chỉ lưu reference times - 5 datetime objects)
- Không cache trung gian

### Speed

- Tương đương với resample cũ
- O(n) complexity cho n nến 5m
- Test với 288 nến 5m (24h): ~10-20ms

### API Calls

- **Không thay đổi** số lượng API calls
- Vẫn fetch đúng số nến 5m cần thiết

## Troubleshooting

### Nếu alignment không đúng

1. **Kiểm tra reference times có khớp không:**
   ```python
   print(AlignedCandleAggregator.TIMEFRAME_REFERENCES)
   print(TimeframeScheduler.TIMEFRAME_REFERENCES)
   # Phải giống nhau!
   ```

2. **Verify với reference time được cung cấp:**
   ```python
   df_25m = AlignedCandleAggregator.aggregate(df_5m, '25m')
   ref_time = datetime(2025, 10, 24, 17, 5, 0)
   assert ref_time in df_25m.index
   ```

3. **Chạy test suite:**
   ```bash
   python test_comprehensive_alignment.py
   ```

### Nếu thêm timeframe mới

1. Thêm vào `TIMEFRAME_REFERENCES` ở **CẢ HAI** file:
   - `data/aligned_candle_aggregator.py`
   - `utils/timeframe_scheduler.py`

2. Kiểm tra xem 1440 % interval có bằng 0 không:
   ```python
   interval = 25
   can_align_midnight = (1440 % interval == 0)
   # Nếu False → BẮT BUỘC phải có reference time
   ```

3. Chạy test để verify

## Kết luận

**Giải pháp Fixed Reference Points** là cách **duy nhất chính xác** để handle:
- ✓ Timeframe không chia hết 24h (như 25m)
- ✓ Alignment nhất quán qua nhiều ngày
- ✓ Đồng bộ giữa aggregator và scheduler
- ✓ Perfect match với giờ mở cửa thực tế từ sàn

**Không nên** dùng:
- ❌ Pandas resample với midnight offset (sai cho 25m)
- ❌ Dynamic offset calculation (không nhất quán)
- ❌ Mod-based alignment without reference (sai qua midnight)

---

**Version:** 1.0.0  
**Date:** 2025-10-25  
**Status:** ✅ Production Ready
