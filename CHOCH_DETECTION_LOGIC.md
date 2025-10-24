# Tổng Hợp Logic Detect CHoCH - Pivot Pattern System

## 📋 Tổng Quan Hệ Thống

Hệ thống phát hiện **CHoCH (Change of Character)** dựa trên **8-pivot pattern** với xác nhận 3 nến đã đóng.

### Quy Trình Chính
```
1. Fetch 50 nến đã đóng → 
2. Rebuild pivots từ đầu → 
3. Phân loại pivot variants → 
4. Chèn fake pivots → 
5. Xác định cụm 8-pivot → 
6. Detect CHoCH → 
7. Xác nhận 3 nến → 
8. Gửi alert
```

---

## 🎯 1. PIVOT DETECTION

### 1.1 Pivot High/Low Detection (Pine Script Logic)
```pine
// TradingView Pine Script
left  = 1  // Số nến bên trái
right = 1  // Số nến bên phải

ph = ta.pivothigh(high, left, right)  // Pivot High
pl = ta.pivotlow(low, left, right)    // Pivot Low

// Pivot được xác định tại: bar_index - right
newPivotBar = (isPH or isPL) ? (bar_index - right) : na
```

### 1.2 Python Implementation
```python
# detectors/choch_detector.py - detect_pivots()

def detect_pivots(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Detect pivot highs and pivot lows
    Returns: (pivot_high_series, pivot_low_series)
    """
    high = df['high']
    low = df['low']
    
    for i in range(self.left, len(df) - self.right):
        # Pivot High: center_high > all left highs AND center_high > all right highs
        center_high = high.iloc[i]
        is_ph = True
        
        # Check left side
        for j in range(i - self.left, i):
            if high.iloc[j] >= center_high:
                is_ph = False
                break
        
        # Check right side
        if is_ph:
            for j in range(i + 1, i + self.right + 1):
                if high.iloc[j] > center_high:
                    is_ph = False
                    break
        
        # Same logic for Pivot Low (opposite comparison)
```

**Điểm Quan Trọng:**
- Pivot được detect tại nến **giữa** (index - right)
- Cần đủ nến 2 bên: `left + 1 + right` bars minimum
- Pivot High: giá cao hơn tất cả nến 2 bên
- Pivot Low: giá thấp hơn tất cả nến 2 bên

---

## 🔍 2. PIVOT VARIANT CLASSIFICATION

### 2.1 Phân Loại 6 Biến Thể

Mỗi pivot được phân loại theo **triplet** (3 nến xung quanh pivot):
```
h1, l1 = Bar trước pivot (left)
h2, l2 = Pivot bar (center)  
h3, l3 = Bar sau pivot (right)
```

#### **Pivot High Variants:**

**PH1** - Standard Bullish Pivot High
```pine
(h2 > h1 AND h2 > h3) AND (l2 > l1 AND l2 > l3)
```
- High của pivot > 2 bên
- Low của pivot cũng > 2 bên
- **Ý nghĩa:** Nến tăng mạnh, cả high lẫn low đều cao hơn

**PH2** - Inside Bar Pivot High  
```pine
(h2 >= h1 AND h2 > h3) AND (l2 > l3 AND l2 < l1)
```
- High ≥ left, > right
- Low nằm giữa (l1 < l2 > l3)
- **Ý nghĩa:** Nến #1 (left) là mẹ, pivot là inside bar

**PH3** - Outside Bar Pivot High
```pine
(h2 > h1 AND h2 >= h3) AND (l2 < l3 AND l2 > l1)
```
- High > left, ≥ right
- Low nằm dưới right nhưng trên left
- **Ý nghĩa:** Biến thể đặc biệt, ít phổ biến

#### **Pivot Low Variants:**

**PL1** - Standard Bearish Pivot Low
```pine
(l2 < l1 AND l2 < l3) AND (h2 < h1 AND h2 < h3)
```
- Low < 2 bên, High cũng < 2 bên
- **Ý nghĩa:** Nến giảm mạnh

