#!/bin/bash
# View CHoCH Backtest Logs - Linux/Cloud Script
# Shows available logs and monitors them

set -e

echo "========================================"
echo "CHoCH BACKTEST LOGS VIEWER"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

LOG_DIR="logs"

# Find log files
if [ ! -d "$LOG_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Logs directory not found: $LOG_DIR"
    exit 1
fi

LOG_FILES=$(find "$LOG_DIR" -name "backtest_*.log" 2>/dev/null | sort -r)

if [ -z "$LOG_FILES" ]; then
    echo -e "${YELLOW}[INFO]${NC} No log files found in $LOG_DIR/"
    exit 0
fi

# Display available log files
echo -e "${YELLOW}Available log files:${NC}"
echo ""

i=1
declare -a LOG_ARRAY
while IFS= read -r logfile; do
    LOG_ARRAY[$i]="$logfile"
    FILENAME=$(basename "$logfile")
    SIZE=$(du -h "$logfile" | cut -f1)
    MODIFIED=$(date -r "$logfile" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$logfile" 2>/dev/null | cut -d' ' -f1,2)
    
    echo -e "${CYAN}[$i]${NC} $FILENAME"
    echo -e "    ${GRAY}Modified: $MODIFIED${NC}"
    echo -e "    ${GRAY}Size: $SIZE${NC}"
    echo ""
    i=$((i+1))
done <<< "$LOG_FILES"

echo "========================================"
read -p "Select log file number (or 'q' to quit): " choice

if [ "$choice" = "q" ] || [ "$choice" = "Q" ]; then
    exit 0
fi

# Validate choice
if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -ge "$i" ]; then
    echo -e "${RED}[ERROR]${NC} Invalid selection"
    exit 1
fi

SELECTED_LOG="${LOG_ARRAY[$choice]}"

echo ""
echo "========================================"
echo -e "${CYAN}Viewing:${NC} $(basename "$SELECTED_LOG")"
echo "========================================"
echo ""

echo "Action:"
echo "  [1] View last 50 lines"
echo "  [2] Monitor live"
echo "  [3] View full log"
echo "  [4] Search in log"
read -p "Choose action: " action

case "$action" in
    1)
        echo ""
        tail -n 50 "$SELECTED_LOG"
        echo ""
        ;;
    2)
        echo ""
        echo -e "${YELLOW}[INFO]${NC} Monitoring log file... (Press Ctrl+C to stop)"
        echo ""
        tail -f "$SELECTED_LOG"
        ;;
    3)
        echo ""
        less "$SELECTED_LOG"
        ;;
    4)
        read -p "Enter search term: " search_term
        echo ""
        grep --color=always -n "$search_term" "$SELECTED_LOG" || echo -e "${YELLOW}[INFO]${NC} No matches found"
        echo ""
        ;;
    *)
        echo -e "${RED}[ERROR]${NC} Invalid action"
        exit 1
        ;;
esac
