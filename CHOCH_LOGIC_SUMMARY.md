# CHoCH Detection Logic - Tổng Hợp Dễ Hiểu

## Tổng Quan
CHoCH (Change of Character) là tín hiệu breakout mạnh mẽ trong phân tích kỹ thuật, được phát hiện dựa trên pattern 8 pivot points với các điều kiện giá và volume cụ thể.

## 1. Cấu Trúc 8 Pivot Points

### Pattern Cơ Bản
- **8 điểm pivot** được sắp xếp xen kẽ: High → Low → High → Low → High → Low → High → Low (cho downtrend)
- **Touch/Retest**: Pivot 7 phải chạm lại vùng giá của Pivot 4
- **Extreme**: Pivot 8 phải là điểm cao nhất (uptrend) hoặc thấp nhất (downtrend) trong 8 pivots

### 3 Nhóm Pattern (G1, G2, G3)
Mỗi nhóm có quy tắc sắp xếp thứ tự giá khác nhau:

#### G1 (Original)
- **Uptrend**: P2 < P4 < P6 < P8 và P3 < P5 < P7
- **Downtrend**: P2 > P4 > P6 > P8 và P3 > P5 > P7

#### G2
- **Uptrend**: P3 < P7 < P5, P2 < P6 < P4 < P8, P2 < P5
- **Downtrend**: P3 > P7 > P5, P2 > P6 > P4 > P8, P2 > P5

#### G3
- **Uptrend**: P3 < P5 < P7, P2 < P6 < P4 < P8, P2 < P5
- **Downtrend**: P3 > P5 > P7, P2 > P6 > P4 > P8, P2 > P5

## 2. Điều Kiện Breakout
Trước khi có CHoCH, pattern phải thỏa mãn điều kiện breakout:

### Uptrend Pattern
- Low của nến tại Pivot 5 > High của nến tại Pivot 2

### Downtrend Pattern
- High của nến tại Pivot 5 < Low của nến tại Pivot 2

## 3. Nến CHoCH (Bar Chính)

### CHoCH Up (sau downtrend pattern)
Nến CHoCH phải thỏa mãn **ĐỒNG THỜI** 4 điều kiện:
1. **Low > Low trước đó**: Low của nến CHoCH cao hơn low của nến ngay trước
2. **Close > High trước đó**: Close của nến CHoCH cao hơn high của nến ngay trước
3. **Close > Pivot 6**: Close phá vỡ lên trên pivot 6
4. **Close < Pivot 2**: Close không được vượt quá pivot 2

### CHoCH Down (sau uptrend pattern)
Nến CHoCH phải thỏa mãn **ĐỒNG THỜI** 4 điều kiện:
1. **High < High trước đó**: High của nến CHoCH thấp hơn high của nến ngay trước
2. **Close < Low trước đó**: Close của nến CHoCH thấp hơn low của nến ngay trước
3. **Close < Pivot 6**: Close phá vỡ xuống dưới pivot 6
4. **Close > Pivot 2**: Close không được vượt quá pivot 2

## 4. Nến Confirmation (Xác Nhận)

### Điều Kiện Cơ Bản
- **CHoCH Up**: Low của nến confirmation > High của nến trước CHoCH **VÀ** Close confirmation ≤ Pivot 2
- **CHoCH Down**: High của nến confirmation < Low của nến trước CHoCH **VÀ** Close confirmation ≥ Pivot 2

### Điều Kiện Theo Nhóm Pattern

#### CHoCH Up (từ downtrend)
- **G1**: Close confirmation ≤ High của Pivot 5
- **G2**: Close confirmation ≤ High của Pivot 7
- **G3**: Close confirmation ≤ High của Pivot 5

#### CHoCH Down (từ uptrend)
- **G1**: Close confirmation ≥ Low của Pivot 5
- **G2**: Close confirmation ≥ Low của Pivot 7
- **G3**: Close confirmation ≥ Low của Pivot 5

## 5. Điều Kiện Volume

### G1 (Phức tạp nhất)
Volume của nến CHoCH phải thỏa mãn: **(Điều kiện 678 VÀ Điều kiện 456) HOẶC Điều kiện 45678**

