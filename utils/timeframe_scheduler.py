"""
Timeframe Scheduler - Manages scan intervals for different timeframes
Aligns with candle close times (e.g., 5m closes at :00, :05, :10, :15, etc.)
"""
import logging
from typing import Dict, List, Optional
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
        '10m': 10,   # Aggregated from 5m
        '15m': 15,
        '20m': 20,   # Aggregated from 5m
        '30m': 30,
        '40m': 40,   # Aggregated from 5m
        '50m': 50,   # Aggregated from 5m
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
        self.last_scanned_close: Dict[str, Optional[datetime]] = {}

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

        if minutes < 60:
            # Minute-based timeframes (5m, 15m, 30m)
            # Find next boundary where minute % minutes == 0 and seconds == 0
            current_minute = now.minute
            next_minute = ((current_minute // minutes) + 1) * minutes
            
            if next_minute >= 60:
                # Roll over to next hour
                next_minute = 0
                next_hour = now.hour + 1
                if next_hour >= 24:
                    # Roll over to next day
                    next_dt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
                else:
                    next_dt = now.replace(hour=next_hour, minute=0, second=0)
            else:
                next_dt = now.replace(minute=next_minute, second=0)
            
            # Safety check: if calculated time is not in future, add one period
            if next_dt <= now:
                next_dt = next_dt + timedelta(minutes=minutes)
            
            return next_dt

        if minutes == 60:
            # Hourly: next hour at :00
            next_hour = (now.hour + 1) % 24
            next_dt = now.replace(hour=next_hour, minute=0, second=0)
            if next_dt <= now:
                next_dt += timedelta(hours=1)
            return next_dt

        if minutes == 1440:
            # Daily: next day at 00:00
            next_dt = now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            return next_dt

        # Multi-hour (e.g., 2h, 4h, 6h, ...)
        hours = minutes // 60
        current_block = (now.hour // hours) * hours
        next_block = current_block + hours
        day_increment = 0
        if next_block >= 24:
            next_block -= 24
            day_increment = 1
        next_dt = now.replace(hour=next_block, minute=0, second=0)
        if day_increment:
            next_dt += timedelta(days=1)
        if next_dt <= now:
            next_dt += timedelta(hours=hours)
        return next_dt

    def get_prev_candle_close_time(self, timeframe: str) -> datetime:
        """
        Get previous candle close time for a timeframe.
        
        FIXED: Calculate actual previous candle close based on current time,
        not just next_close - interval.
        """
        minutes = self.TF_TO_MINUTES.get(timeframe, 60)
        now = datetime.now().replace(microsecond=0)

        if minutes < 60:
            # Minute-based timeframes (5m, 15m, 30m)
            # Find the most recent boundary where minute % minutes == 0
            current_minute_boundary = (now.minute // minutes) * minutes
            prev_close = now.replace(minute=current_minute_boundary, second=0)
            
            # FIXED: Only go back one period if we're EXACTLY at the boundary time
            # (both minute AND second must be 0 for the boundary)
            if prev_close >= now:
                prev_close = prev_close - timedelta(minutes=minutes)
            
            return prev_close

        elif minutes == 60:
            # Hourly: previous hour at :00
            prev_close = now.replace(minute=0, second=0)
            if prev_close >= now:
                prev_close = prev_close - timedelta(hours=1)
            return prev_close

        elif minutes == 1440:
            # Daily: previous day at 00:00
            prev_close = now.replace(hour=0, minute=0, second=0)
            if prev_close >= now:
                prev_close = prev_close - timedelta(days=1)
            return prev_close

        else:
            # Multi-hour (2h, 4h, 6h, etc.)
            hours = minutes // 60
            current_block = (now.hour // hours) * hours
            prev_close = now.replace(hour=current_block, minute=0, second=0)
            
            # FIXED: Only go back one period if we're at or after the boundary
            if prev_close >= now:
                prev_close = prev_close - timedelta(hours=hours)
            
            return prev_close

    def mark_scanned(self, timeframe: str, close_time: Optional[datetime] = None) -> None:
        """Mark a timeframe's candle close as scanned to prevent duplicates."""
        if timeframe not in self.timeframes:
            return
        if close_time is None:
            close_time = self.get_prev_candle_close_time(timeframe)
        self.last_scanned_close[timeframe] = close_time

    def should_scan(self, timeframe: str) -> bool:
        """
        Check if a timeframe should be scanned now.
        Scan right after the previous candle close, and only once per close.
        
        CRITICAL: Add buffer time to ensure the closed candle data is available.
        """
        if timeframe not in self.timeframes:
            logger.warning(f"[Scheduler] Unknown timeframe: {timeframe}")
            return False

        now = datetime.now().replace(microsecond=0)
        prev_close = self.get_prev_candle_close_time(timeframe)

        # Avoid duplicate scans: only scan if we haven't scanned this close yet
        last_scanned = self.last_scanned_close.get(timeframe)
        
        # DEBUG: Log detailed timing info
        logger.debug(f"[Scheduler] {timeframe}: now={now.strftime('%H:%M:%S')}, "
                    f"prev_close={prev_close.strftime('%H:%M:%S')}, "
                    f"last_scanned={last_scanned.strftime('%H:%M:%S') if last_scanned else 'None'}")
        
        if last_scanned is not None and last_scanned >= prev_close:
            logger.debug(f"[Scheduler] {timeframe} SKIP: already scanned this candle close")
            return False

        # ⚠️ CRITICAL FIX: Add 30-second buffer after candle close
        # This ensures the closed candle data is fully available from exchange
        buffer_time = timedelta(seconds=30)
        ready_time = prev_close + buffer_time
        
        # Ready to scan if the candle is closed AND buffer time has passed
        is_ready = now >= ready_time
        
        if is_ready:
            logger.debug(f"[Scheduler] {timeframe} READY: candle closed at {prev_close.strftime('%H:%M:%S')}, "
                        f"buffer passed at {ready_time.strftime('%H:%M:%S')}")
        else:
            wait_seconds = (ready_time - now).total_seconds()
            logger.debug(f"[Scheduler] {timeframe} WAIT: need {wait_seconds:.0f}s more")
        
        return is_ready

    def get_wait_time(self, timeframe: str) -> float:
        """
        Get how long to wait before next candle close for a timeframe
        """
        if timeframe not in self.timeframes:
            return 0.0
        now = datetime.now().replace(microsecond=0)
        next_close = self.get_next_candle_close_time(timeframe)
        wait_time = (next_close - now).total_seconds()
        return max(0.0, wait_time)

    def get_next_scan_time(self, timeframe: str) -> str:
        """Get human-readable next scan time for a timeframe (candle close time)"""
        next_close = self.get_next_candle_close_time(timeframe)
        return next_close.strftime('%H:%M:%S')

    def get_scannable_timeframes(self) -> List[str]:
        """Get list of timeframes that should be scanned now (at candle close)"""
        return [tf for tf in self.timeframes if self.should_scan(tf)]

    def get_status_report(self) -> str:
        """Get status report for all timeframes"""
        report = "[Scheduler Status - Candle Close Times]\n"
        for tf in self.timeframes:
            wait_time = self.get_wait_time(tf)
            next_close = self.get_next_scan_time(tf)
            status = "READY" if self.should_scan(tf) else f"WAIT {wait_time:.0f}s"
            report += f"  {tf:6} → {next_close}  [{status}]\n"
        return report.rstrip()


# Example usage (optional manual test)
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scheduler = TimeframeScheduler(['5m', '15m', '1h', '4h'])
    print(scheduler.get_status_report())
