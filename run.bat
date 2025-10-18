@echo off
REM Quick start script for CHoCH Alert Backend (Windows)

echo ==================================
echo CHoCH Alert Backend Setup
echo ==================================

REM Check Python version
python --version

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo WARNING: Please edit .env file with your credentials:
    echo    - TELEGRAM_BOT_TOKEN
    echo    - TELEGRAM_CHAT_ID
    echo.
    pause
)

REM Run tests
echo Running tests...
pytest tests/ -v

echo.
echo ==================================
echo Setup complete! Starting server...
echo ==================================
echo.

REM Run main application
python main.py

pause
