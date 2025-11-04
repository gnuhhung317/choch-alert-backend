@echo off
REM CHoCH Backtest Runner - Windows Batch Script
REM Runs backtest in detached mode (background)

echo ========================================
echo CHoCH BACKTEST - DETACHED MODE
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Create logs directory if not exists
if not exist "logs" mkdir logs

REM Set log file with timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"
set "logfile=logs\backtest_%timestamp%.log"

echo [INFO] Starting backtest in background...
echo [INFO] Log file: %logfile%
echo.
echo Press Ctrl+C to stop monitoring (backtest will continue in background)
echo ========================================
echo.

REM Run Python script in background and redirect output to log file
start /B python backtest_bot.py > "%logfile%" 2>&1

REM Get the PID (approximation - Windows doesn't have easy PID capture)
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /NH') do (
    set "PID=%%i"
    goto :found
)
:found

echo [OK] Backtest started in background
if defined PID (
    echo [INFO] Python PID: %PID%
)
echo [INFO] Log file: %logfile%
echo.
echo To view live logs: tail -f %logfile% (if you have Git Bash)
echo Or open the log file in an editor
echo.
echo To stop the backtest:
echo   1. Open Task Manager (Ctrl+Shift+Esc)
echo   2. Find "python.exe" process running backtest_bot.py
echo   3. End the process
echo.

REM Tail the log file if possible (requires tail command)
where tail >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Following log file... (Ctrl+C to stop monitoring)
    tail -f "%logfile%"
) else (
    echo [INFO] 'tail' command not found. Opening log file...
    timeout /t 3 /nobreak >nul
    start notepad "%logfile%"
)

pause