**PL2** - Inside Bar Pivot Low
```pine
(h2 >= h1 AND h2 < h3) AND (l2 < l3 AND l2 <= l1)
```
- Low ≤ left, < right
- High nằm giữa
- **Ý nghĩa:** Nến #1 là mẹ

**PL3** - Outside Bar Pivot Low  
```pine
(l2 < l1 AND l2 < l3) AND (h2 < h1 AND h2 > h3)
```
- Low < 2 bên
- High nằm giữa
- **Ý nghĩa:** Biến thể đặc biệt

### 2.2 Filtering Logic
```python
# Python implementation
if use_variant_filter:
    variant = self.classify_variant(df, check_idx, is_high)
    accept = variant != "NA" and self.allow_variants.get(variant, False)
    
    if not accept:
        # Skip this pivot
        continue
```

**Settings:**
- `useVariantFilter = true` → Bật lọc
- `allowPH1/PH2/PH3 = true/false` → Chọn loại cho phép
- `allowPL1/PL2/PL3 = true/false` → Chọn loại cho phép

---

## 🔄 3. FAKE PIVOT INSERTION

### 3.1 Khi Nào Cần Fake Pivot?

**Vấn đề:** Khi 2 pivot liên tiếp cùng loại (2 PH hoặc 2 PL), pattern sẽ sai.

**Giải pháp:** Chèn fake pivot ngược loại vào khoảng trống (gap).

### 3.2 Thuật Toán
```pine
// Pine Script logic
if lastHigh == newHigh  // Cùng loại
    gap = newPivotBar - lastBar - 1
    if gap > 0
        // Tìm extreme trong gap
        firstBarInGap = lastBar + 1
        lastBarInGap  = newPivotBar - 1
        
        // Nếu 2 PH → tìm LOW nhỏ nhất trong gap
        // Nếu 2 PL → tìm HIGH lớn nhất trong gap
        float insertPrice = newHigh ? low[offsetFirst] : high[offsetFirst]
        
        for i = offsetFirst to offsetLast
            candidate = newHigh ? low[i] : high[i]
            if (newHigh and candidate < insertPrice) or 
               (not newHigh and candidate > insertPrice)
                insertPrice := candidate
                insertBar   := bar_index - i
        
        // Chèn fake pivot
        storePivot(insertBar, insertPrice, not newHigh)
```

### 3.3 Python Implementation
```python
def insert_fake_pivot(self, state, df, last_bar, last_price, last_high,
                     new_bar, new_high) -> bool:
    if last_high != new_high:
        return False  # Khác loại → không cần fake
    
    gap = new_bar - last_bar - 1
    if gap <= 0 or gap > 3:  # Only insert for small gaps
        return False
    
    # Find extreme in gap
    gap_df = df.iloc[first_bar_in_gap:last_bar_in_gap + 1]
    
    if new_high:
        # Looking for LOW (opposite)
        insert_idx = gap_df['low'].idxmin()
        insert_price = gap_df.loc[insert_idx, 'low']
    else:
        # Looking for HIGH (opposite)
        insert_idx = gap_df['high'].idxmax()
        insert_price = gap_df.loc[insert_idx, 'high']
    
    state.store_pivot(insert_bar, insert_price, not new_high)
    return True
```

**Giới Hạn:**
- Chỉ chèn nếu gap ≤ 3 bars (tránh fake pivot explosion)
- Chỉ chèn **1 fake pivot** mỗi gap (không chèn nhiều)

---

## 📊 4. 8-PIVOT PATTERN VALIDATION

### 4.1 Cấu Trúc 8-Pivot

**Uptrend Pattern:**
```
P1(L) → P2(H) → P3(L) → P4(H) → P5(L) → P6(H) → P7(L) → P8(H)
```
- Pivot xen kẽ: Low-High-Low-High-Low-High-Low-High
- P8 là đỉnh cao nhất trong cụm 1-8

