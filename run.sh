#!/bin/bash
# Quick start script for CHoCH Alert Backend

echo "=================================="
echo "CHoCH Alert Backend Setup"
echo "=================================="

# Check Python version
python3 --version

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your credentials:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - TELEGRAM_CHAT_ID"
    echo ""
    read -p "Press enter to continue after editing .env..."
fi

# Run tests
echo "Running tests..."
pytest tests/ -v

echo ""
echo "=================================="
echo "Setup complete! Starting server..."
echo "=================================="
echo ""

# Run main application
python main.py
