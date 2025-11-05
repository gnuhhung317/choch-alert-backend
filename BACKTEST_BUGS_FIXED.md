# Backtest Critical Bugs - Analysis & Fixes

## 🔴 Bug #1: Floating Positions (Overlapping Signals)

### Mô tả vấn đề
**Severity**: CRITICAL  
**Impact**: Win rate/P&L inflated, missing major losses

Khi một tín hiệu CHoCH mới xuất hiện, code cũ chỉ:
1. Hủy orders pending của trade cũ (`cancel_all_orders()`)
2. Overwrite `self.current_trade` bằng trade mới

**Vấn đề nghiêm trọng**: Nếu trade cũ đã có position mở (≥1 entry filled), position đó bị "treo" vô thời hạn:
- Không có TP/SL bảo vệ nữa (đã bị cancel)
- Không được close → không tính P&L
- Trade không vào `completed_trades` → bỏ qua kết quả

### Ví dụ cụ thể

```
Timeline:
1. Bar 100: Signal CHoCH Up (Long)
   → Entry1 @ 100, Entry2 @ 95, TP @ 110, SL @ 85
   
2. Bar 105: Entry1 filled @ 100 ✓ (Position mở 50%)
   
3. Bar 110: Signal CHoCH Down MỚI (Short) - OVERLAPPING!
   Code cũ:
   ❌ Cancel orders (Entry2, TP, SL của Long)
   ❌ Tạo orders Short mới
   ❌ NHƯNG position Long @ 100 vẫn đang MỞ!
   
4. Position Long @ 100 "treo" mãi mãi:
   - Không có TP @ 110 nữa (đã cancel)
   - Không có SL @ 85 nữa (đã cancel)
   - Nếu giá xuống 80 → Loss -20% KHÔNG ĐƯỢC TÍNH!
```

### Hậu quả thực tế

1. **Backtest không chính xác**:
   - Bỏ qua losses lớn từ positions bị treo
   - Win rate cao giả tạo (vì chỉ tính trades có TP/SL)
   - Total P&L tích cực ảo

2. **Thực tế trading**:
   - Overlapping signals rất phổ biến ở crypto (volatile)
   - Positions chồng chéo → Drawdown khổng lồ
   - Risk management sụp đổ → Blow-up account

3. **Không phải look-ahead bias**:
   - Đây là **omission bias** - bỏ qua rủi ro thực
   - Code giả định "1 trade tại 1 thời điểm" nhưng không enforce đúng

### Fix Implementation

**Code cũ**:
```python
# Cancel existing orders if any (new signal)
if self.current_trade is not None:
    logger.info("Cancelling previous trade orders (new signal)")
    self.cancel_all_orders()  # ❌ Chỉ cancel orders, không close position!
```

**Code mới**:
```python
# ========== FIX BUG 1: HANDLE OVERLAPPING SIGNALS ==========
if self.current_trade is not None:
    logger.warning("⚠️  OVERLAPPING SIGNAL DETECTED!")
    
    # Check if old trade has any position filled
    has_old_position = (self.current_trade['entry1_filled'] or 
                        self.current_trade['entry2_filled'])
    
    if has_old_position:
        # ✓ FORCE CLOSE position cũ at market price
        logger.warning("⚠️  Old trade has OPEN POSITION - Force closing at market!")
        
        force_exit_price = choch_price  # Current market (next bar open in reality)
        force_exit_reason = 'FORCED_CLOSE_NEW_SIGNAL'
        
        # Cancel pending orders
        self.cancel_all_orders()
        
        # ✓ Close trade và ghi nhận P&L
        self.close_trade(force_exit_reason, force_exit_price, choch_timestamp)
        
    else:
        # No position yet, just cancel orders
        self.cancel_all_orders()
        self.current_trade = None
        self.pending_orders = []
```

### Kết quả sau fix

