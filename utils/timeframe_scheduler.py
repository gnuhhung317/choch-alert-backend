"""
Timeframe Scheduler - Manages scan intervals for different timeframes
Aligns with candle close times (e.g., 5m closes at :00, :05, :10, :15, etc.)
"""
import logging
from typing import Dict, List
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TimeframeScheduler:
    """
    Manages when each timeframe should be scanned.
    Aligns scan times with candle close times for accuracy.
    
    Example:
    - 5m timeframe: scans at :00, :05, :10, :15, :20, etc.
    - 15m timeframe: scans at :00, :15, :30, :45
    - 1h timeframe: scans at :00 of each hour
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
    self.intervals: Dict[str, int] = {}  # timeframe -> interval in seconds
    # Track last scanned candle close time per timeframe to avoid duplicate scans
    self.last_scanned_close: Dict[str, datetime] = {}
        
        # Initialize
    for tf in timeframes:
        minutes = self.TF_TO_MINUTES.get(tf, 60)
        self.intervals[tf] = minutes * 60  # Convert to seconds
        self.last_scanned_close[tf] = None
        logger.info(f"[Scheduler] {tf}: aligned to candle close times (every {minutes}m)")

    def get_next_candle_close_time(self, timeframe: str) -> datetime:
        """
        Calculate the next candle close time for a timeframe.
        
        Examples:
        - 5m at 18:29:45 → next close at 18:30:00
        - 15m at 18:29:45 → next close at 18:30:00 (next 15m boundary)
        - 1h at 18:29:45 → next close at 19:00:00
        
        Args:
            timeframe: Timeframe (e.g., '5m')
        
        Returns:
            datetime object of next candle close time
        """
        minutes = self.TF_TO_MINUTES.get(timeframe, 60)
        now = datetime.now().replace(microsecond=0)
            
            # Calculate next close time based on timeframe interval
        current_minute = now.minute
        current_second = now.second
        
        if minutes == 1:
                # For 1m: close at next minute boundary
                if current_second == 0:
                    next_close = now.replace(second=0, microsecond=0)
                else:
                    next_close = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
            
        elif minutes < 60:
                # For minutes (5m, 15m, 30m, etc.): align to minute boundaries
                # Example: 15m closes at :00, :15, :30, :45
                minutes_elapsed = (current_minute // minutes) * minutes
                next_close_minute = minutes_elapsed + minutes
                
                if next_close_minute >= 60:
                    # Roll over to next hour
                    next_close = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                else:
                    # Same hour
                    next_close = now.replace(minute=next_close_minute, second=0, microsecond=0)
                    # If we're already past this minute's close time (shouldn't happen due to construction), roll
                    if now >= next_close:
                        rolled = now + timedelta(minutes=minutes)
                        next_close = rolled.replace(minute=(rolled.minute // minutes) * minutes, second=0, microsecond=0)
            
        elif minutes == 60:
                # For 1h: close at :00 of next hour
                next_close = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            
        elif minutes == 1440:
                # For 1d: close at 00:00 of next day
                next_close = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
        else:
            # For other intervals (2h, 4h, etc.)
            hours = minutes // 60
            hours_elapsed = (now.hour // hours) * hours
            next_close_hour = hours_elapsed + hours
            
            if next_close_hour >= 24:
                next_close = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                next_close = now.replace(hour=next_close_hour, minute=0, second=0, microsecond=0)
                if now >= next_close:
                    next_close += timedelta(hours=hours)
        
        return next_close

    def get_prev_candle_close_time(self, timeframe: str) -> datetime:
        """Get previous candle close time for a timeframe."""
        next_close = self.get_next_candle_close_time(timeframe)
        return next_close - timedelta(seconds=self.intervals.get(timeframe, 60))
    
    def should_scan(self, timeframe: str) -> bool:
        """
        Check if a timeframe should be scanned now.
        Scans if we're close to or past the candle close time.
        
        Args:
            timeframe: Timeframe to check (e.g., '5m')
        
        Returns:
            True if should scan, False otherwise
        """
        if timeframe not in self.timeframes:
            logger.warning(f"[Scheduler] Unknown timeframe: {timeframe}")
            return False
        
        now = datetime.now().replace(microsecond=0)
        prev_close = self.get_prev_candle_close_time(timeframe)

        # Avoid duplicate scans: only scan if we haven't scanned this close yet
        last_scanned = self.last_scanned_close.get(timeframe)
        if last_scanned is not None and last_scanned >= prev_close:
            return False

        # Ready to scan if the candle is closed (now >= prev_close)
        return now >= prev_close
    
    def get_wait_time(self, timeframe: str) -> float:
        """
        Get how long to wait before next candle close for a timeframe
        
        Args:
            timeframe: Timeframe to check (e.g., '5m')
        
        Returns:
            Seconds to wait until next candle close
        """
        if timeframe not in self.timeframes:
            return 0
        
        now = datetime.now().replace(microsecond=0)
        next_close = self.get_next_candle_close_time(timeframe)
        wait_time = (next_close - now).total_seconds()
        return max(0, wait_time)
    
    def get_next_scan_time(self, timeframe: str) -> str:
        """
        Get human-readable next scan time for a timeframe (candle close time)
        
        Args:
            timeframe: Timeframe to check
        
        Returns:
            Human-readable string of next candle close time
        """
        next_close = self.get_next_candle_close_time(timeframe)
        return next_close.strftime('%H:%M:%S')
    
    def get_scannable_timeframes(self) -> List[str]:
        """
        Get list of timeframes that should be scanned now (at candle close)
        
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
        report = "[Scheduler Status - Candle Close Times]\n"
        for tf in self.timeframes:
            wait_time = self.get_wait_time(tf)
            next_close = self.get_next_scan_time(tf)
            status = "READY" if self.should_scan(tf) else f"WAIT {wait_time:.0f}s"
            report += f"  {tf:6} → {next_close}  [{status}]\n"
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
