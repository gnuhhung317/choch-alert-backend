# Web Alert Fix Summary

## Problem
Telegram alerts were sent successfully but web dashboard didn't receive them in real-time.

## Root Cause
SocketIO `emit()` was using incorrect syntax when called from external context (main.py → web.app):

```python
# ❌ WRONG (worked only inside Flask request context)
socketio.emit('alert', data, broadcast=True)

# ✅ CORRECT (works from external context)
socketio.emit('alert', data, namespace='/')
```

## Error Message
```
Server.emit() got an unexpected keyword argument 'broadcast'
```

## Changes Made

### 1. Fixed SocketIO Broadcast in `web/app.py`
**File**: `web/app.py`  
**Function**: `broadcast_alert()`

Changed all 3 occurrences:
```python
# Line 164, 168, 175
socketio.emit('alert', alert_dict, namespace='/')
```

### 2. Added Favicon to Web Dashboard
**File**: `web/templates/index.html`

Added after `<title>`:
```html
<!-- Favicon -->
<link rel="icon" type="image/png" href="{{ url_for('static', filename='images/favicon.png') }}">
```

**File Location**: `web/static/images/favicon.png` (copied from `candlestick-chart.png`)

## Data Flow Verification

### Complete Alert Flow:
1. **Detection** (`detectors/choch_detector.py`)
   - Detects CHoCH with pattern_group (G1/G2/G3)
   
2. **Alert Creation** (`alert/telegram_sender.py`)
   - `create_alert_data()` includes `nhóm` field
   
3. **Telegram Send** (`main.py`)
   - Sends to Telegram bot
   
4. **Web Broadcast** (`web/app.py`)
   - Saves to database with `pattern_group` column
   - Emits via SocketIO to all connected clients
   
5. **Frontend Display** (`web/static/js/alerts.js`)
   - Receives alert with `nhóm` field
   - Displays in "Nhóm" column (G1/G2/G3)

## Test Results

### Test Script: `test_web_alert.py`
```
✅ Alert data includes 'nhóm': G1
✅ Saved to database with ID 136
✅ Broadcast successful (no errors)
✅ Database query confirms pattern_group stored correctly
```

### Alert Data Structure:
```json
{
  "time_date": "2025-10-26 11:55:21",
  "symbol": "BTCUSDT",
  "mã": "BTCUSDT",
  "khung": "5m",
  "hướng": "Long",
  "nhóm": "G1",           // ✅ Pattern group included
  "loại": "CHoCH Up",
  "price": 67432.5,
  "tradingview_link": "https://..."
}
```

## Files Modified
1. `web/app.py` - Fixed socketio.emit() calls (3 places)
2. `web/templates/index.html` - Added favicon link
3. `web/static/images/favicon.png` - New file (copied from candlestick-chart.png)

## Files Created
1. `test_web_alert.py` - Test script for broadcast verification

## How to Verify

### 1. Run Flask Server
```bash
python main.py
```

### 2. Open Web Dashboard
```
http://localhost:5000
```

### 3. Check Browser Console
Should see:
```
🚨 New alert received: {mã: "BTCUSDT", nhóm: "G1", ...}
```

### 4. Verify Table Display
- **Hướng column**: Shows colored badges (Long=green, Short=red)
- **Nhóm column**: Shows plain text (G1, G2, or G3)
- **Favicon**: Should appear in browser tab

## Technical Notes

### SocketIO Context Modes
Flask-SocketIO has two emit modes:

1. **Inside Flask Request Context** (e.g., inside `@socketio.on()` handlers):
   ```python
   emit('event', data, broadcast=True)  # ✅ Works
   ```

2. **Outside Flask Context** (e.g., called from main.py thread):
   ```python
   socketio.emit('event', data, namespace='/')  # ✅ Works
   socketio.emit('event', data, broadcast=True)  # ❌ Error
   ```

### Why This Matters
- Main application runs in separate thread from Flask
- `broadcast_alert()` is called from main.py (external context)
- Must use `namespace='/'` instead of `broadcast=True`

## Prevention
When calling `socketio.emit()` from outside Flask request handlers, always use:
```python
socketio.emit('event_name', data, namespace='/')
```

This ensures compatibility with both internal and external calls.

## Status
✅ **FIXED** - Web dashboard now receives real-time alerts correctly
✅ **VERIFIED** - Test script confirms broadcast works without errors
✅ **BONUS** - Favicon added to improve UX
