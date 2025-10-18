"""
Timeframe Scheduler - Manages scan intervals for different timeframes
"""
import logging
from typing import Dict, List
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TimeframeScheduler:
    """
    Manages when each timeframe should be scanned.
    Each timeframe has its own interval and last scan time.
    """
    
    # Convert timeframe to minutes
    TF_TO_MINUTES = {
        '1m': 1,
        '3m': 3,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '2h': 120,
        '4h': 240,
        '6h': 360,
        '8h': 480,
        '12h': 720,
        '1d': 1440,
    }
    
    def __init__(self, timeframes: List[str]):
        """
        Initialize scheduler for given timeframes
        
        Args:
            timeframes: List of timeframe strings (e.g., ['5m', '15m', '1h'])
        """
        self.timeframes = timeframes
        self.last_scan_time: Dict[str, float] = {}  # timeframe -> last scan time (unix timestamp)
        self.intervals: Dict[str, int] = {}  # timeframe -> interval in seconds
        
        # Initialize
        for tf in timeframes:
            self.last_scan_time[tf] = 0  # Never scanned
            minutes = self.TF_TO_MINUTES.get(tf, 60)
            self.intervals[tf] = minutes * 60  # Convert to seconds
            logger.info(f"[Scheduler] {tf}: scan every {minutes} minutes ({self.intervals[tf]}s)")
    
    def should_scan(self, timeframe: str) -> bool:
        """
        Check if a timeframe should be scanned now
        
        Args:
            timeframe: Timeframe to check (e.g., '5m')
        
        Returns:
            True if enough time has passed since last scan, False otherwise
        """
        if timeframe not in self.timeframes:
            logger.warning(f"[Scheduler] Unknown timeframe: {timeframe}")
            return False
        
        now = time.time()
        last_scan = self.last_scan_time.get(timeframe, 0)
        interval = self.intervals.get(timeframe, 300)
        
        # Check if interval has passed
        time_since_scan = now - last_scan
        should_scan = time_since_scan >= interval
        
        return should_scan
    
    def mark_scanned(self, timeframe: str):
        """
        Mark a timeframe as just scanned
        
        Args:
            timeframe: Timeframe that was scanned
        """
        if timeframe in self.timeframes:
            self.last_scan_time[timeframe] = time.time()
            logger.debug(f"[Scheduler] Marked {timeframe} as scanned")
    
    def get_wait_time(self, timeframe: str) -> float:
        """
        Get how long to wait before next scan for a timeframe
        
        Args:
            timeframe: Timeframe to check (e.g., '5m')
        
        Returns:
            Seconds to wait before next scan (0 if should scan now)
        """
        if timeframe not in self.timeframes:
            return 0
        
        now = time.time()
        last_scan = self.last_scan_time.get(timeframe, 0)
        interval = self.intervals.get(timeframe, 300)
        
        time_since_scan = now - last_scan
        wait_time = max(0, interval - time_since_scan)
        
        return wait_time
    
    def get_next_scan_time(self, timeframe: str) -> str:
        """
        Get human-readable next scan time for a timeframe
        
        Args:
            timeframe: Timeframe to check
        
        Returns:
            Human-readable string of next scan time
        """
        wait_time = self.get_wait_time(timeframe)
        next_time = datetime.now() + timedelta(seconds=wait_time)
        return next_time.strftime('%H:%M:%S')
    
    def get_scannable_timeframes(self) -> List[str]:
        """
        Get list of timeframes that should be scanned now
        
        Returns:
            List of timeframe strings ready for scanning
        """
        return [tf for tf in self.timeframes if self.should_scan(tf)]
    
    def get_status_report(self) -> str:
        """
        Get status report for all timeframes
        
        Returns:
            Formatted status string
        """
        report = "[Scheduler Status]\n"
        for tf in self.timeframes:
            wait_time = self.get_wait_time(tf)
            next_scan = self.get_next_scan_time(tf)
            status = "READY" if wait_time == 0 else f"WAIT {wait_time:.0f}s"
            report += f"  {tf:6} → {next_scan}  [{status}]\n"
        return report.rstrip()


# Example usage
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create scheduler
    scheduler = TimeframeScheduler(['5m', '15m', '1h', '4h'])
    
    print(scheduler.get_status_report())
    print()
    
    # Simulate scanning 5m
    print("Scanning 5m...")
    scheduler.mark_scanned('5m')
    
    print(scheduler.get_status_report())
    print()
    
    # Get scannable timeframes
    scannable = scheduler.get_scannable_timeframes()
    print(f"Scannable now: {scannable}")
