#!/bin/bash
# Script to view trading bot logs

echo "========================================"
echo "CHoCH Trading Bot - Live Logs"
echo "Press Ctrl+C to exit"
echo "========================================"
echo ""

# Check if log file exists
if [ ! -f trading_bot.log ]; then
    echo "✗ Log file not found: trading_bot.log"
    echo "  Bot may not be running yet"
    exit 1
fi

# Check if bot is running
BOT_PID=$(ps aux | grep '[p]ython3 trading_bot.py' | awk '{print $2}')
if [ -z "$BOT_PID" ]; then
    echo "⚠️  Warning: Trading bot is not running"
    echo ""
fi

# Show last 50 lines and follow
tail -n 50 -f trading_bot.log
