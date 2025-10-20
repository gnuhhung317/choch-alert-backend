#!/bin/bash
# Stop CHoCH Alert System - Cloud Version
# Enhanced stop script with proper cleanup and monitoring

set -e

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

print_info "Stopping CHoCH Alert System..."

# Function to check if process is running
is_process_running() {
    local pid=$1
    ps -p "$pid" > /dev/null 2>&1
}

# Function to get process info
get_process_info() {
    local pid=$1
    if is_process_running "$pid"; then
        local uptime=$(ps -o etime= -p "$pid" | tr -d ' ')
        local memory=$(ps -o rss= -p "$pid" | awk '{printf "%.1f MB", $1/1024}')
        local cpu=$(ps -o %cpu= -p "$pid" | tr -d ' ')
        echo "Uptime: $uptime, Memory: $memory, CPU: ${cpu}%"
    fi
}

# Check if PID file exists
if [ -f ".${APP_NAME}.pid" ]; then
    PID=$(cat ".${APP_NAME}.pid")
    print_info "Found PID file with process ID: $PID"
    
    # Check if process is actually running
    if is_process_running "$PID"; then
        print_info "Process is running. $(get_process_info "$PID")"
        
        # Graceful shutdown first
        print_info "Sending SIGTERM for graceful shutdown..."
        kill -TERM "$PID"
        
        # Wait for graceful shutdown
        print_info "Waiting for graceful shutdown (max 15 seconds)..."
        for i in {1..15}; do
            if ! is_process_running "$PID"; then
                print_success "Process terminated gracefully"
                break
            fi
            echo -n "."
            sleep 1
        done
        echo ""
        
        # Force kill if still running
        if is_process_running "$PID"; then
            print_warning "Process still running. Force killing..."
            kill -KILL "$PID"
            sleep 2
            
            if is_process_running "$PID"; then
                print_error "Failed to kill process $PID"
                exit 1
            else
                print_warning "Process force killed"
            fi
        fi
        
    else
        print_warning "PID file exists but process $PID is not running"
    fi
    
    # Remove PID file
    rm -f ".${APP_NAME}.pid"
    print_success "Cleaned up PID file"
    
else
    print_warning "No PID file found"
    
    # Search for any running CHoCH processes
    print_info "Searching for any running CHoCH processes..."
    
    # Look for main.py processes
    PIDS=$(pgrep -f "python.*main\.py" 2>/dev/null || true)
    
    if [ -n "$PIDS" ]; then
        print_warning "Found running Python processes that might be CHoCH Alert:"
        echo "$PIDS" | while read -r pid; do
            if [ -n "$pid" ]; then
                cmdline=$(ps -p "$pid" -o args= 2>/dev/null || echo "Unknown")
                print_info "PID $pid: $cmdline"
            fi
        done
        
        echo -n "Kill these processes? [y/N] "
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo "$PIDS" | while read -r pid; do
                if [ -n "$pid" ] && is_process_running "$pid"; then
                    print_info "Killing process $pid..."
                    kill -TERM "$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
                fi
            done
            sleep 2
            print_success "Processes terminated"
        else
            print_info "Skipping process termination"
        fi
    else
        print_info "No CHoCH Alert processes found"
    fi
fi

# Additional cleanup
print_info "Performing cleanup tasks..."

# Clean up any stale lock files (if your app uses them)
rm -f .lock 2>/dev/null || true
rm -f *.lock 2>/dev/null || true

# Clean up old log files (keep last 10)
if [ -d "logs" ]; then
    print_info "Cleaning up old log files (keeping last 10)..."
    cd logs
    ls -t ${APP_NAME}_*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
    ls -t ${APP_NAME}_error_*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
    cd ..
fi

# Show final status
print_success "=== SHUTDOWN COMPLETE ==="
print_info "CHoCH Alert System has been stopped"

# Check for any remaining processes
REMAINING=$(pgrep -f "python.*main\.py" 2>/dev/null | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    print_warning "Warning: $REMAINING Python processes still running"
else
    print_success "✓ All processes stopped successfully"
fi

print_info "Cleanup completed. System is ready for restart if needed."