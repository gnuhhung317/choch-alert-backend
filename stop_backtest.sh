#!/bin/bash
# Stop CHoCH Backtest - Linux/Cloud Script
# Stops running backtest processes

set -e

echo "========================================"
echo "STOP CHoCH BACKTEST"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

LOG_DIR="logs"

# Find PID files
PID_FILES=$(find "$LOG_DIR" -name "backtest_*.pid" 2>/dev/null)

if [ -z "$PID_FILES" ]; then
    echo -e "${YELLOW}[INFO]${NC} No PID files found. Searching for Python processes..."
    
    # Try to find Python processes running backtest_bot.py
    PYTHON_PIDS=$(pgrep -f "python.*backtest_bot.py" 2>/dev/null || true)
    
    if [ -n "$PYTHON_PIDS" ]; then
        echo ""
        echo -e "${YELLOW}Found Python processes running backtest:${NC}"
        echo "$PYTHON_PIDS" | while read -r pid; do
            if ps -p "$pid" > /dev/null 2>&1; then
                CMD=$(ps -p "$pid" -o cmd= 2>/dev/null || echo "unknown")
                MEM=$(ps -p "$pid" -o rss= 2>/dev/null || echo "0")
                MEM_MB=$((MEM / 1024))
                echo -e "  ${CYAN}PID:${NC} $pid | ${CYAN}Memory:${NC} ${MEM_MB} MB"
                echo -e "  ${CYAN}Command:${NC} $CMD"
            fi
        done
        echo ""
        read -p "Stop all these processes? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$PYTHON_PIDS" | while read -r pid; do
                if ps -p "$pid" > /dev/null 2>&1; then
                    kill "$pid" 2>/dev/null && echo -e "${GREEN}[OK]${NC} Stopped process $pid" || echo -e "${RED}[ERROR]${NC} Failed to stop process $pid"
                fi
            done
        fi
    else
        echo -e "${YELLOW}[INFO]${NC} No Python backtest processes found"
    fi
else
    echo -e "${YELLOW}[INFO]${NC} Found PID file(s)"
    echo ""
    
    for pid_file in $PID_FILES; do
        if [ -f "$pid_file" ]; then
            PID=$(cat "$pid_file")
            FILENAME=$(basename "$pid_file")
            
            echo -e "${CYAN}Processing PID file:${NC} $FILENAME"
            echo -e "  ${CYAN}PID:${NC} $PID"
            
            # Check if process is still running
            if ps -p "$PID" > /dev/null 2>&1; then
                CMD=$(ps -p "$PID" -o cmd= 2>/dev/null || echo "unknown")
                MEM=$(ps -p "$PID" -o rss= 2>/dev/null || echo "0")
                MEM_MB=$((MEM / 1024))
                
                echo -e "  ${GREEN}Status: Running${NC}"
                echo -e "  ${CYAN}Memory:${NC} ${MEM_MB} MB"
                echo -e "  ${CYAN}Command:${NC} $CMD"
                
                read -p "  Stop this process? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    kill "$PID" 2>/dev/null && echo -e "  ${GREEN}[OK]${NC} Process stopped" || echo -e "  ${RED}[ERROR]${NC} Failed to stop process"
                    
                    # Remove PID file
                    rm -f "$pid_file" && echo -e "  ${GREEN}[OK]${NC} PID file removed"
                fi
            else
                echo -e "  ${RED}Status: Not running${NC}"
                
                # Remove stale PID file
                rm -f "$pid_file" && echo -e "  ${YELLOW}[OK]${NC} Removed stale PID file"
            fi
            echo ""
        fi
    done
fi

echo "========================================"
echo -e "${GREEN}[DONE]${NC}"
echo "========================================"
