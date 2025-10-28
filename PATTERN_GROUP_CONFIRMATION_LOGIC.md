# Pattern Group Confirmation Logic

## Overview

Đã bổ sung logic xác nhận (confirmation) dựa trên **Pattern Group** (G1, G2, G3) cho nến confirmation trong hệ thống CHoCH Alert.

## Pattern Group Specific Conditions

### Downtrend → CHoCH Up (Đảo chiều lên)

| Pattern Group | Confirmation Condition | Pivot Reference |
|---------------|------------------------|-----------------|
| **G1** | `Close_CF <= HIGH_5` | Pivot 5 (High) |
| **G2** | `Close_CF <= HIGH_7` | Pivot 7 (High) |
| **G3** | `Close_CF <= HIGH_5` | Pivot 5 (High) |

### Uptrend → CHoCH Down (Đảo chiều xuống)

| Pattern Group | Confirmation Condition | Pivot Reference |
|---------------|------------------------|-----------------|
| **G1** | `Close_CF >= LOW_5` | Pivot 5 (Low) |
| **G2** | `Close_CF >= LOW_7` | Pivot 7 (Low) |
| **G3** | `Close_CF >= LOW_5` | Pivot 5 (Low) |

## Logic Flow

### 3-Candle CHoCH Confirmation

```
Pre-CHoCH [2] → CHoCH Bar [1] → Confirmation [0]
```

1. **Pre-CHoCH Bar [2]**: Nến trước khi CHoCH xảy ra
2. **CHoCH Bar [1]**: Nến CHoCH (previous bar)
3. **Confirmation Bar [0]**: Nến xác nhận (current bar)

### CHoCH Bar Conditions (Bar [1])

#### CHoCH Up
```python
low[1] > low[2] AND 
close[1] > high[2] AND 
close[1] > pivot6 AND 
close[1] < pivot5
```

#### CHoCH Down
```python
high[1] < high[2] AND 
close[1] < low[2] AND 
close[1] < pivot6 AND 
close[1] > pivot5
```

### Confirmation Bar Conditions (Bar [0])

#### Basic Confirmation
- **CHoCH Up**: `low[0] > high[2]` (low của nến confirm > high của nến pre-CHoCH)
- **CHoCH Down**: `high[0] < low[2]` (high của nến confirm < low của nến pre-CHoCH)

#### Pattern Group Specific Confirmation

##### Downtrend → CHoCH Up
```python
if pattern_group == "G1":
    confirm_up = close[0] <= p5  # Close_CF <= HIGH_5
elif pattern_group == "G2":
    confirm_up = close[0] <= p7  # Close_CF <= HIGH_7
elif pattern_group == "G3":
    confirm_up = close[0] <= p5  # Close_CF <= HIGH_5
```

##### Uptrend → CHoCH Down
```python
if pattern_group == "G1":
    confirm_down = close[0] >= p5  # Close_CF >= LOW_5
elif pattern_group == "G2":
    confirm_down = close[0] >= p7  # Close_CF >= LOW_7
elif pattern_group == "G3":
    confirm_down = close[0] >= p5  # Close_CF >= LOW_5
```

## Why Different References?

### G2 Uses P7, Others Use P5

- **G2**: Sử dụng P7 vì trong G2, P7 có vai trò đặc biệt trong cấu trúc:
  - Uptrend G2: `p3 < p7 < p5` (P7 nằm giữa P3 và P5)
  - Downtrend G2: `p3 > p7 > p5` (P7 nằm giữa P3 và P5)
  
- **G1, G3**: Sử dụng P5 vì P5 là pivot quan trọng trong cấu trúc của các pattern này:
  - G1: `p3 < p5 < p7` hoặc `p3 > p5 > p7`
  - G3: `p3 < p5 < p7` hoặc `p3 > p5 > p7`

## Example Scenarios

### Example 1: Downtrend → CHoCH Up (G1)

