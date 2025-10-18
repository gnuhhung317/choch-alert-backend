# Visualization Guide

## 📊 Tính năng vẽ đồ thị CHoCH

Hệ thống tự động tạo biểu đồ và Pine Script mỗi khi phát hiện CHoCH signal!

## 🎨 Output Files

Khi có CHoCH signal, hệ thống tạo 2 files:

### 1. Chart Image (PNG)
```
charts/BTCUSDT_5m_20251018_130045.png
```
- Candlestick chart với 100 nến gần nhất
- Pivot highs được đánh dấu **▼ (cyan)** và nối với nhau
- Pivot lows được đánh dấu **▲ (yellow)** và nối với nhau
- CHoCH signal được đánh dấu **★** với annotation
- Dark theme, professional styling

### 2. Pine Script (TradingView)
```
charts/BTCUSDT_5m_20251018_130045.pine
```
- Pine Script v5 code
- Vẽ tất cả pivot lines
- Đánh dấu CHoCH signal
- Có thể copy-paste trực tiếp vào TradingView

## 📋 Cách sử dụng Pine Script

### Bước 1: Mở TradingView
1. Truy cập https://www.tradingview.com
2. Mở chart của symbol (ví dụ: BTCUSDT)
3. Chọn đúng timeframe

### Bước 2: Paste Code
1. Click **Pine Editor** (dưới cùng chart)
2. Mở file `.pine` trong folder `charts/`
3. Copy toàn bộ code
4. Paste vào Pine Editor
5. Click **Add to Chart**

### Bước 3: Xem kết quả
- Các pivot points sẽ hiện trên chart
- CHoCH signal được đánh dấu rõ ràng
- So sánh với chart PNG để verify

## 🖼️ Ví dụ Chart

```
Chart Elements:
┌─────────────────────────────────────────────┐
│ BTCUSDT 5m - CHoCH Signal                   │
├─────────────────────────────────────────────┤
│                                             │
│     ▼────────▼  Pivot Highs (cyan)         │
│    /          \                             │
│   /            \         ★ CHoCH Up         │
│  /              \       / $67,450.30        │
│ /                \     /                    │
│                   \   /                     │
│                    \ /                      │
│                     ▲────────▲              │
│              Pivot Lows (yellow)            │
│                                             │
│  Candlesticks (green/red)                  │
│  [100 most recent bars]                    │
└─────────────────────────────────────────────┘
```

## 🔧 Configuration

Trong `config.py` hoặc `.env`:

```python
# Enable/disable chart generation
GENERATE_CHARTS = True

# Chart output directory
CHART_OUTPUT_DIR = "charts"

# Chart resolution (DPI)
CHART_DPI = 100

# Number of candles to display
CHART_CANDLES = 100
```

## 📁 File Structure

```
choch-alert-backend/
├── charts/                          # Auto-generated
│   ├── BTCUSDT_5m_20251018_130045.png
│   ├── BTCUSDT_5m_20251018_130045.pine
│   ├── ETHUSDT_15m_20251018_130123.png
│   └── ETHUSDT_15m_20251018_130123.pine
│
├── visualization/
│   ├── __init__.py
│   └── chart_plotter.py             # Chart generator
│
└── main.py                          # Auto-calls plotter
```

## 🎯 Use Cases

### 1. Verify Signals
- So sánh chart với TradingView
- Kiểm tra pivot placement
- Confirm CHoCH detection

### 2. Historical Analysis
- Review past signals
- Study patterns
- Improve detector parameters

### 3. Documentation
- Share signals with team
- Report to clients
- Track performance

### 4. Debugging
- Visualize pivot logic
- Check detection accuracy
- Fine-tune parameters

## 🚀 Example Workflow

```bash
# 1. Run system
python main.py

# 2. Wait for CHoCH signal
[SIGNAL] CHoCH detected on BTCUSDT 5m: CHoCH Up
[CHART] Saved chart: charts/BTCUSDT_5m_20251018_130045.png
[SCRIPT] Saved Pine Script: charts/BTCUSDT_5m_20251018_130045.pine

# 3. Check chart
open charts/BTCUSDT_5m_20251018_130045.png

# 4. Verify on TradingView
# - Copy content of .pine file
# - Paste to TradingView Pine Editor
# - Add to chart
# - Compare!
```

## 📊 Chart Features

### Candlesticks
- Green: Bullish (close >= open)
- Red: Bearish (close < open)
- Wick shows high/low
- Last 100 candles displayed

### Pivot Points
- **Cyan ▼**: Pivot High
- **Yellow ▲**: Pivot Low
- Dashed lines connect consecutive pivots
- Shows price structure clearly

### CHoCH Signal
- **★** Large star marker
- Color: Green (Up) / Red (Down)
- Annotation box with price
- Arrow pointing to signal bar

### Styling
- Dark background
- High contrast colors
- Professional appearance
- Timestamp on x-axis
- Price on y-axis
- Grid for easy reading

## 💡 Tips

### Best Practices:
1. **Keep charts folder organized** - Delete old charts periodically
2. **Compare with TradingView** - Always verify signals
3. **Study patterns** - Review charts to understand CHoCH better
4. **Share findings** - Use charts in reports/discussions

### Troubleshooting:
- **Chart not generated?** - Check `charts/` folder permissions
- **Pine Script error?** - Make sure TradingView chart matches symbol/timeframe
- **Pivots not showing?** - Ensure chart has enough historical data

## 📝 Future Enhancements

Planned features:
- [ ] Multi-timeframe alignment visualization
- [ ] Volume profile overlay
- [ ] Support/resistance zones
- [ ] Risk/reward visualization
- [ ] Interactive web charts
- [ ] Animated GIF for signal formation
- [ ] PDF report generation
- [ ] Email chart delivery

## 🎨 Customization

Edit `visualization/chart_plotter.py` to customize:
- Colors
- Marker styles
- Annotation format
- Chart size
- Timeframe windows
- Additional indicators

Example:
```python
# Change CHoCH marker
ax.scatter(date, price, 
    color=color, 
    s=500,           # Larger size
    marker='D',      # Diamond instead of star
    alpha=0.8)       # Transparency
```

## 📚 Resources

- [Matplotlib Documentation](https://matplotlib.org)
- [TradingView Pine Script v5](https://www.tradingview.com/pine-script-docs/en/v5/)
- [Candlestick Patterns](https://www.investopedia.com/candlestick-patterns/)

---

**Happy Trading! 📈**
