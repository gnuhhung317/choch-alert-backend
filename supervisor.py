#!/usr/bin/env python
"""
CHoCH Alert System Supervisor - Run and manage the application in background
Can be used for SSH remote execution without terminal
"""
import subprocess
import os
import sys
import time
import signal
import json
from pathlib import Path
from datetime import datetime

class ChochSupervisor:
    """Supervisor for CHoCH Alert System"""
    
    def __init__(self):
        self.pid_file = Path(".choch_alert.pid")
        self.status_file = Path(".choch_alert.status")
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.process = None
    
    def get_log_file(self):
        """Get log file path with timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return self.log_dir / f"choch_alert_{timestamp}.log"
    
    def start(self):
        """Start the application in background"""
        if self.is_running():
            print(f"✗ CHoCH Alert System is already running (PID: {self.get_pid()})")
            return False
        
        log_file = self.get_log_file()
        print(f"Starting CHoCH Alert System...")
        print(f"Log file: {log_file}")
        
        try:
            # Open log file
            with open(log_file, 'w') as logf:
                # Start process
                self.process = subprocess.Popen(
                    [sys.executable, 'main.py'],
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    preexec_fn=os.setpgrp if hasattr(os, 'setpgrp') else None
                )
            
            # Save PID
            self.pid_file.write_text(str(self.process.pid))
            
            # Save status
            status = {
                'pid': self.process.pid,
                'start_time': datetime.now().isoformat(),
                'log_file': str(log_file)
            }
            self.status_file.write_text(json.dumps(status, indent=2))
            
            print(f"✓ CHoCH Alert System started")
            print(f"  PID: {self.process.pid}")
            print(f"  Command: tail -f {log_file}")
            return True
        
        except Exception as e:
            print(f"✗ Failed to start: {e}")
            return False
    
    def stop(self, force=False):
        """Stop the application"""
        pid = self.get_pid()
        if not pid:
            print("✗ No running process found")
            return False
        
        try:
            print(f"Stopping CHoCH Alert System (PID: {pid})...")
            
            if force:
                os.kill(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGTERM)
                # Wait for graceful shutdown
                time.sleep(2)
                
                # Force kill if still running
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            
            # Clean up files
            self.pid_file.unlink(missing_ok=True)
            self.status_file.unlink(missing_ok=True)
            
            print("✓ Process stopped")
            return True
        
        except ProcessLookupError:
            print("✗ Process not found")
            self.pid_file.unlink(missing_ok=True)
            self.status_file.unlink(missing_ok=True)
            return False
        except Exception as e:
            print(f"✗ Error stopping process: {e}")
            return False
    
    def get_pid(self):
        """Get PID from file"""
        if self.pid_file.exists():
            try:
                return int(self.pid_file.read_text().strip())
            except (ValueError, OSError):
                return None
        return None
    
    def is_running(self):
        """Check if process is running"""
        pid = self.get_pid()
        if not pid:
            return False
        
        try:
            os.kill(pid, 0)  # Check if process exists
            return True
        except (OSError, ProcessLookupError):
            self.pid_file.unlink(missing_ok=True)
            self.status_file.unlink(missing_ok=True)
            return False
    
    def status(self):
        """Get status of the application"""
        if self.is_running():
            pid = self.get_pid()
            print(f"✓ CHoCH Alert System is running")
            print(f"  PID: {pid}")
            
            # Try to get status info
            if self.status_file.exists():
                try:
                    status = json.loads(self.status_file.read_text())
                    print(f"  Started: {status.get('start_time')}")
                    print(f"  Log file: {status.get('log_file')}")
                    
                    # Show process info
                    try:
                        result = subprocess.run(
                            ['ps', 'aux'],
                            capture_output=True,
                            text=True
                        )
                        for line in result.stdout.split('\n'):
                            if str(pid) in line:
                                print(f"\nProcess info:")
                                print(f"  {line}")
                                break
                    except:
                        pass
                
                except:
                    pass
        else:
            print("✗ CHoCH Alert System is NOT running")
    
    def logs(self, follow=False, lines=50):
        """Show logs"""
        log_files = sorted(self.log_dir.glob('*.log'), reverse=True)
        
        if not log_files:
            print("✗ No log files found")
            return
        
        latest_log = log_files[0]
        print(f"Latest log file: {latest_log}\n")
        
        if follow:
            # Follow log file (tail -f)
            try:
                subprocess.run(['tail', '-f', str(latest_log)])
            except KeyboardInterrupt:
                print("\nStopped")
        else:
            # Show last N lines
            try:
                subprocess.run(['tail', '-n', str(lines), str(latest_log)])
            except:
                # Fallback if tail is not available
                with open(latest_log) as f:
                    all_lines = f.readlines()
                    for line in all_lines[-lines:]:
                        print(line, end='')


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='CHoCH Alert System Supervisor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python supervisor.py start          # Start the system
  python supervisor.py stop           # Stop the system
  python supervisor.py status         # Check status
  python supervisor.py logs           # Show latest logs
  python supervisor.py logs -f        # Follow logs (tail -f)
  python supervisor.py logs -n 100    # Show last 100 lines
        """
    )
    
    parser.add_argument(
        'command',
        choices=['start', 'stop', 'status', 'logs', 'restart'],
        help='Command to run'
    )
    
    parser.add_argument(
        '-f', '--follow',
        action='store_true',
        help='Follow logs (tail -f)'
    )
    
    parser.add_argument(
        '-n', '--lines',
        type=int,
        default=50,
        help='Number of lines to show (default: 50)'
    )
    
    args = parser.parse_args()
    
    supervisor = ChochSupervisor()
    
    if args.command == 'start':
        supervisor.start()
    elif args.command == 'stop':
        supervisor.stop()
    elif args.command == 'restart':
        supervisor.stop()
        time.sleep(1)
        supervisor.start()
    elif args.command == 'status':
        supervisor.status()
    elif args.command == 'logs':
        supervisor.logs(follow=args.follow, lines=args.lines)


if __name__ == '__main__':
    main()
