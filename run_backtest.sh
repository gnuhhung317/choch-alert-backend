#!/bin/bash
# CHoCH Backtest Runner - Linux/Cloud Script
# Activates virtual environment and runs backtest in detached mode

set -e  # Exit on error

echo "========================================"
echo "CHoCH BACKTEST - DETACHED MODE (Cloud)"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
VENV_PATH="venv"
SCRIPT_NAME="backtest_bot.py"
LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/backtest_${TIMESTAMP}.log"
PID_FILE="${LOG_DIR}/backtest_${TIMESTAMP}.pid"

# Create logs directory
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo -e "${YELLOW}[INFO]${NC} Created logs directory"
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Python3 is not installed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}[WARNING]${NC} Virtual environment not found at: $VENV_PATH"
    read -p "Create virtual environment now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${CYAN}[INFO]${NC} Creating virtual environment..."
        python3 -m venv "$VENV_PATH"
        echo -e "${GREEN}[OK]${NC} Virtual environment created"
        
        # Activate and install requirements
        source "${VENV_PATH}/bin/activate"
        if [ -f "requirements.txt" ]; then
            echo -e "${CYAN}[INFO]${NC} Installing requirements..."
            pip install -r requirements.txt
            echo -e "${GREEN}[OK]${NC} Requirements installed"
        fi
    else
        echo -e "${RED}[ERROR]${NC} Cannot proceed without virtual environment"
        exit 1
    fi
else
    echo -e "${GREEN}[OK]${NC} Virtual environment found: $VENV_PATH"
fi

# Activate virtual environment
echo -e "${CYAN}[INFO]${NC} Activating virtual environment..."
source "${VENV_PATH}/bin/activate"
echo -e "${GREEN}[OK]${NC} Virtual environment activated"

# Check if Python script exists
if [ ! -f "$SCRIPT_NAME" ]; then
    echo -e "${RED}[ERROR]${NC} Script not found: $SCRIPT_NAME"
    exit 1
fi

# Display Python version
PYTHON_VERSION=$(python --version 2>&1)
echo -e "${CYAN}[INFO]${NC} Python version: $PYTHON_VERSION"
echo ""

# Start backtest in background using nohup
echo -e "${YELLOW}[INFO]${NC} Starting backtest in background..."
echo -e "${CYAN}[INFO]${NC} Log file: $LOG_FILE"
echo ""

nohup python "$SCRIPT_NAME" > "$LOG_FILE" 2>&1 &
PID=$!

# Save PID to file
echo $PID > "$PID_FILE"

# Wait a moment to check if process started successfully
sleep 2

# Check if process is still running
if ps -p $PID > /dev/null; then
    echo "========================================"
    echo -e "${GREEN}[OK] Backtest started successfully!${NC}"
    echo "========================================"
    echo ""
    echo -e "${CYAN}Process ID (PID):${NC} $PID"
    echo -e "${CYAN}Log file:${NC} $LOG_FILE"
    echo -e "${CYAN}PID file:${NC} $PID_FILE"
    echo ""
    echo -e "${YELLOW}To view live logs:${NC}"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo -e "${YELLOW}To stop the backtest:${NC}"
    echo "  kill $PID"
    echo "  OR use: ./stop_backtest.sh"
    echo ""
    echo -e "${YELLOW}To check status:${NC}"
    echo "  ps -p $PID"
    echo ""
    
    # Ask if user wants to monitor logs
    read -p "Monitor logs now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${CYAN}[INFO]${NC} Monitoring logs... (Press Ctrl+C to stop monitoring)"
        echo "========================================"
        echo ""
        tail -f "$LOG_FILE"
    else
        echo ""
        echo -e "${GREEN}[INFO]${NC} Backtest running in background"
        echo -e "${YELLOW}[INFO]${NC} Use the commands above to monitor or stop"
    fi
else
    echo -e "${RED}[ERROR]${NC} Failed to start backtest"
    echo -e "${YELLOW}[INFO]${NC} Check log file: $LOG_FILE"
    exit 1
fi