#### Điều kiện 678: Volume lớn nhất trong cụm {Vol6, Vol7, Vol8}
- Vol8 = max(Vol6, Vol7, Vol8), **HOẶC**
- Vol6 = max(Vol6, Vol7, Vol8), **HOẶC**
- Vol_CHoCH = max(Vol6, Vol7, Vol8)

#### Điều kiện 456: Volume lớn nhất trong cụm {Vol4, Vol5, Vol6}
- Vol4 = max(Vol4, Vol5, Vol6), **HOẶC**
- Vol6 = max(Vol4, Vol5, Vol6)

#### Điều kiện 45678: Volume lớn nhất trong cụm {Vol4, Vol5, Vol6, Vol7, Vol8}
- Vol8 = max(Vol4, Vol5, Vol6, Vol7, Vol8), **HOẶC**
- Vol_CHoCH = max(Vol4, Vol5, Vol6, Vol7, Vol8)

### G2 & G3 (Đơn giản hơn)
Volume của nến CHoCH phải là lớn nhất trong cụm {Vol4, Vol5, Vol6}:
- Vol4 = max(Vol4, Vol5, Vol6), **HOẶC**
- Vol5 = max(Vol4, Vol5, Vol6), **HOẶC**
- Vol_CHoCH = max(Vol4, Vol5, Vol6)

## 6. Luồng Phát Hiện

### Thứ Tự Các Bước:
1. **Xây dựng pivots**: Tìm 8 điểm pivot thỏa mãn pattern và variant (PH1/PH2/PH3/PL1/PL2/PL3)
2. **Kiểm tra 8-pattern**: Xác nhận cấu trúc xen kẽ, touch/retest, và breakout
3. **Theo dõi CHoCH**: Sau khi có 8-pattern, chờ nến thỏa mãn điều kiện CHoCH
4. **Xác nhận tín hiệu**: Nến tiếp theo phải thỏa mãn điều kiện confirmation + volume
5. **Khóa tín hiệu**: Mỗi pattern chỉ tạo 1 tín hiệu, không lặp lại

### Điều Kiện Thời Gian:
- **Tất cả nến phải đã đóng**: Không sử dụng nến đang hình thành
- **3 nến liên tiếp**: Pre-CHoCH → CHoCH → Confirmation (đều đã đóng)

## 7. Ý Nghĩa Logic

### Tại Sao CHoCH Quan Trọng:
- **Breakout mạnh**: Vượt qua resistance/support và pivot levels
- **Volume confirmation**: Xác nhận sức mạnh của breakout
- **3-candle confirmation**: Giảm false signals
- **Pattern-specific**: Mỗi nhóm pattern có logic riêng phù hợp

### Risk Management:
- Chỉ trade theo direction của tín hiệu (Long/Short)
- Volume filter giúp loại bỏ breakouts yếu
- Confirmation candle đảm bảo momentum tiếp tục

## 8. Ví Dụ Thực Tế

### CHoCH Up G1:
1. **8-pivot downtrend** được xác nhận
2. **Nến CHoCH**: Low > Low_trước, Close > High_trước, Close > P6, Close < P2
3. **Volume**: Thỏa mãn (678_ok AND 456_ok) OR 45678_ok
4. **Confirmation**: Low_confirmation > High_preCHoCH, Close_confirmation ≤ P2, Close_confirmation ≤ P5
5. **Kết quả**: Tín hiệu Long tại giá Close của nến CHoCH

### CHoCH Down G2:
1. **8-pivot uptrend** được xác nhận
2. **Nến CHoCH**: High < High_trước, Close < Low_trước, Close < P6, Close > P2
3. **Volume**: Vol_CHoCH = max(Vol4, Vol5, Vol6)
4. **Confirmation**: High_confirmation < Low_preCHoCH, Close_confirmation ≥ P2, Close_confirmation ≥ P7
5. **Kết quả**: Tín hiệu Short tại giá Close của nến CHoCH

---

**Tài liệu này giải thích logic CHoCH mà không cần kiến thức lập trình. Tất cả điều kiện đều dựa trên giá, volume và mối quan hệ giữa các nến đã đóng.**