**Downtrend Pattern:**
```
P1(H) → P2(L) → P3(H) → P4(L) → P5(H) → P6(L) → P7(H) → P8(L)
```
- Pivot xen kẽ: High-Low-High-Low-High-Low-High-Low
- P8 là đáy thấp nhất trong cụm 1-8

### 4.2 Điều Kiện Validation

#### A. Alternating Structure
```python
# Uptrend: Low-High-Low-High-Low-High-Low-High
up_struct = (not h1) and h2 and (not h3) and h4 and (not h5) and h6 and (not h7) and h8

# Downtrend: High-Low-High-Low-High-Low-High-Low  
down_struct = h1 and (not h2) and h3 and (not h4) and h5 and (not h6) and h7 and (not h8)
```

#### B. P7 Retest P4
```python
# Uptrend: low[P7] < high[P4] (P7 chạm/phá vùng P4)
# Downtrend: high[P7] > low[P4]

touch_retest = (up_struct and (lo7 < hi4)) or (down_struct and (hi7 > lo4))
```

**Ý nghĩa:** P7 phải retest lại vùng P4 (tạo cấu trúc sóng hợp lệ).

#### C. P8 Là Extreme
```python
all_prices = [p1, p2, p3, p4, p5, p6, p7, p8]
is_highest8 = p8 == max(all_prices)  # For uptrend
is_lowest8 = p8 == min(all_prices)   # For downtrend
```

#### D. Order Constraints (Higher Highs / Lower Lows)
```python
# Uptrend: HH (P2 < P4 < P6 < P8) + HL (P1 < P3 < P5 < P7)
up_order_ok = (p2 < p4 < p6 < p8) and (p1 < p3 < p5 < p7)

# Downtrend: LH + LL
down_order_ok = (p1 > p3 > p5 > p7) and (p2 > p4 > p6 > p8)
```

#### E. Breakout Conditions
```python
# Uptrend breakout: 
# - low[P5] > high[P2] (P5 breakout khỏi P2)
# - low[P3] > low[P1]  (P3 cao hơn P1)
up_breakout = (lo5 > hi2) and (lo3 > lo1)

# Downtrend breakout:
# - high[P5] < low[P2] (P5 breakdown P2)
# - high[P3] < high[P1] (P3 thấp hơn P1)
down_breakout = (hi5 < lo2) and (hi3 < hi1)
```

### 4.3 Final Validation
```python
# Uptrend pattern CẦN up_breakout conditions
state.last_eight_up = (up_struct and up_order_ok and 
                       touch_retest and is_highest8 and 
                       up_breakout)

# Downtrend pattern CẦN down_breakout conditions
state.last_eight_down = (down_struct and down_order_ok and 
                         touch_retest and is_lowest8 and 
                         down_breakout)

if state.last_eight_up or state.last_eight_down:
    state.pivot5 = p5  # Reference cho CHoCH additional condition
    state.pivot6 = p6  # Reference cho CHoCH main condition
    state.last_eight_bar_idx = b8
```

---

## 🚨 5. CHoCH DETECTION

### 5.1 Điều Kiện CHoCH (3-Candle Logic)

**CHoCH yêu cầu 3 nến ĐÃ ĐÓNG:**
```
[Pre-CHoCH] → [CHoCH Bar] → [Confirmation Bar]
    (n-2)         (n-1)            (n)
```

#### **CHoCH Up** (Bullish Reversal sau Downtrend)
```python
# Nến CHoCH (n-1):
choch_up_bar = (
    prev['low'] > pre_prev['low'] AND          # Low phá cấu trúc
    prev['close'] > pre_prev['high'] AND       # Close vượt high trước đó
    prev['close'] > state.pivot6 AND           # Close > P6 (breakout reference)
    prev['close'] < state.pivot5               # Close < P5 (nằm trong range)
)

# Confirmation (n):
confirm_up = current['low'] > pre_prev['high']  # Low cao hơn high của pre-CHoCH
```

