"""
Signal converter - Convert CHoCH detector results to Signal objects
"""
import logging
from datetime import datetime
from typing import Dict, Optional
import pandas as pd

from trading.signal_bus import Signal
from detectors.choch_detector import ChochDetector

logger = logging.getLogger(__name__)


def create_signal_from_choch(
    symbol: str,
    timeframe: str,
    result: Dict,
    detector: ChochDetector
) -> Optional[Signal]:
    """
    Convert CHoCH detector result to Signal object
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        result: CHoCH detection result from detector.process_new_bar()
        detector: ChochDetector instance to get pivot data
    
    Returns:
        Signal object or None if invalid
    """
    try:
        # Check if valid CHoCH signal
        if not (result.get('choch_up') or result.get('choch_down')):
            return None
        
        # Get detector state
        key = f"{symbol}_{timeframe}"
        state = detector.get_state(key)
        
        if state is None or state.pivot_count() < 8:
            logger.warning(f"Cannot create signal: no state or not enough pivots for {key}")
            return None
        
        # Get pivot data
        b8, p8, h8 = state.get_pivot_from_end(0)  # Pivot 8
        b7, p7, h7 = state.get_pivot_from_end(1)
        b6, p6, h6 = state.get_pivot_from_end(2)  # Pivot 6
        b5, p5, h5 = state.get_pivot_from_end(3)  # Pivot 5
        b4, p4, h4 = state.get_pivot_from_end(4)
        
        # Get signal details
        direction = result.get('direction')  # 'Long' or 'Short'
        signal_type = result.get('signal_type')  # 'CHoCH Up' or 'CHoCH Down'
        pattern_group = result.get('pattern_group', 'Unknown')
        choch_price = result.get('price')
        timestamp = result.get('timestamp')
        
        # Convert timestamp if needed
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.to_pydatetime()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()
        
        # Calculate entry/TP/SL levels based on strategy
        # Entry 1 (conservative): CHoCH close price
        # Entry 2 (aggressive): Pivot 6
        # TP: Pivot 5
        # SL: Pivot 8
        
        if direction == 'Long':
            entry1_price = choch_price  # Conservative - closer to TP
            entry2_price = p6  # Aggressive - further from TP (should be high)
            tp_price = p5  # Should be high
            sl_price = p8  # Should be low
            
        else:  # Short
            entry1_price = choch_price  # Conservative - closer to TP
            entry2_price = p6  # Aggressive - further from TP (should be low)
            tp_price = p5  # Should be low
            sl_price = p8  # Should be high
        
        # Create signal
        signal = Signal(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            signal_type=signal_type,
            pattern_group=pattern_group,
            choch_price=choch_price,
            entry1_price=entry1_price,
            entry2_price=entry2_price,
            tp_price=tp_price,
            sl_price=sl_price,
            pivot5=p5,
            pivot6=p6,
            pivot8=p8,
            timestamp=timestamp,
            metadata={
                'pivot4': p4,
                'pivot7': p7,
                'detector_state_key': key
            }
        )
        
        logger.debug(f"Signal created: {symbol} {timeframe} {direction}")
        return signal
    
    except Exception as e:
        logger.error(f"Error creating signal from CHoCH result: {e}", exc_info=True)
        return None
