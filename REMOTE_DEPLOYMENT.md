# Running CHoCH Alert System Without Terminal

This guide shows how to run the CHoCH Alert System in the background, ideal for SSH remote servers.

## Quick Start

### Option 1: Using Python Supervisor (Recommended - Cross-platform)

```bash
# Start in background
python supervisor.py start

# Check status
python supervisor.py status

# View logs
python supervisor.py logs

# Follow logs (tail -f)
python supervisor.py logs -f

# Stop
python supervisor.py stop

# Restart
python supervisor.py restart
```

### Option 2: Using Shell Scripts (Linux/macOS)

```bash
# Make scripts executable
chmod +x run_background.sh stop_background.sh check_status.sh

# Start in background
./run_background.sh

# Check status
./check_status.sh

# View latest logs
tail -f logs/choch_alert_*.log

# Stop
./stop_background.sh
```

### Option 3: Using Batch Files (Windows)

```cmd
# Start in background
run_background.bat

# Stop
stop_background.bat

# View logs
type logs\choch_alert_*.log
```

### Option 4: Using Systemd Service (Linux Production)

```bash
# Copy service file to systemd directory
sudo cp choch-alert.service /etc/systemd/system/

# Edit the service file to set correct paths and username
sudo nano /etc/systemd/system/choch-alert.service

# Create log directory
sudo mkdir -p /var/log/choch-alert
sudo chown choch:choch /var/log/choch-alert

# Reload systemd daemon
sudo systemctl daemon-reload

# Start service
sudo systemctl start choch-alert

# Enable auto-start on boot
sudo systemctl enable choch-alert

# Check status
sudo systemctl status choch-alert

# View logs
sudo journalctl -u choch-alert -f
```

## SSH Remote Usage Example

### Setup on Remote Server

```bash
# SSH to remote server
ssh user@your-remote-server.com

# Navigate to application directory
cd ~/choch-alert-backend

# Start application in background
python supervisor.py start

# Check it's running
python supervisor.py status

# View logs
python supervisor.py logs -f

# Logout (Ctrl+D) - application continues running
```

### Checking Status Later

```bash
# SSH to remote server again
ssh user@your-remote-server.com

# Check if still running
python supervisor.py status

# View logs
python supervisor.py logs -n 100
```

## Log Files

Log files are automatically saved to `logs/` directory with timestamp:

```
logs/
├── choch_alert_20251018_120000.log
├── choch_alert_20251018_130000.log
└── choch_alert_20251018_140000.log
```

## Troubleshooting

### Application not starting

```bash
# Check if Python is available
python --version

# Try starting with more verbose output
python -u main.py

# Check for required dependencies
pip install -r requirements.txt
```

### Check running processes

```bash
# Linux/macOS
ps aux | grep main.py

# Windows
tasklist | findstr python
```

### Force stop process

```bash
# Linux/macOS
pkill -9 -f "python main.py"

# Windows
taskkill /IM python.exe /F
```

### View full logs

```bash
# Show last 100 lines
python supervisor.py logs -n 100

# Follow logs in real-time
python supervisor.py logs -f

# Count log entries
wc -l logs/*.log
```

## Best Practices for Remote Servers

### 1. Use Screen/Tmux (Alternative Method)

```bash
# Create a new screen session
screen -S choch

# Inside screen, start the application
python main.py

# Detach: Ctrl+A then D
# Reattach: screen -r choch
```

### 2. Use Nohup (Simple Method)

```bash
# Start with nohup
nohup python main.py > logs/choch_alert.log 2>&1 &

# Get the PID
echo $!

# Kill later
kill <PID>
```

### 3. Monitor with Top

```bash
# While running, check CPU/Memory
top -p $(pgrep -f main.py)
```

### 4. Setup Cron for Auto-restart

```bash
# Edit crontab
crontab -e

# Add this line to check every 5 minutes and restart if dead:
*/5 * * * * cd ~/choch-alert-backend && python supervisor.py status || python supervisor.py start
```

## Configuration Notes

Before running, make sure:

1. ✅ All dependencies are installed: `pip install -r requirements.txt`
2. ✅ Configuration is set in `config.py`
3. ✅ Telegram bot token and chat ID are configured
4. ✅ Binance API credentials are configured
5. ✅ `logs/` directory exists or will be created

## File Overview

| File | Purpose |
|------|---------|
| `supervisor.py` | Python-based supervisor (cross-platform) |
| `run_background.sh` | Shell script to start on Linux/macOS |
| `stop_background.sh` | Shell script to stop on Linux/macOS |
| `check_status.sh` | Shell script to check status |
| `run_background.bat` | Batch script to start on Windows |
| `stop_background.bat` | Batch script to stop on Windows |
| `choch-alert.service` | Systemd service file for production Linux |

## Support

For issues or questions, check:
- `logs/` directory for detailed logs
- Application logs with `python supervisor.py logs -f`
- Application configuration in `config.py`
