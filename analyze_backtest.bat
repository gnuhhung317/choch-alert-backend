@echo off
REM Backtest Analysis - Windows Batch Script
REM Runs the backtest analysis tool on CSV summary files

echo ================================================================================
echo BACKTEST ANALYSIS TOOL
echo ================================================================================
echo.

REM Check if file argument provided
if "%1"=="" (
    echo Usage: analyze_backtest.bat [summary_file.csv]
    echo.
    echo Looking for latest backtest summary file...
    echo.
    
    REM Find latest summary file
    for /f "delims=" %%i in ('dir /b /o-d "io\output\backtest_SUMMARY_*.csv" 2^>nul') do (
        set "LATEST=%%i"
        goto :found
    )
    
    echo Error: No backtest summary files found in io\output\
    echo.
    echo Please run backtest_bot.py first to generate data.
    pause
    exit /b 1
    
    :found
    echo Found latest file: %LATEST%
    echo.
    python analyze_backtest.py "io\output\%LATEST%"
) else (
    REM Use provided file
    python analyze_backtest.py "%1"
)

echo.
echo ================================================================================
echo Analysis complete! Check io\output\ for exported files and charts.
echo ================================================================================
pause
