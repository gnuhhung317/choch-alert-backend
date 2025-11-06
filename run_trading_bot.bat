@echo off
REM Windows script to run the trading bot

echo ========================================
echo CHoCH Live Trading Bot
echo ========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.trading to .env and configure your API keys
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

REM Install requirements if needed
echo Checking dependencies...
pip install -q -r requirements.txt

echo.
echo ========================================
echo Starting trading bot...
echo Press Ctrl+C to stop
echo ========================================
echo.

REM Run the bot
python trading_bot.py

pause
