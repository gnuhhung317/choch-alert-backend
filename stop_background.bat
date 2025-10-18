@echo off
REM Stop CHoCH Alert System running in background (Windows)

echo Stopping CHoCH Alert System...

REM Method 1: Kill pythonw.exe process
taskkill /IM pythonw.exe /F 2>nul

REM Method 2: Kill python.exe if pythonw not found
if errorlevel 1 (
    taskkill /IM python.exe /FI "WINDOWTITLE eq CHOCH*" /F 2>nul
)

REM Clean up PID file
if exist .choch_alert.pid (
    del .choch_alert.pid
)

echo ✓ Process stopped