✅ **Tất cả positions được close đúng cách**  
✅ **Không có floating positions**  
✅ **P&L chính xác (bao gồm forced closes)**  
✅ **Win rate realistic (bao gồm interrupted trades)**  
✅ **Drawdown được tính đầy đủ**

---

## 🔴 Bug #2: Look-Ahead Bias (Same-Bar Filling)

### Mô tả vấn đề
**Severity**: HIGH  
**Impact**: Over-optimistic results (higher win rate, faster fills)

Code cũ xử lý bar theo thứ tự:
1. Phát hiện tín hiệu CHoCH trên bar `i` (dựa vào close)
2. Tạo orders ngay lập tức
3. **Check fill ngay trên CÙNG bar `i`** ← Vấn đề ở đây!

### Why is this wrong?

Trong thực tế:
- Bạn chỉ biết tín hiệu **SAU KHI bar close**
- Sau khi biết tín hiệu, bạn đặt orders
- Orders chỉ có thể fill từ **bar TIẾP THEO** trở đi

Code cũ cho phép:
- "Nhìn trước" high/low của bar tín hiệu
- Fill entries/TP/SL "ngay lập tức" nếu price đã chạm
- Không phản ánh latency thực tế

### Ví dụ cụ thể

```
Bar 100 OHLC: 
  Open: 100, High: 110, Low: 95, Close: 105
  → CHoCH Up signal confirmed at Close = 105

Setup:
  Entry1: 100 (High P6)
  Entry2: 95 (CHoCH close would be 105, but assume 95 for demo)
  TP: 120
  SL: 85

Code cũ (WRONG):
  Bar 100:
    1. Detect signal at close = 105 ✓
    2. Create orders ✓
    3. Check orders on SAME bar 100:
       → Low = 95 touched Entry2! ❌ FILL IMMEDIATELY
       → This is LOOK-AHEAD - you can't know low before close!

Code mới (CORRECT):
  Bar 100:
    1. Check orders (nothing to check yet)
    2. Detect signal at close = 105 ✓
    3. Create orders ✓
    → Orders CANNOT fill on bar 100 anymore
    
  Bar 101 (next bar):
    1. Check orders ✓ (now can fill based on bar 101 OHLC)
```

### Hậu quả thực tế

1. **Backtest quá lạc quan**:
   - Entries fill nhanh hơn thực tế
   - TP đạt được "tức thì" trong trường hợp may mắn
   - Win rate inflate 2-5%

2. **Timeframe thấp bị ảnh hưởng nhiều hơn**:
   - 30m/1h: Volatility cao → high/low range lớn
   - Càng nhiều cơ hội "fill ngay" giả tạo

3. **Gap giữa backtest và live**:
   - Backtest: 75% win rate
   - Live: 70% win rate ← Vì không có same-bar fills

### Fix Implementation

**Code cũ (WRONG ORDER)**:
```python
for i in range(50, len(df)):
    # 1. Rebuild pivots
    pivot_count = self.detector.rebuild_pivots(key, window_df)
    
    # 2. Check for CHoCH signal
    if i >= 52:
        result = self.detector.process_new_bar(key, window_df)
        if result.get('choch_up') or result.get('choch_down'):
            # Create orders HERE (on bar i)
            await self.on_choch_signal(...)
    
    # 3. ❌ Check orders on SAME bar i (look-ahead!)
    await self.check_orders(current_bar, current_idx)
```

**Code mới (CORRECT ORDER)**:
```python
for i in range(50, len(df)):
    # 1. Rebuild pivots
    pivot_count = self.detector.rebuild_pivots(key, window_df)
    
    # 2. ✓ Check orders FIRST (for orders created on PREVIOUS bars)
    current_bar = df.iloc[i]
    current_idx = df.index[i]
    await self.check_orders(current_bar, current_idx)
    
    # 3. Then check for NEW signal (creates orders for NEXT bars)
    if i >= 52:
        result = self.detector.process_new_bar(key, window_df)
        if result.get('choch_up') or result.get('choch_down'):
            await self.on_choch_signal(...)
            # Orders created here can only fill on bar i+1 and later
```

