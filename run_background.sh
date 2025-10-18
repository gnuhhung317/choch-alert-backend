#!/bin/bash
# Run CHoCH Alert System in background (for Linux/macOS)

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Get timestamp for log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/choch_alert_${TIMESTAMP}.log"

# Run the application in background and redirect output to log file
nohup python main.py > "$LOG_FILE" 2>&1 &

# Get the PID of the background process
PID=$!

# Save PID to a file for easy management
echo $PID > .choch_alert.pid

# Print information
echo "CHoCH Alert System started in background"
echo "PID: $PID"
echo "Log file: $LOG_FILE"
echo ""
echo "To view logs:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To stop the process:"
echo "  kill $PID"
echo "  or"
echo "  ./stop_background.sh"