**Pine Script:**
```pine
// CHoCH bar
chochUpBar = (low > low[1]) and (close > high[1]) and 
             (close > pivot6) and (close < pivot5)

baseUp = isAfterEight and lastEightDown and chochUpBar

fireChochUp := (not chochLocked) and baseUp
```

#### **CHoCH Down** (Bearish Reversal sau Uptrend)
```python
# Nến CHoCH (n-1):
choch_down_bar = (
    prev['high'] < pre_prev['high'] AND        # High phá cấu trúc
    prev['close'] < pre_prev['low'] AND        # Close xuống dưới low trước
    prev['close'] < state.pivot6 AND           # Close < P6 (breakdown reference)
    prev['close'] > state.pivot5               # Close > P5 (nằm trong range)
)

# Confirmation (n):
confirm_down = current['high'] < pre_prev['low']  # High thấp hơn low của pre-CHoCH
```

### 5.2 Điều Kiện Bổ Sung

```python
# Must be after 8-pattern
is_after_eight = current_idx > state.last_eight_bar_idx

# Match pattern direction
base_up = is_after_eight and state.last_eight_down and choch_up_bar
base_down = is_after_eight and state.last_eight_up and choch_down_bar

# Check confirmation
fire_up = (not state.choch_locked) and base_up and confirm_up
fire_down = (not state.choch_locked) and base_down and confirm_down
```

### 5.3 CHoCH Locking Mechanism

```python
if fire_up or fire_down:
    state.choch_locked = True  # Lock để tránh duplicate signals
    state.choch_bar_idx = prev_idx  # Lưu bar CHoCH
    state.choch_price = prev['close']  # Lưu giá CHoCH
```

**Unlock khi nào?**
```python
# Khi có pivot mới SAU cụm 8-pattern
if not na(lastEightBarIdx) and newPivotBar > lastEightBarIdx:
    chochLocked := false  # Reset lock
```

---

## 📈 6. QUY TRÌNH XỬ LÝ TOÀN BỘ

### 6.1 Rebuild Pivots (Từ Đầu Mỗi Lần)
```python
def rebuild_pivots(self, timeframe: str, df: pd.DataFrame) -> int:
    """
    Rebuild ALL pivots from fresh 50-bar window
    """
    state = self.get_state(timeframe)
    
    # 1. RESET state (xóa pivots cũ)
    state.reset()
    
    # 2. Detect pivots in entire dataframe
    ph, pl = self.detect_pivots(df)
    
    # 3. Process each pivot
    for check_idx in range(self.left, len(df) - self.right):
        if is_pivot:
            # Variant filtering
            if use_variant_filter:
                variant = classify_variant(df, check_idx, is_high)
                if not allowed:
                    continue
            
            # Insert fake pivot if needed
            if state.pivot_count() > 0:
                insert_fake_pivot(...)
            
            # Store new pivot
            state.store_pivot(pivot_idx, pivot_price, is_high)
    
    # 4. Check 8-pattern
    self.check_eight_pattern(state, df)
    
    return state.pivot_count()
```

### 6.2 Process New Bar (CHoCH Detection)
```python
def process_new_bar(self, timeframe: str, df: pd.DataFrame) -> Dict:
    """
    Detect CHoCH on latest CLOSED bars (3-candle confirmation)
    """
    if len(df) < 3:
        return no_signal
    
    # Current = confirmation bar (CLOSED)
    # Prev = CHoCH bar (CLOSED)
    # Pre-prev = pre-CHoCH bar (CLOSED)
    current_idx = df.index[-1]  # Latest CLOSED bar
    
    fire_up, fire_down = self.check_choch(df, state, current_idx)
    
    if fire_up or fire_down:
        return {
            'signal_type': 'CHoCH Up' if fire_up else 'CHoCH Down',
            'direction': 'Long' if fire_up else 'Short',
            'price': state.choch_price,
            'timestamp': current_idx
        }
    
    return no_signal
```

