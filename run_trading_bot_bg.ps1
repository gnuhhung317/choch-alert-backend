# PowerShell script to run trading bot in background (detached mode)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CHoCH Live Trading Bot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path .env)) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.trading to .env and configure your API keys"
    Write-Host ""
    exit 1
}

# Activate virtual environment if it exists
if (Test-Path venv\Scripts\Activate.ps1) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & venv\Scripts\Activate.ps1
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python version: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found! Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Install requirements
Write-Host "Checking dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting trading bot in background..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start bot in background
$process = Start-Process python -ArgumentList "trading_bot.py" -NoNewWindow -PassThru -RedirectStandardOutput "trading_bot.log" -RedirectStandardError "trading_bot_error.log"

Start-Sleep -Seconds 2

if ($process.HasExited) {
    Write-Host "✗ Failed to start trading bot" -ForegroundColor Red
    Write-Host "Check trading_bot_error.log for details" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Trading bot started in background" -ForegroundColor Green
Write-Host "  Process ID: $($process.Id)" -ForegroundColor White
Write-Host "  Log file: trading_bot.log" -ForegroundColor White
Write-Host "  Error log: trading_bot_error.log" -ForegroundColor White
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  Get-Content trading_bot.log -Wait -Tail 50    # View live logs" -ForegroundColor White
Write-Host "  Stop-Process -Id $($process.Id)               # Stop the bot" -ForegroundColor White
Write-Host "  Get-Process | Where-Object {`$_.Name -eq 'python'}  # Check if running" -ForegroundColor White
Write-Host ""

# Save PID to file for stop script
$process.Id | Out-File -FilePath "trading_bot.pid" -Encoding ASCII
Write-Host "PID saved to trading_bot.pid" -ForegroundColor Gray
Write-Host ""
