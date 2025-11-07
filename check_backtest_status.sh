#!/bin/bash
# Check CHoCH Backtest Status - Linux/Cloud Script
# Checks running backtest processes and shows status

echo "========================================"
echo "CHoCH BACKTEST STATUS"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

LOG_DIR="logs"

# Check for running Python processes
PYTHON_PIDS=$(pgrep -f "python.*backtest_bot.py" 2>/dev/null || true)

if [ -z "$PYTHON_PIDS" ]; then
    echo -e "${YELLOW}[INFO]${NC} No backtest processes currently running"
else
    echo -e "${GREEN}[INFO]${NC} Found running backtest process(es):"
    echo ""
    
    echo "$PYTHON_PIDS" | while read -r pid; do
        if ps -p "$pid" > /dev/null 2>&1; then
            CMD=$(ps -p "$pid" -o cmd= 2>/dev/null || echo "unknown")
            MEM=$(ps -p "$pid" -o rss= 2>/dev/null || echo "0")
            MEM_MB=$((MEM / 1024))
            CPU=$(ps -p "$pid" -o %cpu= 2>/dev/null || echo "0")
            ELAPSED=$(ps -p "$pid" -o etime= 2>/dev/null || echo "unknown")
            
            echo -e "${CYAN}PID:${NC} $pid"
            echo -e "  ${CYAN}CPU:${NC} ${CPU}%"
            echo -e "  ${CYAN}Memory:${NC} ${MEM_MB} MB"
            echo -e "  ${CYAN}Elapsed:${NC} $ELAPSED"
            echo -e "  ${CYAN}Command:${NC} $CMD"
            echo ""
            
            # Find associated log file
            PID_FILE=$(find "$LOG_DIR" -name "backtest_*.pid" -exec grep -l "^${pid}$" {} \; 2>/dev/null | head -n1)
            if [ -n "$PID_FILE" ]; then
                LOG_FILE="${PID_FILE%.pid}.log"
                if [ -f "$LOG_FILE" ]; then
                    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
                    echo -e "  ${CYAN}Log file:${NC} $(basename "$LOG_FILE") (${LOG_SIZE})"
                    
                    # Show last few lines of log
                    echo -e "  ${CYAN}Latest log entries:${NC}"
                    tail -n 3 "$LOG_FILE" | sed 's/^/    /'
                fi
            fi
            echo ""
        fi
    done
fi

echo "========================================"

# Check for recent log files
echo ""
echo -e "${CYAN}Recent log files:${NC}"
RECENT_LOGS=$(find "$LOG_DIR" -name "backtest_*.log" -mmin -60 2>/dev/null | sort -r | head -n 5)

if [ -z "$RECENT_LOGS" ]; then
    echo -e "${YELLOW}[INFO]${NC} No log files modified in the last hour"
else
    echo ""
    while IFS= read -r logfile; do
        FILENAME=$(basename "$logfile")
        SIZE=$(du -h "$logfile" | cut -f1)
        MODIFIED=$(date -r "$logfile" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c %y "$logfile" 2>/dev/null | cut -d' ' -f1,2)
        
        echo -e "  ${CYAN}File:${NC} $FILENAME"
        echo -e "  ${CYAN}Modified:${NC} $MODIFIED | ${CYAN}Size:${NC} $SIZE"
        echo ""
    done <<< "$RECENT_LOGS"
fi

echo "========================================"
echo ""
echo -e "${YELLOW}Commands:${NC}"
echo "  ./view_backtest_logs.sh  - View logs"
echo "  ./stop_backtest.sh       - Stop backtest"
echo "  tail -f logs/backtest_*.log  - Monitor latest log"