```
Pattern: G1 Downtrend (p3 > p5 > p7)
P5 = 50000 (HIGH)

CHoCH Bar [1]: close = 50500 (CHoCH triggered)
Confirmation Bar [0]: close = 49800

Check: close[0] <= p5?
49800 <= 50000 ✅ CONFIRMED!
```

### Example 2: Downtrend → CHoCH Up (G2)

```
Pattern: G2 Downtrend (p3 > p7 > p5)
P7 = 51000 (HIGH)

CHoCH Bar [1]: close = 51500 (CHoCH triggered)
Confirmation Bar [0]: close = 50800

Check: close[0] <= p7?
50800 <= 51000 ✅ CONFIRMED!
```

### Example 3: Uptrend → CHoCH Down (G1)

```
Pattern: G1 Uptrend (p3 < p5 < p7)
P5 = 52000 (LOW)

CHoCH Bar [1]: close = 51500 (CHoCH triggered)
Confirmation Bar [0]: close = 52200

Check: close[0] >= p5?
52200 >= 52000 ✅ CONFIRMED!
```

## Implementation Files

### Python Backend
- **File**: `detectors/choch_detector.py`
- **Method**: `check_choch()`
- **Changes**: 
  - Lấy 8 pivot prices (p1-p8)
  - Kiểm tra `state.pattern_group`
  - Áp dụng điều kiện theo pattern group
  - Log thông tin pivot reference

### Pine Script
- **File**: `indicator.pine`
- **Changes**:
  - Thêm `var string matchedGroup`
  - Tách `confirmUpBasic` và `confirmDownBasic`
  - Áp dụng pattern group conditions
  - Match logic với Python

## Testing

### Test Cases

1. **G1 CHoCH Up**: Verify `close[0] <= p5`
2. **G2 CHoCH Up**: Verify `close[0] <= p7`
3. **G3 CHoCH Up**: Verify `close[0] <= p5`
4. **G1 CHoCH Down**: Verify `close[0] >= p5`
5. **G2 CHoCH Down**: Verify `close[0] >= p7`
6. **G3 CHoCH Down**: Verify `close[0] >= p5`

### Log Output

Python logs now include pattern group reference:
```
[CHoCH-G1] ✅ CONFIRMED UP @ 50500.00 (Close_CF 49800.00 <= P5 50000.00)
[CHoCH-G2] ✅ CONFIRMED DOWN @ 51500.00 (Close_CF 52200.00 >= P7 51000.00)
```

## Benefits

1. **More Selective**: Chỉ confirm khi nến confirmation nằm trong vùng an toàn
2. **Pattern Specific**: Mỗi pattern group có điều kiện phù hợp
3. **Reduce False Signals**: Lọc các signal yếu
4. **Better Risk Management**: Entry point tốt hơn

## Rollback

Nếu cần rollback về logic cũ (không có pattern group conditions):

```python
# Python: Chỉ cần dùng confirm_up_basic và confirm_down_basic
confirm_up = confirm_up_basic
confirm_down = confirm_down_basic
```

```pine
// Pine Script: Dùng confirmUpBasic và confirmDownBasic trực tiếp
fireChochUp := (not chochLocked) and baseUp
fireChochDn := (not chochLocked) and baseDown
```

## Notes

- ✅ **Backward Compatible**: Logic cũ vẫn hoạt động (basic confirmation)
- ✅ **All Closed Candles**: Tất cả nến đều đã đóng
- ✅ **Python-Pine Sync**: Logic giống nhau hoàn toàn
- ✅ **Logging Enhanced**: Thêm thông tin pivot reference

## Summary

Với logic mới:
- **G2** sử dụng P7 làm reference (vì cấu trúc đặc biệt của G2)
- **G1, G3** sử dụng P5 làm reference
- Confirmation phải thỏa mãn CẢ basic condition VÀ pattern group condition
- System logs hiển thị pattern group và pivot reference rõ ràng
