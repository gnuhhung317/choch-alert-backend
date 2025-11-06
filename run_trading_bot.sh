#!/bin/bash
# Linux/Mac script to run the trading bot

echo "========================================"
echo "CHoCH Live Trading Bot"
echo "========================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.trading to .env and configure your API keys"
    echo ""
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found! Please install Python 3.8+"
    exit 1
fi

# Install requirements if needed
echo "Checking dependencies..."
pip3 install -q -r requirements.txt

echo ""
echo "========================================"
echo "Starting trading bot in background..."
echo "Press Ctrl+C to stop"
echo "========================================"
echo ""

# Run the bot in background (detached mode)
nohup python3 trading_bot.py > trading_bot.log 2>&1 &
BOT_PID=$!

echo "✓ Trading bot started in background"
echo "  PID: $BOT_PID"
echo "  Log file: trading_bot.log"
echo ""
echo "Commands:"
echo "  tail -f trading_bot.log    # View live logs"
echo "  kill $BOT_PID              # Stop the bot"
echo "  ps aux | grep trading_bot  # Check if running"
echo ""
