#!/bin/bash
# Stop CHoCH Alert System running in background

# Check if PID file exists
if [ -f .choch_alert.pid ]; then
    PID=$(cat .choch_alert.pid)
    
    # Check if process is still running
    if ps -p $PID > /dev/null; then
        echo "Stopping CHoCH Alert System (PID: $PID)..."
        kill $PID
        
        # Wait a bit for graceful shutdown
        sleep 2
        
        # Force kill if still running
        if ps -p $PID > /dev/null; then
            echo "Force killing process..."
            kill -9 $PID
        fi
        
        # Remove PID file
        rm .choch_alert.pid
        echo "✓ Process stopped"
    else
        echo "Process with PID $PID is not running"
        rm .choch_alert.pid
    fi
else
    echo "No PID file found. Searching for Python process..."
    pkill -f "python main.py"
    echo "✓ Killed all matching processes"
fi