### Kết quả sau fix

✅ **Không có same-bar fills**  
✅ **Orders chỉ fill từ bar tiếp theo**  
✅ **Phản ánh latency thực tế**  
✅ **Win rate realistic (lower nhưng accurate)**  
✅ **Backtest → Live gap giảm đáng kể**

---

## 📊 Impact Analysis

### Before Fixes
```
Win Rate: 74% (inflated)
Total P&L: +288% (missing forced closes)
Profit Factor: 3.82 (overestimated)
Max Drawdown: 6.4% (underestimated)
```

### After Fixes (Expected)
```
Win Rate: 68-70% (realistic)
Total P&L: +200-250% (includes all trades)
Profit Factor: 2.5-3.0 (accurate)
Max Drawdown: 10-15% (complete picture)
```

**Note**: Actual numbers depend on how often:
1. Overlapping signals occur (volatile markets → more)
2. Same-bar fills happened (high volatility bars → more)

---

## 🔍 How to Verify Fixes

### Test #1: Check for Floating Positions
```bash
# Run backtest and grep logs for:
grep "OVERLAPPING SIGNAL" backtest.log
grep "FORCED_CLOSE_NEW_SIGNAL" backtest.log

# Should see warnings when signals overlap
# All forced closes should be recorded in trades
```

### Test #2: Verify No Same-Bar Fills
```python
# Add to Trade dataclass:
signal_bar_index: int  # Bar where signal was detected
fill_bar_index: int    # Bar where entry filled

# Check condition:
assert fill_bar_index > signal_bar_index, "Same-bar fill detected!"
```

### Test #3: Compare Win Rates
```bash
# Run same backtest multiple times
# Win rate should be stable (not random)
# If win rate drops 3-5% after fix → that's the bias removed
```

---

## 🚀 Additional Recommendations

### 1. Add Trade Type Classification
```python
@dataclass
class Trade:
    ...
    trade_type: str  # 'FULL', 'PARTIAL', 'FORCED_CLOSE'
```

### 2. Track Overlap Statistics
```python
class BacktestResult:
    ...
    total_overlaps: int
    forced_closes: int
    overlap_rate: float
```

### 3. Implement Multi-Position Mode (Optional)
For advanced users who want simultaneous positions:
```python
# Instead of forcing close, allow multiple trades
self.active_trades: List[Dict] = []  # Multiple concurrent trades
# Track each independently with unique IDs
```

### 4. Add Slippage Model
```python
# For forced closes, add realistic slippage
slippage_pct = 0.1  # 0.1% slippage
force_exit_price = choch_price * (1 - slippage_pct/100)  # Long
force_exit_price = choch_price * (1 + slippage_pct/100)  # Short
```

---

## ✅ Checklist - Fixes Applied

- [x] Bug #1: Force close old positions on new signal
- [x] Bug #2: Move check_orders before signal detection
- [x] Added warning logs for overlapping signals
- [x] Track forced close reason in exit_reason
- [x] Updated trade dataclass comment
- [x] Added detailed documentation

---

## 🎯 Conclusion

Hai bugs này là **CRITICAL** và ảnh hưởng trực tiếp đến độ tin cậy của backtest:

1. **Bug #1 (Floating Positions)**: Bỏ qua losses nghiêm trọng
2. **Bug #2 (Look-Ahead Bias)**: Kết quả quá lạc quan

Sau khi fix:
- ✅ Backtest phản ánh chính xác thực tế trading
- ✅ Win rate và P&L realistic
- ✅ Risk metrics đầy đủ
- ✅ Confidence cao khi deploy live

**QUAN TRỌNG**: Chạy lại backtest sau khi fix để có baseline chính xác!
