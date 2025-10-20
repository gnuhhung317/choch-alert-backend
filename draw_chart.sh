#!/bin/bash
# Script để vẽ biểu đồ CHoCH cho symbol cụ thể

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🎨 CHoCH Chart Drawer${NC}"
echo "=================================="

# Check if Python script exists
if [ ! -f "draw_chart.py" ]; then
    echo "❌ draw_chart.py not found!"
    exit 1
fi

# Default values
SYMBOL="JOEUSDT.P"
TIMEFRAME="15m"
BARS="50"

# Parse arguments
if [ $# -ge 1 ]; then
    SYMBOL="$1"
fi

if [ $# -ge 2 ]; then
    TIMEFRAME="$2"
fi

if [ $# -ge 3 ]; then
    BARS="$3"
fi

echo -e "${YELLOW}Symbol:${NC} $SYMBOL"
echo -e "${YELLOW}Timeframe:${NC} $TIMEFRAME"
echo -e "${YELLOW}Bars:${NC} $BARS"
echo "=================================="

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Run the Python script
echo "🚀 Starting chart generation..."
python draw_chart.py "$SYMBOL" "$TIMEFRAME" "$BARS"

# Check if charts directory was created and has files
if [ -d "charts" ]; then
    CHART_COUNT=$(find charts -name "*.png" -newer draw_chart.py 2>/dev/null | wc -l)
    if [ "$CHART_COUNT" -gt 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Chart generated successfully!${NC}"
        echo "📁 Check the 'charts' directory for output files"
        
        # Show recent files
        echo ""
        echo "📊 Recent chart files:"
        find charts -name "*.png" -newer draw_chart.py 2>/dev/null | head -5 | while read file; do
            echo "   📈 $file"
        done
        
        # Show Pine Script files if any
        PINE_COUNT=$(find charts -name "*.pine" -newer draw_chart.py 2>/dev/null | wc -l)
        if [ "$PINE_COUNT" -gt 0 ]; then
            echo ""
            echo "📝 Pine Script files:"
            find charts -name "*.pine" -newer draw_chart.py 2>/dev/null | head -3 | while read file; do
                echo "   📜 $file"
            done
        fi
    fi
fi

echo ""
echo "🎯 Usage examples:"
echo "  ./draw_chart.sh                          # JOEUSDT.P 15m 50 bars"
echo "  ./draw_chart.sh BTCUSDT 1h              # BTCUSDT 1h 50 bars"
echo "  ./draw_chart.sh ETHUSDT 5m 100          # ETHUSDT 5m 100 bars"
echo "  ./draw_chart.sh ADAUSDT.P 30m 75        # ADAUSDT.P 30m 75 bars"