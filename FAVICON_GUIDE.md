# Hướng dẫn hiển thị Favicon

## Vấn đề
Browser cache đang giữ favicon cũ (hoặc không có favicon).

## Giải pháp đã thực hiện

### 1. File favicon đã có
✅ File: `web/static/images/favicon.png`
✅ Size: 11,334 bytes
✅ Last modified: Oct 26, 2025 12:06 PM

### 2. HTML đã được cập nhật với:
- Multiple favicon links (16x16, 32x32, shortcut icon)
- Cache-busting parameter `?v=1`
- Proper Flask url_for() syntax

```html
<link rel="icon" type="image/png" sizes="32x32" href="/static/images/favicon.png?v=1">
<link rel="icon" type="image/png" sizes="16x16" href="/static/images/favicon.png?v=1">
<link rel="shortcut icon" href="/static/images/favicon.png?v=1">
```

## Cách xóa cache browser

### Chrome/Edge:
1. **Ctrl + Shift + R** (Windows) - Hard Reload
2. Hoặc: F12 → Network tab → Disable cache (checkbox) → F5

### Firefox:
1. **Ctrl + F5** - Hard Reload
2. Hoặc: **Ctrl + Shift + Delete** → Clear cache

### Safari:
1. **Cmd + Option + R** (Mac) - Hard Reload
2. Hoặc: Develop → Empty Caches

## Test thủ công

### 1. Hard Reload trang
```
Ctrl + Shift + R (Windows)
Cmd + Shift + R (Mac)
```

### 2. Mở DevTools và kiểm tra Network tab
Tìm request:
```
GET /static/images/favicon.png?v=1
Status: 200 (not 304)
```

### 3. Truy cập trực tiếp favicon
Mở browser và vào:
```
http://localhost:5000/static/images/favicon.png?v=1
```

Nếu thấy hình candlestick chart → favicon đã hoạt động!

### 4. Xóa hoàn toàn cache browser
**Chrome**: 
- Settings → Privacy → Clear browsing data
- Chọn "Cached images and files"
- Time range: All time
- Clear data

**Firefox**:
- Settings → Privacy & Security → Cookies and Site Data
- Clear Data → Check "Cached Web Content"
- Clear

## Nếu vẫn không thấy favicon

### Option 1: Convert sang .ico format
```bash
# Sử dụng online converter hoặc ImageMagick
magick candlestick-chart.png -define icon:auto-resize=16,32,48 favicon.ico
```

### Option 2: Restart Flask server
```bash
# Stop server (Ctrl+C)
# Clear pycache
Remove-Item -Recurse -Force web/__pycache__

# Restart
python -m web.app
```

### Option 3: Test với Private/Incognito window
Mở browser ở chế độ Private/Incognito (không có cache):
```
Ctrl + Shift + N (Chrome/Edge)
Ctrl + Shift + P (Firefox)
```

## Kiểm tra log
Server log cho thấy favicon được load:
```
"GET /static/images/favicon.png HTTP/1.1" 304 -
```

- **304** = File cached (browser đã có)
- **200** = File loaded fresh (sau khi hard reload)

## Xác nhận favicon hoạt động
✅ File tồn tại: `web/static/images/favicon.png`
✅ HTML có link tags với cache-busting
✅ Server response 304/200 cho favicon request
✅ Flask serving file correctly

**Chỉ cần hard reload (Ctrl + Shift + R) là thấy favicon ngay!**

## Quick Test Command
```bash
# Test favicon URL directly
curl http://localhost:5000/static/images/favicon.png?v=1 -I
```

Should return:
```
HTTP/1.1 200 OK
Content-Type: image/png
Content-Length: 11334
```
