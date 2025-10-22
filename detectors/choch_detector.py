"""
CHoCH Detector - Replicates Pine Script logic for CHoCH signal detection
Supports multi-timeframe with per-TF state management
"""
import pandas as pd
import numpy as np
from collections import deque
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class TimeframeState:
    """State management for a single timeframe"""
    
    def __init__(self, left: int, right: int, keep_pivots: int):
        self.left = left
        self.right = right
        self.keep_pivots = keep_pivots
        
        # Pivot storage (matching Pine Script arrays)
        self.prices = deque(maxlen=keep_pivots)
        self.bars = deque(maxlen=keep_pivots)
        self.highs = deque(maxlen=keep_pivots)
        
        # State variables
        self.last_pivot_bar: Optional[int] = None
        self.last_pivot_price: Optional[float] = None
        self.last_eight_up = False
        self.last_eight_down = False
        self.last_eight_bar_idx: Optional[int] = None
        self.pivot6: Optional[float] = None  # Changed from pivot4 to pivot6 for 8-pivot pattern
        self.choch_locked = False
        self.choch_bar_idx: Optional[int] = None  # Bar where CHoCH triggered
        self.choch_price: Optional[float] = None  # Price where CHoCH triggered
        
        # Đơn giản hóa - không cần confirmation tracking
    
    def store_pivot(self, bar: int, price: float, is_high: bool):
        """Store a pivot point"""
        self.bars.append(bar)
        self.prices.append(price)
        self.highs.append(is_high)

    def reset(self):
        """Reset state and clear stored pivots/flags.

        Use this when you want to rebuild pivots from a fresh dataframe
        (e.g. when monitor loop always supplies a full window). This
        prevents duplicate/accumulating pivots across rebuilds.
        """
        self.prices = deque(maxlen=self.keep_pivots)
        self.bars = deque(maxlen=self.keep_pivots)
        self.highs = deque(maxlen=self.keep_pivots)

        self.last_pivot_bar = None
        self.last_pivot_price = None
        self.last_eight_up = False
        self.last_eight_down = False
        self.last_eight_bar_idx = None
        self.pivot6 = None
        self.choch_locked = False
        self.choch_bar_idx = None
        self.choch_price = None
        
        # Đơn giản hóa - không cần reset confirmation fields
    
    def pivot_count(self) -> int:
        """Get number of stored pivots"""
        return len(self.prices)
    
    def get_pivot_from_end(self, idx_from_end: int) -> Tuple[int, float, bool]:
        """Get pivot by index from end (0 = most recent)"""
        idx = len(self.prices) - 1 - idx_from_end
        return self.bars[idx], self.prices[idx], self.highs[idx]


