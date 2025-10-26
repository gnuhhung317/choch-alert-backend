# Pattern Groups Update (G1, G2, G3)

## Tổng quan thay đổi

Hệ thống CHoCH Alert đã được cập nhật để hỗ trợ **3 nhóm pattern khác nhau** (G1, G2, G3) thay vì chỉ 1 pattern duy nhất. Web dashboard giờ hiển thị **nhóm pattern** thay vì cột "Hướng" (Long/Short).

## Pattern Groups

### G1 (Original Pattern)
- **Uptrend**: `p2 < p4 < p6 < p8` và `p3 < p5 < p7`
- **Downtrend**: `p3 > p5 > p7` và `p2 > p4 > p6 > p8`

### G2 (New Pattern)
- **Uptrend**: `p3 < p7 < p5`, `p2 < p6 < p4 < p8`, `p2 < p5`
- **Downtrend**: `p3 > p7 > p5`, `p2 > p6 > p4 > p8`, `p2 > p5`

### G3 (New Pattern)
- **Uptrend**: `p3 < p5 < p7`, `p2 < p6 < p4 < p8`, `p2 < p5`
- **Downtrend**: `p3 > p5 > p7`, `p2 > p6 > p4 > p8`, `p2 > p5`

## Các thay đổi chính

### 1. Python Detector (`detectors/choch_detector.py`)
- ✅ Thêm logic kiểm tra 3 nhóm pattern (G1, G2, G3)
- ✅ Lưu thông tin nhóm pattern vào `TimeframeState`
- ✅ Trả về `pattern_group` trong kết quả detection

### 2. Database (`database/models.py`)
- ✅ Thêm cột `pattern_group` (VARCHAR(10)) vào bảng `alerts`
- ✅ Thêm cột `pattern_group` vào bảng `alert_archive`
- ✅ Thêm index cho cột `pattern_group`
- ✅ Cập nhật `to_dict()` và `from_alert_data()` methods

### 3. Alert Creation (`alert/telegram_sender.py`)
- ✅ Thêm parameter `pattern_group` vào `create_alert_data()`
- ✅ Trả về `'nhóm': pattern_group` trong alert data

### 4. Main System (`main.py`)
- ✅ Truyền `pattern_group` từ detection result vào `create_alert_data()`

### 5. Web Dashboard
#### HTML (`web/templates/index.html`)
- ✅ Thay cột "Hướng" thành "Nhóm"
- ✅ Thêm filter "Pattern Group" với options G1, G2, G3

#### JavaScript (`web/static/js/alerts.js`)
- ✅ Hiển thị pattern group (G1/G2/G3) với badge màu Long/Short
- ✅ Thêm pattern filter vào filter system
- ✅ Cập nhật filter logic để hỗ trợ pattern groups

### 6. Pine Script (`indicator.pine`)
- ✅ Thêm logic 3 nhóm pattern giống Python
- ✅ Đồng bộ hoàn toàn với Python detector

## Cách cập nhật hệ thống hiện có

### Bước 1: Backup database
```powershell
# Backup database cũ
Copy-Item "data/choch_alerts.db" "data/choch_alerts.db.backup"
```

### Bước 2: Chạy migration script
```powershell
# Migration sẽ thêm cột pattern_group vào database
python database/add_pattern_group_migration.py
```

### Bước 3: Khởi động lại hệ thống
```powershell
# Stop hệ thống cũ (nếu đang chạy)
./stop_background.bat

# Start hệ thống mới
python main.py
```

## Kiểm tra kết quả

### 1. Kiểm tra Logs
```
[8-PIVOT-G1] ✓✓✓ VALID UPTREND PATTERN: P1:... -> P8:...
[8-PIVOT-G2] ✓✓✓ VALID DOWNTREND PATTERN: P1:... -> P8:...
[8-PIVOT-G3] ✓✓✓ VALID UPTREND PATTERN: P1:... -> P8:...
```

### 2. Kiểm tra Web Dashboard
- Mở http://localhost:5000
- Cột "Nhóm" hiển thị G1/G2/G3 với màu xanh (Long) hoặc đỏ (Short)
- Filter "Pattern Group" cho phép lọc theo G1, G2, G3

### 3. Kiểm tra Database
```python
from database.alert_db import AlertDatabase

db = AlertDatabase()
recent_alerts = db.get_recent_alerts(limit=10)
for alert in recent_alerts:
    print(f"{alert.symbol} {alert.timeframe} - Pattern: {alert.pattern_group} - {alert.direction}")
```

## Tính năng mới

### 1. Pattern Group Badge
- G1, G2, G3 được hiển thị với màu sắc tương ứng với hướng
- **Long (G1/G2/G3)**: Badge xanh lá
- **Short (G1/G2/G3)**: Badge đỏ

### 2. Pattern Filter
- Lọc alerts theo pattern group (G1, G2, G3)
- Có thể chọn multiple patterns cùng lúc
- Filter tags hiển thị active pattern filters

### 3. Database Query
- Có thể query alerts theo pattern_group
- Index trên pattern_group để tăng tốc query

## Backward Compatibility

- ✅ Database migration script tự động thêm cột mới
- ✅ Alerts cũ (không có pattern_group) sẽ hiển thị "N/A"
- ✅ Hệ thống vẫn hoạt động bình thường với alerts cũ
- ✅ Pine Script indicator tương thích ngược

## Testing

### Test Detection
```python
# Test xem detector có trả về pattern_group không
result = detector.process_new_bar('5m', df)
if result.get('choch_up'):
    print(f"Pattern Group: {result.get('pattern_group')}")  # Should print G1, G2, or G3
```

### Test Database
```python
# Test xem database có lưu pattern_group không
from database.alert_db import AlertDatabase
db = AlertDatabase()
alert_data = {
    'mã': 'BTCUSDT',
    'khung': '5m',
    'hướng': 'Long',
    'nhóm': 'G2',  # Pattern group
    'loại': 'CHoCH Up',
    'price': 50000,
    'tradingview_link': 'https://...'
}
alert_id = db.add_alert(alert_data)
alert = db.get_alert_by_id(alert_id)
assert alert.pattern_group == 'G2'
```

### Test Web Dashboard
1. Mở http://localhost:5000
2. Kiểm tra cột "Nhóm" hiển thị G1/G2/G3
3. Test filter "Pattern Group"
4. Kiểm tra badge colors (xanh cho Long, đỏ cho Short)

## Rollback (nếu cần)

Nếu muốn quay lại phiên bản cũ:

```powershell
# 1. Stop hệ thống
./stop_background.bat

# 2. Restore database backup
Copy-Item "data/choch_alerts.db.backup" "data/choch_alerts.db"

# 3. Checkout code cũ
git checkout <previous-commit-hash>

# 4. Start lại
python main.py
```

## Notes

- Pattern group được xác định tại thời điểm phát hiện 8-pivot pattern
- CHoCH signal sẽ kế thừa pattern group từ 8-pivot pattern trước đó
- Mỗi CHoCH signal chỉ thuộc 1 pattern group duy nhất
- Pattern group không thay đổi sau khi được xác định

## Support

Nếu có vấn đề, kiểm tra:
1. Logs trong `choch_alert.log`
2. Database migration đã chạy thành công chưa
3. Web browser console có lỗi JavaScript không
4. Pattern group có được lưu vào database không

---

**Version**: 2.0.0  
**Date**: 2025-10-26  
**Author**: CHoCH Alert System Team