### 6.3 Main Loop (Real-time Monitoring)
```python
# main.py - mode_realtime()

while True:
    # 1. Fetch 50 CLOSED candles (exclude open candle)
    df = await fetcher.fetch_closed_candles(symbol, timeframe, limit=50)
    
    # 2. Rebuild pivots from scratch
    pivot_count = detector.rebuild_pivots(timeframe, df)
    
    # 3. Check CHoCH (3-candle confirmation)
    result = detector.process_new_bar(timeframe, df)
    
    # 4. Send alert if signal detected
    if result['signal_type']:
        await telegram.send_alert(result)
        await web.broadcast(result)
        await db.save_alert(result)
    
    # 5. Wait for next candle close
    await sleep_until_next_candle_close(timeframe)
```

---

## 🎯 7. CRITICAL DESIGN DECISIONS

### 7.1 CLOSED CANDLES ONLY
```python
# ✅ ĐÚNG: Loại bỏ open candle ở fetcher
df = df[:-1]  # Remove last (open) candle

# ❌ SAI: Sử dụng open candle
df = df  # Include open candle → FALSE SIGNALS
```

**Lý do:** Open candle chưa hoàn thành → giá thay đổi liên tục → CHoCH không xác định.

### 7.2 REBUILD FROM SCRATCH (Không Incremental)
```python
# ✅ ĐÚNG: Reset và rebuild
state.reset()  # Clear old pivots
for pivot in new_df:
    state.store_pivot(...)

# ❌ SAI: Append thêm pivots
for pivot in new_df:
    state.store_pivot(...)  # → Duplicate pivots!
```

**Lý do:** Fetch 50 bars mỗi lần → nếu append sẽ duplicate → pivot count tăng vô hạn.

### 7.3 3-CANDLE CONFIRMATION
```python
# ✅ ĐÚNG: Cần 3 nến đã đóng
pre_prev = df.index[-3]  # Pre-CHoCH
prev = df.index[-2]      # CHoCH
current = df.index[-1]   # Confirmation

# ❌ SAI: CHoCH ngay khi breakout
if close > pivot6:
    fire_choch()  # → Too early, no confirmation!
```

**Lý do:** Confirmation giảm false signals, đảm bảo trend đã chuyển.

### 7.4 FAKE PIVOT LIMIT
```python
# ✅ ĐÚNG: Chỉ chèn nếu gap ≤ 3
if gap <= 3:
    insert_fake_pivot()

# ❌ SAI: Chèn mọi gap
insert_fake_pivot()  # → Pivot explosion!
```

**Lý do:** 50 bars giới hạn → gap lớn = thiếu data → không nên chèn fake.

---

## 📊 8. LOGGING & DEBUGGING

### 8.1 Pivot Detection Logs
```python
logger.info(f"[rebuild_pivots] {len(df)} bars → {total_real_pivots} real → {pivot_after} total")
logger.debug(f"Fake PH inserted @ {insert_price:.6f} in gap of {gap} bars")
```

### 8.2 8-Pattern Validation Logs
```python
logger.info(f"[8-PIVOT] ✓✓✓ VALID UPTREND PATTERN: P1:{p1} → ... → P8:{p8}")
logger.info(f"   Breakout UP: lo5({lo5}) > hi2({hi2}) = {lo5 > hi2}")
```

### 8.3 CHoCH Confirmation Logs
```python
logger.info(f"[CHoCH] ✅ CONFIRMED: UP @ {prev['close']}")
logger.info(f"   CHoCH bar: {prev_idx} (CLOSED)")
logger.info(f"   Pre-CHoCH: {pre_prev_idx} (CLOSED)")
logger.info(f"   Confirm bar: {current_idx} (CLOSED)")
```

---

## 🔧 9. CONFIGURATION