class ChochDetector:
    """Main CHoCH detector with multi-timeframe support"""
    
    def __init__(self, left: int = 1, right: int = 1, keep_pivots: int = 200,
                 use_variant_filter: bool = True,
                 allow_ph1: bool = True, allow_ph2: bool = True, allow_ph3: bool = True,
                 allow_pl1: bool = True, allow_pl2: bool = True, allow_pl3: bool = True):
        
        self.left = left
        self.right = right
        self.keep_pivots = keep_pivots
        self.use_variant_filter = use_variant_filter
        
        self.allow_variants = {
            'PH1': allow_ph1, 'PH2': allow_ph2, 'PH3': allow_ph3,
            'PL1': allow_pl1, 'PL2': allow_pl2, 'PL3': allow_pl3
        }
        
        # Per-timeframe states
        self.states: Dict[str, TimeframeState] = {}
    
    def get_state(self, timeframe: str) -> TimeframeState:
        """Get or create state for a timeframe"""
        if timeframe not in self.states:
            self.states[timeframe] = TimeframeState(self.left, self.right, self.keep_pivots)
        return self.states[timeframe]
    
    def detect_pivots(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Detect pivot highs and pivot lows
        Returns: (pivot_high_series, pivot_low_series)
        """
        high = df['high']
        low = df['low']
        
        # Initialize result series
        ph = pd.Series(index=df.index, dtype=float)
        pl = pd.Series(index=df.index, dtype=float)
        
        # Calculate pivots (need enough bars on both sides)
        window_size = self.left + self.right + 1
        
        for i in range(self.left, len(df) - self.right):
            # Check pivot high
            center_high = high.iloc[i]
            is_ph = True
            
            # Check left side
            for j in range(i - self.left, i):
                if high.iloc[j] >= center_high:
                    is_ph = False
                    break
            
            # Check right side
            if is_ph:
                for j in range(i + 1, i + self.right + 1):
                    if high.iloc[j] > center_high:
                        is_ph = False
                        break
            
            if is_ph:
                ph.iloc[i] = center_high
            
            # Check pivot low
            center_low = low.iloc[i]
            is_pl = True
            
            # Check left side
            for j in range(i - self.left, i):
                if low.iloc[j] <= center_low:
                    is_pl = False
                    break
            
            # Check right side
            if is_pl:
                for j in range(i + 1, i + self.right + 1):
                    if low.iloc[j] < center_low:
                        is_pl = False
                        break
            
            if is_pl:
                pl.iloc[i] = center_low
        
        return ph, pl
    
    def classify_variant(self, df: pd.DataFrame, pivot_idx: int, is_high: bool) -> str:
        """
        Classify pivot variant (PH1/PH2/PH3 or PL1/PL2/PL3)
        Uses triplet around the pivot bar
        
        Pine Script logic:
        - Pivot is detected at bar_index - right
        - Triplet uses: high[right+1], high[right], high[right-1]
        - In Python: pivot_idx is the center, so we use pivot_idx-1, pivot_idx, pivot_idx+1
        """
        # Need bars on both sides
        if pivot_idx < 1 or pivot_idx >= len(df) - 1:
            return "NA"
        
        # Triplet: left(h1), center(h2), right(h3)
        # h1 = bar before pivot (left side)
        # h2 = pivot bar itself (center)
        # h3 = bar after pivot (right side)
        h1 = df['high'].iloc[pivot_idx - 1]
        h2 = df['high'].iloc[pivot_idx]
        h3 = df['high'].iloc[pivot_idx + 1]
        
        l1 = df['low'].iloc[pivot_idx - 1]
        l2 = df['low'].iloc[pivot_idx]
        l3 = df['low'].iloc[pivot_idx + 1]
        
        # Check for NA values
        if pd.isna(h1) or pd.isna(h2) or pd.isna(h3) or pd.isna(l1) or pd.isna(l2) or pd.isna(l3):
            return "NA"
        
        if is_high:
            # PH variants - EXACT Pine Script logic
            # PH1: (h2 > h1 and h2 > h3) and (l2 > l1 and l2 > l3)
            if (h2 > h1 and h2 > h3) and (l2 > l1 and l2 > l3):
                return "PH1"
            # PH2: (h2 >= h1 and h2 > h3) and (l2 > l3 and l2 < l1)
            elif (h2 >= h1 and h2 > h3) and (l2 > l3 and l2 < l1):
                return "PH2"
            # PH3: (h2 > h1 and h2 >= h3) and (l2 < l3 and l2 > l1)
            elif (h2 > h1 and h2 >= h3) and (l2 < l3 and l2 > l1):
                return "PH3"
        else:
            # PL variants - EXACT Pine Script logic
            # PL1: (l2 < l1 and l2 < l3) and (h2 < h1 and h2 < h3)
            if (l2 < l1 and l2 < l3) and (h2 < h1 and h2 < h3):
                return "PL1"
            # PL2: (h2 >= h1 and h2 < h3) and (l2 < l3 and l2 <= l1)
            elif (h2 >= h1 and h2 < h3) and (l2 < l3 and l2 <= l1):
                return "PL2"
            # PL3: (l2 < l1 and l2 < l3) and (h2 < h1 and h2 > h3)
            elif (l2 < l1 and l2 < l3) and (h2 < h1 and h2 > h3):
                return "PL3"
        
        return "NA"
    
    def insert_fake_pivot(self, state: TimeframeState, df: pd.DataFrame, 
                         last_bar: int, last_price: float, last_high: bool,
                         new_bar: int, new_high: bool) -> bool:
        """
        Insert fake pivot if two consecutive pivots are same type
        Returns True if pivot was inserted
        
        IMPORTANT: Only insert ONE fake pivot per gap, even if gap has multiple extremes.
        This prevents fake pivot explosion when reconstructing from limited bars.
        """
        if last_high != new_high:
            return False
        
        # Convert timestamps to integer positions if needed
        if isinstance(new_bar, pd.Timestamp) and isinstance(last_bar, pd.Timestamp):
            # Find positions in dataframe
            try:
                new_bar_pos = df.index.get_loc(new_bar)
                last_bar_pos = df.index.get_loc(last_bar)
                gap = new_bar_pos - last_bar_pos - 1
            except KeyError:
                return False
        else:
            gap = new_bar - last_bar - 1
            new_bar_pos = new_bar
            last_bar_pos = last_bar
        
        if gap <= 0:
            return False
        
        # Only insert if gap is small (1-3 bars)
        # This prevents fake pivot explosion in limited dataframes
        # When gap > 3, we skip fake pivot to keep count reasonable
        if gap > 3:
            logger.debug(f"Gap too large ({gap} bars), skipping fake pivot")
            return False
        
        # Find extreme in gap using integer positions
        first_bar_in_gap = last_bar_pos + 1
        last_bar_in_gap = new_bar_pos - 1
        
        # Map to dataframe indices
        try:
            gap_df = df.iloc[first_bar_in_gap:last_bar_in_gap + 1]
            
            if len(gap_df) == 0:
                return False
            
            if new_high:
                # Looking for low (opposite of the consecutive high)
                insert_idx = gap_df['low'].idxmin()
                insert_price = gap_df.loc[insert_idx, 'low']
            else:
                # Looking for high (opposite of the consecutive low)
                insert_idx = gap_df['high'].idxmax()
                insert_price = gap_df.loc[insert_idx, 'high']
            
            insert_bar = insert_idx
            insert_high = not new_high
            
            # Validate: fake pivot must be between last and new pivot
            if insert_bar > last_bar and insert_bar < new_bar:
                state.store_pivot(insert_bar, insert_price, insert_high)
                state.last_pivot_bar = insert_bar
                state.last_pivot_price = insert_price
                logger.debug(f"Fake {'PH' if insert_high else 'PL'} inserted @ {insert_price:.6f} in gap of {gap} bars")
                return True
        
        except (KeyError, IndexError) as e:
            logger.debug(f"Error inserting fake pivot: {e}")
        
        return False
    
    def check_eight_pattern(self, state: TimeframeState, df: pd.DataFrame) -> bool:
        """
        Check for valid 8-pivot pattern
        Returns True if pattern is valid and updates state
        """
        if state.pivot_count() < 8:
            return False
        
        # Get last 8 pivots
        b8, p8, h8 = state.get_pivot_from_end(0)
        b7, p7, h7 = state.get_pivot_from_end(1)
        b6, p6, h6 = state.get_pivot_from_end(2)
        b5, p5, h5 = state.get_pivot_from_end(3)
        b4, p4, h4 = state.get_pivot_from_end(4)
        b3, p3, h3 = state.get_pivot_from_end(5)
        b2, p2, h2 = state.get_pivot_from_end(6)
        b1, p1, h1 = state.get_pivot_from_end(7)
        
        # Check alternating structure for 8 pivots
        up_struct = (not h1) and h2 and (not h3) and h4 and (not h5) and h6 and (not h7) and h8
        down_struct = h1 and (not h2) and h3 and (not h4) and h5 and (not h6) and h7 and (not h8)
        
        if not (up_struct or down_struct):
            return False
        
        # Check P7 retest P4 (for 8-pivot pattern)
        try:
            hi7 = df.loc[b7, 'high']
            lo7 = df.loc[b7, 'low']
            hi4 = df.loc[b4, 'high']
            lo4 = df.loc[b4, 'low']
            
            touch_retest = (up_struct and (lo7 < hi4)) or (down_struct and (hi7 > lo4))
            
            if not touch_retest:
                return False
        except KeyError:
            return False
        
        # Check P8 is extreme
        all_prices = [p1, p2, p3, p4, p5, p6, p7, p8]
        is_highest8 = p8 == max(all_prices)
        is_lowest8 = p8 == min(all_prices)
        
        # Check order constraints for 8-pivot pattern
        up_order_ok = (p2 < p4 < p6 < p8) and (p1 < p3 < p5 < p7)
        down_order_ok = (p1 > p3 > p5 > p7) and (p2 > p4 > p6 > p8)
        
        # Additional breakout conditions for 8-pivot pattern
        try:
            # For uptrend: low[5] > high[2] and low[3] > low[1]
            lo5 = df.loc[b5, 'low']
            hi2 = df.loc[b2, 'high']
            lo3 = df.loc[b3, 'low']
            lo1 = df.loc[b1, 'low']
            
            # For downtrend: high[5] < low[2] and high[3] < high[1]
            hi5 = df.loc[b5, 'high']
            lo2 = df.loc[b2, 'low']
            hi3 = df.loc[b3, 'high']
            hi1 = df.loc[b1, 'high']
            
            up_breakout = (lo5 > hi2) and (lo3 > lo1)
            down_breakout = (hi5 < lo2) and (hi3 < hi1)
            
        except KeyError:
            up_breakout = False
            down_breakout = False
        
        # Validate pattern
        old_eight_up = state.last_eight_up
        old_eight_down = state.last_eight_down
        
        state.last_eight_up = up_struct and up_order_ok and touch_retest and is_highest8 and up_breakout
        state.last_eight_down = down_struct and down_order_ok and touch_retest and is_lowest8 and down_breakout
        
        if state.last_eight_up or state.last_eight_down:
            state.pivot6 = p6  # Reference pivot for CHoCH (was p4 in 6-pivot pattern)
            state.last_eight_bar_idx = b8
            
            if state.last_eight_up:
                logger.info(f"[8-PIVOT] ✓✓✓ VALID UPTREND: P1:{p1:.6f}(L) -> P2:{p2:.6f}(H) -> P3:{p3:.6f}(L) -> P4:{p4:.6f}(H) -> P5:{p5:.6f}(L) -> P6:{p6:.6f}(H) -> P7:{p7:.6f}(L-retest P4) -> P8:{p8:.6f}(H)")
                logger.info(f"   Breakout: low[5]({lo5:.6f}) > high[2]({hi2:.6f}) = {lo5 > hi2}, low[3]({lo3:.6f}) > low[1]({lo1:.6f}) = {lo3 > lo1}")
            else:
                logger.info(f"[8-PIVOT] ✓✓✓ VALID DOWNTREND: P1:{p1:.6f}(H) -> P2:{p2:.6f}(L) -> P3:{p3:.6f}(H) -> P4:{p4:.6f}(L) -> P5:{p5:.6f}(H) -> P6:{p6:.6f}(L) -> P7:{p7:.6f}(H-retest P4) -> P8:{p8:.6f}(L)")
                logger.info(f"   Breakout: high[5]({hi5:.6f}) < low[2]({lo2:.6f}) = {hi5 < lo2}, high[3]({hi3:.6f}) < high[1]({hi1:.6f}) = {hi3 < hi1}")
            
            return True
        
        return False
    
    def check_choch(self, df: pd.DataFrame, state: TimeframeState, 
                    current_idx: int) -> Tuple[bool, bool]:
        """
        Kiểm tra CHoCH với confirmation (CHỈ SỬ DỤNG CLOSED CANDLES):
        - CHoCH Up: Nến sau CHoCH phải có low > high của nến trước CHoCH
        - CHoCH Down: Nến sau CHoCH phải có high < low của nến trước CHoCH
        
        IMPORTANT: Tất cả nến (pre-CHoCH, CHoCH, confirmation) đều phải đã ĐÓNG
        
        Returns: (fire_choch_up, fire_choch_down)
        """
        if state.pivot_count() < 8:
            return False, False

        if state.last_eight_bar_idx is None:
            return False, False

        # Must be after eight pattern
        is_after_eight = current_idx > state.last_eight_bar_idx

        if not is_after_eight:
            return False, False

        # ⚠️ CRITICAL: Cần ít nhất 3 nến ĐÃ ĐÓNG cho confirmation logic
        # current_idx là nến confirmation cuối cùng (ĐÃ ĐÓNG)
        # Không còn cần lo về nến đang mở vì đã được loại bỏ ở fetcher
        try:
            current_loc = df.index.get_loc(current_idx)
            if current_loc < 2:  # Need at least 3 bars total
                return False, False
                
            current = df.loc[current_idx]  # Nến confirmation (ĐÃ ĐÓNG)
            prev_idx = df.index[current_loc - 1]
            prev = df.loc[prev_idx]  # Nến CHoCH (ĐÃ ĐÓNG)
            pre_prev_idx = df.index[current_loc - 2] 
            pre_prev = df.loc[pre_prev_idx]  # Nến trước CHoCH (ĐÃ ĐÓNG)
        except (KeyError, IndexError):
            return False, False

        # CHoCH conditions on previous bar (nến CHoCH - ĐÃ ĐÓNG)
        # CHoCH Up: low[prev] > low[pre_prev] AND close[prev] > high[pre_prev] AND close[prev] > pivot6
        choch_up_bar = (prev['low'] > pre_prev['low'] and 
                       prev['close'] > pre_prev['high'] and 
                       prev['close'] > state.pivot6)
        
        # CHoCH Down: high[prev] < high[pre_prev] AND close[prev] < low[pre_prev] AND close[prev] < pivot6
        choch_down_bar = (prev['high'] < pre_prev['high'] and 
                         prev['close'] < pre_prev['low'] and 
                         prev['close'] < state.pivot6)

        # Match with pattern direction
        base_up = is_after_eight and state.last_eight_down and choch_up_bar
        base_down = is_after_eight and state.last_eight_up and choch_down_bar

        # Confirmation conditions (TẤT CẢ ĐỀU ĐÃ ĐÓNG):
        # CHoCH Up: current bar low > high của nến trước CHoCH (pre_prev)
        confirm_up = base_up and (current['low'] > pre_prev['high'])
        
        # CHoCH Down: current bar high < low của nến trước CHoCH (pre_prev)  
        confirm_down = base_down and (current['high'] < pre_prev['low'])

        # Fire signal nếu có confirmation và chưa lock
        if not state.choch_locked and (confirm_up or confirm_down):
            state.choch_locked = True
            state.choch_bar_idx = prev_idx  # CHoCH occurred at previous bar (ĐÃ ĐÓNG)
            state.choch_price = prev['close']  # CHoCH price (ĐÃ ĐÓNG)
            
            fire_choch_up = confirm_up
            fire_choch_down = confirm_down
            
            logger.info(f"[CHoCH] ✅ CONFIRMED: {'UP' if confirm_up else 'DOWN'} @ {prev['close']:.6f} (ALL CLOSED CANDLES)")
            logger.info(f"   CHoCH bar: {prev_idx} (O:{prev['open']}, H:{prev['high']}, L:{prev['low']}, C:{prev['close']}) [CLOSED]")
            logger.info(f"   Pre-CHoCH: {pre_prev_idx} (O:{pre_prev['open']}, H:{pre_prev['high']}, L:{pre_prev['low']}, C:{pre_prev['close']}) [CLOSED]")
            logger.info(f"   Confirm bar: {current_idx} (O:{current['open']}, H:{current['high']}, L:{current['low']}, C:{current['close']}) [CLOSED]")
            
            return fire_choch_up, fire_choch_down

        return False, False
    
    def rebuild_pivots(self, timeframe: str, df: pd.DataFrame) -> int:
        """
        Rebuild ALL pivots from a fresh dataframe window.
        
        This is called when monitor_loop fetches 50 bars and wants to
        rebuild the pivot state from scratch. Pivots from the old state
        are discarded and replaced with pivots from the new dataframe.
        
        Args:
            timeframe: Timeframe identifier
            df: Fresh dataframe (e.g., 50 bars)
        
        Returns:
            Number of pivots built
        """
        state = self.get_state(timeframe)
        
        # RESET: Clear all previous state and pivots
        state.reset()
        
        if len(df) < self.left + self.right + 1:
            return 0
        
        # Detect pivots in entire dataframe
        ph, pl = self.detect_pivots(df)
        
        total_ph = ph.notna().sum()
        total_pl = pl.notna().sum()
        total_real_pivots = total_ph + total_pl
        
        # Process ALL pivots in dataframe
        for check_idx in range(self.left, len(df) - self.right):
            is_ph = pd.notna(ph.iloc[check_idx])
            is_pl = pd.notna(pl.iloc[check_idx])
            
            if not (is_ph or is_pl):
                continue
            
            pivot_price = ph.iloc[check_idx] if is_ph else pl.iloc[check_idx]
            pivot_idx = df.index[check_idx]
            is_high = is_ph
            
            # Variant filtering
            accept = True
            if self.use_variant_filter:
                variant = self.classify_variant(df, check_idx, is_high)
                accept = variant != "NA" and self.allow_variants.get(variant, False)
            
            if accept:
                # Insert fake pivot if needed (only once per gap)
                if state.pivot_count() > 0:
                    last_bar, last_price, last_high = state.get_pivot_from_end(0)
                    self.insert_fake_pivot(state, df, last_bar, last_price, last_high, 
                                          pivot_idx, is_high)
                
                # Store new pivot
                state.store_pivot(pivot_idx, pivot_price, is_high)
                state.last_pivot_bar = pivot_idx
                state.last_pivot_price = pivot_price
        
        # Check for 8-pattern
        self.check_eight_pattern(state, df)
        
        pivot_after = state.pivot_count()
        logger.info(f"[rebuild_pivots] {len(df)} bars → {total_real_pivots} real pivots → {pivot_after} total (with fakes)")
        
        return pivot_after
    
    def process_new_bar(self, timeframe: str, df: pd.DataFrame) -> Dict:
        """
        Process new bar for a timeframe and detect CHoCH (CLOSED CANDLES ONLY)
        
        IMPORTANT: DataFrame chỉ chứa CLOSED candles (open candle đã được loại bỏ ở fetcher)
        
        Args:
            timeframe: Timeframe identifier (e.g., '5m')
            df: DataFrame with CLOSED OHLCV data only, index = timestamp
        
        Returns:
            Dict with detection results: {
                'choch_up': bool,
                'choch_down': bool,
                'signal_type': str or None,
                'direction': str or None,
                'price': float or None,
                'timestamp': pd.Timestamp or None
            }
        """
        state = self.get_state(timeframe)
        
        result = {
            'choch_up': False,
            'choch_down': False,
            'signal_type': None,
            'direction': None,
            'price': None,
            'timestamp': None
        }
        
        if len(df) < 3:
            logger.debug(f"[{timeframe}] Not enough CLOSED bars for CHoCH confirmation (need 3, have {len(df)})")
            return result
        
        # ✅ Nến confirmation là nến cuối cùng (ĐÃ ĐÓNG - vì open candle đã được loại bỏ)
        current_idx = df.index[-1]  # Latest CLOSED bar (confirmation candle)
        logger.debug(f"[{timeframe}] Checking CHoCH confirmation on CLOSED bar: {current_idx}")
        
        fire_up, fire_down = self.check_choch(df, state, current_idx)
        
        if fire_up or fire_down:
            result['choch_up'] = fire_up
            result['choch_down'] = fire_down
            result['signal_type'] = 'CHoCH Up' if fire_up else 'CHoCH Down'
            result['direction'] = 'Long' if fire_up else 'Short'
            # Use CHoCH price and timestamp (đã đóng)
            result['price'] = state.choch_price
            result['timestamp'] = current_idx
        
        return result
