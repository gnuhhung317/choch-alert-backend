# CHoCH Detection Logic - Summary

## Overview
CHoCH (Change of Character) detector sử dụng 8-pivot pattern với 3 nhóm (G1, G2, G3) và xác nhận bằng 3 nến.

## 8-Pivot Pattern Structure

### Cấu trúc xen kẽ
- **Uptrend:** L1 → H2 → L3 → H4 → L5 → H6 → L7 → H8
- **Downtrend:** H1 → L2 → H3 → L4 → H5 → L6 → H7 → L8

### Điều kiện chung
1. **Retest:** P7 phải chạm P4 (lo7 < hi4 hoặc hi7 > lo4)
2. **Extreme:** P8 là cao/thấp nhất trong cụm 1-8
3. **Breakout:** 
   - Uptrend: lo5 > hi2
   - Downtrend: hi5 < lo2

## 3 Nhóm Pattern (G1, G2, G3)

### G1 (Original)
**Uptrend:** `p2 < p4 < p6 < p8` AND `p3 < p5 < p7`  
**Downtrend:** `p3 > p5 > p7` AND `p2 > p4 > p6 > p8`

### G2
**Uptrend:** `p3 < p7 < p5` AND `p2 < p6 < p4 < p8` AND `p2 < p5`  
**Downtrend:** `p3 > p7 > p5` AND `p2 > p6 > p4 > p8` AND `p2 > p5`

### G3
**Uptrend:** `p3 < p5 < p7` AND `p2 < p6 < p4 < p8` AND `p2 < p5`  
**Downtrend:** `p3 > p5 > p7` AND `p2 > p6 > p4 > p8` AND `p2 > p5`

## CHoCH 3-Candle Confirmation

### Timeline
```
[Pre-CHoCH] → [CHoCH Bar] → [Confirmation]
   [2]           [1]            [0]
```

### CHoCH Up (Downtrend → Uptrend)
**CHoCH Bar [1]:**
- `low[1] > low[2]`
- `close[1] > high[2]`
- `pivot6 < close[1] < pivot5`

**Confirmation [0]:**
- `low[0] > high[2]`

### CHoCH Down (Uptrend → Downtrend)
**CHoCH Bar [1]:**
- `high[1] < high[2]`
- `close[1] < low[2]`
- `pivot5 < close[1] < pivot6`

**Confirmation [0]:**
- `high[0] < low[2]`

## Pattern Group Specific Conditions

### Price Conditions (Confirmation Candle)

| Direction | G1 | G2 | G3 |
|-----------|----|----|----| 
| CHoCH Up | `close ≤ p5` | `close ≤ p7` | `close ≤ p5` |
| CHoCH Down | `close ≥ p5` | `close ≥ p7` | `close ≥ p5` |

### Volume Conditions

#### G1 (3 điều kiện - phải thỏa cả 3)
1. **Cụm 678:** `(vol8 OR vol6 OR vol_choch)` là max trong {vol6, vol7, vol8}
2. **Cụm 456:** `(vol4 OR vol6)` là max trong {vol4, vol5, vol6}
3. **Cụm 45678:** `(vol8 OR vol_choch)` là max trong {vol4, vol5, vol6, vol7, vol8}

#### G2 & G3 (1 điều kiện)
- **Cụm 456:** `(vol4 OR vol5 OR vol_choch)` là max trong {vol4, vol5, vol6}

## Final Confirmation Logic

```
IF (baseCondition AND priceCondition AND volumeCondition AND NOT chochLocked)
    THEN fire CHoCH signal
    SET chochLocked = true
```

**Base Condition:**
- CHoCH Up: `lastEightDown AND chochUpBar AND confirmUpBasic`
- CHoCH Down: `lastEightUp AND chochDownBar AND confirmDownBasic`

## Pivot Variants (Required)

Chỉ detect pivot khi match variant patterns:
- **PH1, PH2, PH3:** Pivot High variants
- **PL1, PL2, PL3:** Pivot Low variants

Pivot detection dựa trên triplet [LEFT, CENTER, RIGHT] với điều kiện về high/low.

## Key Features

✅ **Closed Candles Only:** Tất cả logic dựa trên nến đã đóng  
✅ **State Locking:** CHoCH signal chỉ fire 1 lần cho mỗi 8-pivot pattern  
✅ **Fake Pivot Insertion:** Tự động chèn pivot giả khi có 2 pivot liên tiếp cùng loại  
✅ **Multi-Timeframe:** State management độc lập cho từng timeframe  
✅ **Volume Filter:** Lọc signal dựa trên volume tại các pivot quan trọng

## Examples

### G1 CHoCH Up
```
Downtrend pattern detected with p1-p8
→ Nến [1]: close breaks above high[2] (CHoCH)
→ Nến [0]: low > high[2] (Confirmation)
→ close[0] <= p5 (Price condition)
→ Volume checks pass (3 conditions)
→ 🟢 FIRE CHoCH UP
```

### G2 CHoCH Down
```
Uptrend pattern detected with p1-p8
→ Nến [1]: close breaks below low[2] (CHoCH)
→ Nến [0]: high < low[2] (Confirmation)
→ close[0] >= p7 (Price condition)
→ Volume checks pass (1 condition)
→ 🔴 FIRE CHoCH DOWN
```