### 9.1 Environment Variables (`config.py`)
```python
SYMBOLS = 'ALL'  # or 'BTCUSDT,ETHUSDT'
TIMEFRAMES = '5m,15m,30m,1h'
ENABLE_CHART = '1'  # Chart generation
USE_VARIANT_FILTER = '1'  # Pivot variant filtering
ALLOW_PH1 = '1'  # Allow PH1 variant
ALLOW_PH2 = '1'  # Allow PH2 variant
# ... etc
```

### 9.2 Pine Script Settings
```pine
// Variant filters
useVariantFilter = input.bool(true, "Lọc theo biến thể")
allowPH1 = input.bool(true, "Cho phép PH loại 1")
allowPH2 = input.bool(true, "Cho phép PH loại 2")
allowPH3 = input.bool(true, "Cho phép PH loại 3")
allowPL1 = input.bool(true, "Cho phép PL loại 1")
allowPL2 = input.bool(true, "Cho phép PL loại 2")
allowPL3 = input.bool(true, "Cho phép PL loại 3")
showVariantLabel = input.bool(false, "Hiển thị mã biến thể")
```

---

## 📝 10. TESTING & VALIDATION

### 10.1 Test Scripts
```bash
# Test CHoCH confirmation logic
python test_choch_confirmation.py

# Test specific scenarios
python test_confirmation_logic.py

# Full test suite
pytest tests/
```

### 10.2 Visual Validation
```bash
# Generate charts for debugging
ENABLE_CHART=1 CHART_MODE=history python main.py

# Compare with Pine Script
# Export to TradingView format in charts/*.pine
```

### 10.3 Key Test Cases
1. **2 Pivot Liên Tiếp Cùng Loại** → Fake pivot inserted
2. **8-Pattern Valid** → P7 retest P4, P8 extreme, order OK
3. **CHoCH + Confirmation** → 3 closed candles required
4. **Variant Filtering** → Only allowed variants stored
5. **Gap > 3 Bars** → No fake pivot inserted

---

## 🎓 11. KEY TAKEAWAYS

### ✅ DO's
1. **Always use CLOSED candles** (exclude open candle)
2. **Rebuild pivots from scratch** each scan (not incremental)
3. **Require 3-candle confirmation** for CHoCH
4. **Filter variants** to reduce noise (PH1/PL1 most reliable)
5. **Limit fake pivots** to gaps ≤ 3 bars
6. **Lock CHoCH** after firing until next pivot
7. **Log extensively** for debugging

### ❌ DON'Ts
1. **Never use open/incomplete candles** → False signals
2. **Don't append pivots** → Duplicate explosion
3. **Don't fire CHoCH without confirmation** → Too many false positives
4. **Don't insert fake pivots in large gaps** → Unreliable
5. **Don't process same CHoCH twice** → Need locking mechanism

---

## 📚 12. FILES REFERENCE

### Core Files
- `detectors/choch_detector.py` - Main detection engine (Python)
- `indicator.pine` - 8-pivot version (Pine Script)
- `source.pine` - 6-pivot version with variants (Pine Script)
- `main.py` - Real-time monitoring loop
- `data/binance_fetcher.py` - Fetch closed candles

### Testing
- `test_choch_confirmation.py` - Test 3-candle logic
- `test_confirmation_logic.py` - Test specific scenarios
- `tests/` - Full test suite

### Visualization
- `visualization/chart_plotter.py` - Chart generation
- `charts/*.pine` - Exported Pine Script for TradingView

---

## 🚀 13. QUICK START

### Run Real-time Monitoring
```powershell
# PowerShell
python main.py
```

### Test CHoCH Logic
```powershell
python test_choch_confirmation.py
```

### Generate Historical Charts
```powershell
$env:CHART_MODE="history"; python main.py
```

### Run in Background
```powershell
.\run_background.bat
```

---

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**Author:** CHoCH Alert Backend Team
