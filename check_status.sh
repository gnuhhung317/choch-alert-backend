#!/bin/bash
# Check status of CHoCH Alert System

if [ -f .choch_alert.pid ]; then
    PID=$(cat .choch_alert.pid)
    
    if ps -p $PID > /dev/null; then
        echo "✓ CHoCH Alert System is running"
        echo "PID: $PID"
        echo ""
        echo "Process details:"
        ps aux | grep $PID | grep -v grep
        echo ""
        echo "Memory usage:"
        ps -o pid,vsz,rss,comm -p $PID | tail -1
    else
        echo "✗ CHoCH Alert System is NOT running"
        echo "PID file exists but process is dead: $PID"
        rm .choch_alert.pid
    fi
else
    echo "✗ No PID file found. Checking for running processes..."
    if pgrep -f "python main.py" > /dev/null; then
        echo "Found running process:"
        ps aux | grep "python main.py" | grep -v grep
    else
        echo "✗ No running CHoCH Alert System process found"
    fi
fi
