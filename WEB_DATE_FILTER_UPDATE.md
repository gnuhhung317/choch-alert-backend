# Web Date Filter Update - CHoCH Alert Backend

## Tổng Quan
Cập nhật hệ thống lọc ngày trên web dashboard để hỗ trợ xem dữ liệu của tất cả các ngày, không chỉ hôm nay.

## Các Tính Năng Mới

### 1. Backend API Enhancements (`web/app.py`)

**Tham số mới cho `/api/alerts`:**
- `date_filter`: 
  - `'today'` - Chỉ alerts hôm nay (GMT+7)
  - `'all'` - Tất cả alerts (không lọc ngày)
  - `'YYYY-MM-DD'` - Ngày cụ thể (format ISO)
- `start_date`: Ngày bắt đầu (format: YYYY-MM-DD)
- `end_date`: Ngày kết thúc (format: YYYY-MM-DD)

**Các chế độ lọc:**
1. **Today Mode**: `date_filter=today` - Chỉ lấy alerts từ 00:00 hôm nay (GMT+7)
2. **All Mode**: `date_filter=all` hoặc không truyền tham số - Lấy tất cả alerts
3. **Specific Date**: `date_filter=2025-10-31` - Lấy alerts của ngày cụ thể
4. **Date Range**: `start_date=2025-10-01&end_date=2025-10-31` - Lấy alerts trong khoảng thời gian

### 2. Frontend UI Updates (`web/templates/index.html`)

**Date Filter Dropdown:**
```html
<select id="dateFilter" onchange="toggleCustomDateRange()">
    <option value="today" selected>Hôm nay</option>
    <option value="all">Tất cả các ngày</option>
    <option value="custom">Tùy chọn ngày...</option>
</select>
```

**Custom Date Range Picker:**
- Hiện khi chọn "Tùy chọn ngày..."
- 2 input fields: "Từ ngày" và "Đến ngày" (HTML5 date picker)
- Tự động ẩn khi chọn "Hôm nay" hoặc "Tất cả các ngày"

### 3. Frontend Logic Updates (`web/static/js/alerts.js`)

**Cải tiến chính:**
1. **Reload từ API khi apply filters** - Thay vì chỉ filter client-side, giờ gọi lại API với date parameters
2. **Custom date range support** - Lưu `startDate` và `endDate` trong `currentFilters`
3. **Smart date filtering**:
   - Real-time alerts: Vẫn filter client-side nếu date = 'today'
   - Historical data: Filter server-side qua API
4. **Active filter tags** - Hiển thị date filter đang active với icon và text phù hợp

## Luồng Hoạt Động

### Khi Load Trang Lần Đầu:
```javascript
// Default: Load today's alerts
currentFilters.date = 'today'
→ API call: GET /api/alerts?limit=500&date_filter=today
→ Display alerts từ 00:00 hôm nay đến hiện tại (GMT+7)
```

### Khi Chọn "Tất cả các ngày":
```javascript
currentFilters.date = 'all'
→ API call: GET /api/alerts?limit=500&date_filter=all
→ Display tất cả alerts (tối đa 500)
```

### Khi Chọn "Tùy chọn ngày":
```javascript
// Show custom date picker
toggleCustomDateRange() → Hiện startDate và endDate inputs

// User chọn: Từ 01/10/2025 đến 31/10/2025
currentFilters.date = 'custom'
currentFilters.startDate = '2025-10-01'
currentFilters.endDate = '2025-10-31'

→ API call: GET /api/alerts?limit=500&start_date=2025-10-01&end_date=2025-10-31
→ Display alerts trong khoảng từ 00:00 ngày 01/10 đến 23:59:59 ngày 31/10 (GMT+7)
```

### Real-time Alert Handling:
```javascript
socket.on('alert', (data) => {
    // Check nếu alert pass current filters
    if (currentFilters.date === 'today' && !isToday(data.time_date)) {
        return; // Skip alert không phải hôm nay
    }
    
    if (currentFilters.date === 'all') {
        // Accept tất cả real-time alerts
    }
    
    if (currentFilters.date === 'custom') {
        // Accept tất cả (custom range chỉ áp dụng cho historical data)
    }
});
```

## Breaking Changes

**None** - Tương thích ngược 100%:
- Default behavior vẫn là "Hôm nay"
- API endpoint `/api/alerts` vẫn hoạt động như cũ nếu không truyền date params
- Socket.IO real-time alerts không thay đổi

## Testing

### Test Cases:

1. **Default Load (Today)**:
   ```
   - Mở dashboard
   - Verify: Chỉ hiện alerts hôm nay
   - Verify: Filter tag hiện "Ngày: Hôm nay"
   ```

2. **All Dates**:
   ```
   - Chọn "Tất cả các ngày"
   - Click "Apply Filters"
   - Verify: Hiện tất cả alerts
   - Verify: Filter tag hiện "Ngày: Tất cả"
   ```

3. **Custom Date Range**:
   ```
   - Chọn "Tùy chọn ngày..."
   - Verify: Date pickers xuất hiện
   - Chọn start_date và end_date
   - Click "Apply Filters"
   - Verify: Chỉ hiện alerts trong khoảng đã chọn
   - Verify: Filter tag hiện "Từ ... Đến ..."
   ```

4. **Real-time Alerts**:
   ```
   - Set filter = "Hôm nay"
   - Verify: Real-time alerts hôm nay được thêm vào
   - Set filter = "Tất cả các ngày"
   - Verify: Real-time alerts được thêm vào
   - Set filter = custom range (tháng trước)
   - Verify: Real-time alerts hôm nay KHÔNG được thêm vào
   ```

5. **Clear Filters**:
   ```
   - Set bất kỳ filter nào
   - Click "Clear All"
   - Verify: Reset về "Hôm nay"
   - Verify: Chỉ hiện alerts hôm nay
   ```

## Performance Considerations

1. **Limit 500 alerts**: API tối đa fetch 500 alerts để tránh overload
2. **Client-side pagination**: 50 alerts/page cho performance tốt
3. **Server-side date filtering**: Giảm data transfer, tăng tốc độ load
4. **Smart filtering**: Real-time alerts chỉ filter client-side khi cần

## Future Enhancements

- [ ] Quick date presets (7 ngày, 30 ngày, tháng này, tháng trước)
- [ ] Calendar UI cho date picker (thay vì HTML5 native)
- [ ] Export alerts theo date range
- [ ] Statistics by date range
- [ ] Auto-refresh với configurable interval

## Rollback Instructions

Nếu cần rollback:
```bash
git revert HEAD
git push
```

Hoặc restore specific files:
- `web/app.py`
- `web/templates/index.html`
- `web/static/js/alerts.js`
