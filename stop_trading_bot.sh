#!/bin/bash
# Script to stop the trading bot

echo "========================================"
echo "Stopping CHoCH Trading Bot"
echo "========================================"
echo ""

# Find trading bot process
BOT_PID=$(ps aux | grep '[p]ython3 trading_bot.py' | awk '{print $2}')

if [ -z "$BOT_PID" ]; then
    echo "✗ Trading bot is not running"
    exit 1
fi

echo "Found trading bot process: PID $BOT_PID"
echo "Stopping..."

# Stop the bot
kill $BOT_PID

# Wait a bit
sleep 2

# Check if stopped
if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "⚠️  Bot still running, force killing..."
    kill -9 $BOT_PID
    sleep 1
fi

if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "✗ Failed to stop bot"
    exit 1
else
    echo "✓ Trading bot stopped successfully"
fi

echo ""
