#!/bin/bash
# CHoCH Alert System - Cloud Deployment Script
# Runs the application in detached mode with enhanced monitoring and auto-restart

set -e  # Exit on any error

# Configuration
APP_NAME="choch-alert"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root is not recommended for security reasons"
fi

# Create necessary directories
print_info "Setting up directories..."
mkdir -p logs
mkdir -p data/cache
mkdir -p charts

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Install/update requirements
print_info "Checking dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if config file exists
if [ ! -f "config.py" ]; then
    print_error "config.py not found! Please create configuration file first."
    exit 1
fi

# Check if .env file exists (optional)
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Make sure environment variables are set properly."
fi

# Stop existing process if running
print_info "Checking for existing processes..."
if [ -f ".${APP_NAME}.pid" ]; then
    OLD_PID=$(cat ".${APP_NAME}.pid")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        print_warning "Stopping existing process (PID: $OLD_PID)..."
        kill $OLD_PID
        sleep 3
        
        # Force kill if still running
        if ps -p $OLD_PID > /dev/null 2>&1; then
            print_warning "Force killing existing process..."
            kill -9 $OLD_PID
        fi
    fi
    rm -f ".${APP_NAME}.pid"
fi

# Generate log filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/${APP_NAME}_${TIMESTAMP}.log"
ERROR_LOG="logs/${APP_NAME}_error_${TIMESTAMP}.log"

# Create startup info
print_info "Starting CHoCH Alert System..."
echo "Timestamp: $(date)" > "$LOG_FILE"
echo "Script Dir: $SCRIPT_DIR" >> "$LOG_FILE"
echo "Python: $(which python)" >> "$LOG_FILE"
echo "Pip packages:" >> "$LOG_FILE"
pip list >> "$LOG_FILE" 2>&1
echo "===========================================" >> "$LOG_FILE"

# Start the application with nohup and proper logging
print_info "Launching application in detached mode..."

# Use exec to replace the shell with Python process for better signal handling
nohup bash -c "
    cd '$SCRIPT_DIR'
    source venv/bin/activate
    exec python -u main.py
" > "$LOG_FILE" 2> "$ERROR_LOG" &

# Get PID of the background process
PID=$!

# Save PID to file
echo $PID > ".${APP_NAME}.pid"

# Wait a moment to check if process started successfully
sleep 2

if ps -p $PID > /dev/null; then
    print_success "CHoCH Alert System started successfully!"
else
    print_error "Failed to start application. Check logs for details."
    cat "$ERROR_LOG"
    exit 1
fi

# Display process information
echo ""
print_success "=== DEPLOYMENT SUCCESSFUL ==="
echo "Application: CHoCH Alert System"
echo "Process ID: $PID"
echo "Log File: $LOG_FILE"
echo "Error Log: $ERROR_LOG"
echo "PID File: .${APP_NAME}.pid"
echo "Status: Running"
echo ""

print_info "=== USEFUL COMMANDS ==="
echo "View live logs:"
echo "  tail -f $LOG_FILE"
echo ""
echo "View error logs:"
echo "  tail -f $ERROR_LOG"
echo ""
echo "Check process status:"
echo "  ps -p $PID"
echo "  or"
echo "  ./check_status.sh"
echo ""
echo "Stop the application:"
echo "  kill $PID"
echo "  or"
echo "  ./stop_background.sh"
echo ""

# Create a simple status check script
cat > check_status.sh << 'EOF'
#!/bin/bash
APP_NAME="choch-alert"
if [ -f ".${APP_NAME}.pid" ]; then
    PID=$(cat ".${APP_NAME}.pid")
    if ps -p $PID > /dev/null 2>&1; then
        echo "✓ CHoCH Alert System is running (PID: $PID)"
        echo "Uptime: $(ps -o etime= -p $PID | tr -d ' ')"
        echo "Memory: $(ps -o rss= -p $PID | awk '{printf "%.1f MB", $1/1024}')"
        echo "CPU: $(ps -o %cpu= -p $PID | tr -d ' ')%"
    else
        echo "✗ Process not running (PID file exists but process is dead)"
        rm -f ".${APP_NAME}.pid"
    fi
else
    echo "✗ CHoCH Alert System is not running (no PID file found)"
fi
EOF
chmod +x check_status.sh

# Monitor for first few seconds to ensure stability
print_info "Monitoring startup for 10 seconds..."
for i in {1..10}; do
    if ! ps -p $PID > /dev/null; then
        print_error "Application crashed during startup!"
        print_error "Check logs: $LOG_FILE and $ERROR_LOG"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""

print_success "Application is stable and running successfully!"
print_info "The application will continue running in the background."
print_info "Check logs regularly and monitor system resources."

# Show recent log entries
echo ""
print_info "=== RECENT LOG ENTRIES ==="
tail -10 "$LOG_FILE"