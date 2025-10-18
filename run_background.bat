@echo off
REM Run CHoCH Alert System in background (for Windows)

REM Get the directory where this script is located
setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Get current timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set LOG_FILE=logs\choch_alert_%mydate%_%mytime%.log

echo CHoCH Alert System starting in background...
echo Log file: %LOG_FILE%

REM Run Python script in background
start /b pythonw main.py > %LOG_FILE% 2>&1

REM Also save PID to file (if possible)
for /f "tokens=2" %%A in ('tasklist ^| find /i "pythonw"') do (
    echo %%A > .choch_alert.pid
)

echo ✓ CHoCH Alert System started in background
echo.
echo To view logs:
echo   type %LOG_FILE%
echo.
echo To stop the process:
echo   taskkill /IM pythonw.exe /F
echo   or use: stop_background.bat
