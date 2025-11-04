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
        self.pivot5: Optional[float] = None  # Pivot 5 for additional CHoCH condition
        self.pivot6: Optional[float] = None  # Changed from pivot4 to pivot6 for 8-pivot pattern
        self.pattern_group: Optional[str] = None  # Store which group (G1, G2, G3) matched
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
        self.pivot5 = None
        self.pivot6 = None
        self.pattern_group = None
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
                 allow_ph1: bool = True, allow_ph2: bool = True, allow_ph3: bool = True,
                 allow_pl1: bool = True, allow_pl2: bool = True, allow_pl3: bool = True):
        
        self.left = left
        self.right = right
        self.keep_pivots = keep_pivots
        
        # CHỈ detect pivot theo variant pattern (giống Pine Script)
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
    
    def is_pivot_high_basic(self, df: pd.DataFrame, i: int) -> bool:
        """Check if bar i is a basic pivot high (without variant filtering)"""
        center_high = df['high'].iloc[i]
        
        # Check left side
        for j in range(i - self.left, i):
            if df['high'].iloc[j] >= center_high:
                return False
        
        # Check right side
        for j in range(i + 1, i + self.right + 1):
            if df['high'].iloc[j] > center_high:
                return False
        
        return True
    
    def is_pivot_low_basic(self, df: pd.DataFrame, i: int) -> bool:
        """Check if bar i is a basic pivot low (without variant filtering)"""
        center_low = df['low'].iloc[i]
        
        # Check left side
        for j in range(i - self.left, i):
            if df['low'].iloc[j] <= center_low:
                return False
        
        # Check right side
        for j in range(i + 1, i + self.right + 1):
            if df['low'].iloc[j] < center_low:
                return False
        
        return True
    
    def detect_pivots_with_variants(self, df: pd.DataFrame) -> List[Tuple[int, float, bool, str]]:
        """
        Detect pivots CHỈ KHI match variant pattern (giống Pine Script)
        
        Returns: List of (index, price, is_high, variant_type)
        """
        pivots = []
        
        for i in range(self.left, len(df) - self.right):
            # Check pivot high với variant
            if self.is_pivot_high_basic(df, i):
                variant = self.classify_variant(df, i, is_high=True)
                if variant != "NA" and self.allow_variants.get(variant, False):
                    pivots.append((i, df['high'].iloc[i], True, variant))
            
            # Check pivot low với variant
            if self.is_pivot_low_basic(df, i):
                variant = self.classify_variant(df, i, is_high=False)
                if variant != "NA" and self.allow_variants.get(variant, False):
                    pivots.append((i, df['low'].iloc[i], False, variant))
        
        return pivots
    
    def classify_variant(self, df: pd.DataFrame, pivot_idx: int, is_high: bool) -> str:
        """
        Classify pivot variant (PH1/PH2/PH3 or PL1/PL2/PL3)
        Uses triplet around the pivot bar
        
        Pine Script logic:
        - Pivot is detected at bar_index - right (nến giữa)
        - Triplet: high[right+1] (left), high[right] (center/pivot), high[right-1] (right)
        - Timeline: [LEFT/h3] → [CENTER/h2/PIVOT] → [RIGHT/h1]
        - In Python: pivot_idx-1 (left/h3), pivot_idx (center/h2), pivot_idx+1 (right/h1)
        """
        # Need bars on both sides
        if pivot_idx < 1 or pivot_idx >= len(df) - 1:
            return "NA"
        
        # Triplet mapping to Pine Script:
        # h3 = left side (bar before pivot in timeline)
        # h2 = center (pivot bar itself)
        # h1 = right side (bar after pivot in timeline)
        h3 = df['high'].iloc[pivot_idx - 1]  # LEFT side (high[right+1] in Pine)
        h2 = df['high'].iloc[pivot_idx]      # CENTER (high[right] in Pine) - PIVOT
        h1 = df['high'].iloc[pivot_idx + 1]  # RIGHT side (high[right-1] in Pine)
        
        l3 = df['low'].iloc[pivot_idx - 1]   # LEFT side
        l2 = df['low'].iloc[pivot_idx]       # CENTER - PIVOT
        l1 = df['low'].iloc[pivot_idx + 1]   # RIGHT side
        
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
    
    def check_eight_pattern(self, state: TimeframeState, df: pd.DataFrame, pivot_offset: int = 0) -> Tuple[bool, bool, Optional[str], Optional[float], Optional[float], Optional[int], Optional[float]]:
        """
        Check for valid 8-pivot pattern (supports pattern groups G1, G2, G3)
        
        Args:
            pivot_offset: Offset to shift pivot reading (0 = use latest pivots, 1 = skip latest pivot)
                         Used when CHoCH bar is the newest pivot to check pattern from previous 8 pivots
        
        Returns:
            Tuple of (last_eight_up, last_eight_down, pattern_group, pivot5, pivot6, last_eight_bar_idx, p2)
        """
        logger.info(f"[CHECK_EIGHT_PATTERN] CALLED with offset={pivot_offset}, pivot_count={state.pivot_count()}")
        
        required_pivots = 8 + pivot_offset
        if state.pivot_count() < required_pivots:
            logger.info(f"[CHECK_EIGHT_PATTERN] Not enough pivots: {state.pivot_count()} < {required_pivots}")
            return False, False, None, None, None, None, None
        
        # ALWAYS use latest 8 pivots for pattern check (matching Pine Script logic)
        # Pine Script: getPivotFromEnd(0) = newest, getPivotFromEnd(7) = 8th from end
        # Python: get_pivot_from_end(0) = newest, get_pivot_from_end(7) = 8th from end
        
        # Map to 8-pivot pattern (p1 = oldest of the 8, p8 = newest)
        b8, p8, h8 = state.get_pivot_from_end(0 + pivot_offset)
        b7, p7, h7 = state.get_pivot_from_end(1 + pivot_offset)
        b6, p6, h6 = state.get_pivot_from_end(2 + pivot_offset)
        b5, p5, h5 = state.get_pivot_from_end(3 + pivot_offset)
        b4, p4, h4 = state.get_pivot_from_end(4 + pivot_offset)
        b3, p3, h3 = state.get_pivot_from_end(5 + pivot_offset)
        b2, p2, h2 = state.get_pivot_from_end(6 + pivot_offset)
        b1, p1, h1 = state.get_pivot_from_end(7 + pivot_offset)
        
        # NOTE: removed 10-pivot (G4/G5) handling — always use the latest 8 pivots
        
        # Check alternating structure for 8 pivots
        up_struct = (not h1) and h2 and (not h3) and h4 and (not h5) and h6 and (not h7) and h8
        down_struct = h1 and (not h2) and h3 and (not h4) and h5 and (not h6) and h7 and (not h8)
        
        
        if not (up_struct or down_struct):
            return False, False, None, None, None, None, None
        
        # Check P7 retest P4 (for 8-pivot pattern)
        try:
            hi7 = df.loc[b7, 'high']
            lo7 = df.loc[b7, 'low']
            hi4 = df.loc[b4, 'high']
            lo4 = df.loc[b4, 'low']
            
            touch_retest = (up_struct and (lo7 < hi4)) or (down_struct and (hi7 > lo4))
            
            logger.info(f"[CHECK_EIGHT_PATTERN] Touch retest check:")
            logger.info(f"  b7={b7}, lo7={lo7:.6f}, hi7={hi7:.6f} (P7={p7:.6f})")
            logger.info(f"  b4={b4}, hi4={hi4:.6f}, lo4={lo4:.6f} (P4={p4:.6f})")
            logger.info(f"  up_struct={up_struct}, lo7 < hi4? {lo7:.6f} < {hi4:.6f} = {lo7 < hi4}")
            logger.info(f"  down_struct={down_struct}, hi7 > lo4? {hi7:.6f} > {lo4:.6f} = {hi7 > lo4}")
            logger.info(f"  → touch_retest={touch_retest}")
            
            if not touch_retest:
                logger.info(f"[CHECK_EIGHT_PATTERN] Touch retest FAILED - returning False")
                return False, False, None, None, None, None, None
        except KeyError as e:
            logger.info(f"[CHECK_EIGHT_PATTERN] Touch retest KeyError: {e} - returning False")
            return False, False, None, None, None, None, None
        
        # Check P8 is extreme
        all_prices = [p1, p2, p3, p4, p5, p6, p7, p8]
        is_highest8 = p8 == max(all_prices)
        is_lowest8 = p8 == min(all_prices)
        
        # Order constraints - Groups G1..G3
        # G1 (Original): 
        g1_up_order = (p2 < p4 < p6 < p8) and (p3 < p5 < p7)
        g1_down_order = (p3 > p5 > p7) and (p2 > p4 > p6 > p8)
        
        # G2:
        # Uptrend: p3 < p7 < p5, p2 < p6 < p4 < p8, p2 < p5
        g2_up_order = (p3 < p7 < p5) and (p2 < p6 < p4 < p8) and (p2 < p5)
        # Downtrend: p3 > p7 > p5, p2 > p6 > p4 > p8, p2 > p5
        g2_down_order = (p3 > p7 > p5) and (p2 > p6 > p4 > p8) and (p2 > p5)
        
        # G3:
        # Uptrend: p3 < p5 < p7, p2 < p6 < p4 < p8, p2 < p5
        g3_up_order = (p3 < p5 < p7) and (p2 < p6 < p4 < p8) and (p2 < p5)
        # Downtrend: p3 > p5 > p7, p2 > p6 > p4 > p8, p2 > p5
        g3_down_order = (p3 > p5 > p7) and (p2 > p6 > p4 > p8) and (p2 > p5)
        
        # Removed G4/G5/G6 (10-pivot groups). Keep only G1..G3 order checks.
        # Combined order check (any of G1, G2, G3 is valid)
        up_order_ok = g1_up_order or g2_up_order or g3_up_order
        down_order_ok = g1_down_order or g2_down_order or g3_down_order

        # Breakout conditions (simplified - removed p1/p3 comparisons)
        try:
            # For uptrend: low[5] > high[2]
            lo5 = df.loc[b5, 'low']
            hi2 = df.loc[b2, 'high']

            # For downtrend: high[5] < low[2]
            hi5 = df.loc[b5, 'high']
            lo2 = df.loc[b2, 'low']

            up_breakout = (lo5 > hi2)
            down_breakout = (hi5 < lo2)

        except KeyError:
            up_breakout = False
            down_breakout = False
        # Validate pattern - uptrend cần up_breakout, downtrend cần down_breakout
        last_eight_up_result = up_struct and up_order_ok and touch_retest and is_highest8 and up_breakout
        last_eight_down_result = down_struct and down_order_ok and touch_retest and is_lowest8 and down_breakout
        
        pattern_group_result = None
        
        if last_eight_up_result or last_eight_down_result:
            # Determine which group matched
            if last_eight_up_result:
                if g1_up_order:
                    pattern_group_result = "G1"
                elif g2_up_order:
                    pattern_group_result = "G2"
                elif g3_up_order:
                    pattern_group_result = "G3"
                    
                logger.info(f"[8-PIVOT-{pattern_group_result}] ✓✓✓ VALID UPTREND PATTERN (offset={pivot_offset}): P1:{p1:.6f}(L) -> P2:{p2:.6f}(H) -> P3:{p3:.6f}(L) -> P4:{p4:.6f}(H) -> P5:{p5:.6f}(L) -> P6:{p6:.6f}(H) -> P7:{p7:.6f}(L-retest P4) -> P8:{p8:.6f}(H)")
                logger.info(f"   Breakout UP: low[5]({lo5:.6f}) > high[2]({hi2:.6f}) = {lo5 > hi2}")
            else:
                if g1_down_order:
                    pattern_group_result = "G1"
                elif g2_down_order:
                    pattern_group_result = "G2"
                elif g3_down_order:
                    pattern_group_result = "G3"
                    
                logger.info(f"[8-PIVOT-{pattern_group_result}] ✓✓✓ VALID DOWNTREND PATTERN (offset={pivot_offset}): P1:{p1:.6f}(H) -> P2:{p2:.6f}(L) -> P3:{p3:.6f}(H) -> P4:{p4:.6f}(L) -> P5:{p5:.6f}(H) -> P6:{p6:.6f}(L) -> P7:{p7:.6f}(H-retest P4) -> P8:{p8:.6f}(L)")
                logger.info(f"   Breakout DOWN: high[5]({hi5:.6f}) < low[2]({lo2:.6f}) = {hi5 < lo2}")
            
            return last_eight_up_result, last_eight_down_result, pattern_group_result, p5, p6, b8, p2
        
        return False, False, None, None, None, None, None
        
    def check_choch(self, df: pd.DataFrame, state: TimeframeState, 
                    current_idx: int) -> Tuple[bool, bool]:
        """
        Kiểm tra CHoCH với confirmation (CHỈ SỬ DỤNG CLOSED CANDLES):
        - CHoCH Up: Nến sau CHoCH phải có low > high của nến trước CHoCH AND close <= pivot2
        - CHoCH Down: Nến sau CHoCH phải có high < low của nến trước CHoCH AND close >= pivot2
        
        CHoCH Bar Conditions:
        - CHoCH Up: close[CHoCH] < pivot2 (không vượt quá pivot2)
        - CHoCH Down: close[CHoCH] > pivot2 (không vượt quá pivot2)
        
        IMPORTANT: Tất cả nến (pre-CHoCH, CHoCH, confirmation) đều phải đã ĐÓNG
        
        Pattern Group Specific Conditions (added on confirmation candle):
        - Downtrend → CHoCH Up:
          * G1: Close_CF <= HIGH_5
          * G2: Close_CF <= HIGH_7
          * G3: Close_CF <= HIGH_5
        - Uptrend → CHoCH Down:
          * G1: Close_CF >= LOW_5
          * G2: Close_CF >= LOW_7
          * G3: Close_CF >= LOW_5
        
        Volume Conditions:
        - G1: (678_ok AND 456_ok) OR 45678_ok
          * 678_ok: (Vol8 OR Vol6 OR Vol_CHoCH) max in {vol6, vol7, vol8}
          * 456_ok: (Vol4 OR Vol6) max in {vol4, vol5, vol6}
          * 45678_ok: (Vol8 OR Vol_CHoCH) max in {vol4, vol5, vol6, vol7, vol8}
        - G2/G3: (Vol4 OR Vol5 OR Vol_CHoCH) max in cluster 456
        
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

        # Get pivot prices for pattern group conditions
        if state.pivot_count() < 8:
            return False, False
            
        b8, p8, h8 = state.get_pivot_from_end(0)
        b7, p7, h7 = state.get_pivot_from_end(1)
        b6, p6, h6 = state.get_pivot_from_end(2)
        b5, p5, h5 = state.get_pivot_from_end(3)
        b4, p4, h4 = state.get_pivot_from_end(4)
        b3, p3, h3 = state.get_pivot_from_end(5)
        b2, p2, h2 = state.get_pivot_from_end(6)
        b1, p1, h1 = state.get_pivot_from_end(7)
        
        # Get volumes at pivot bars
        try:
            vol8 = df.loc[b8, 'volume']
            vol7 = df.loc[b7, 'volume']
            vol6 = df.loc[b6, 'volume']
            vol5 = df.loc[b5, 'volume']
            vol4 = df.loc[b4, 'volume']
            vol_choch = prev['volume']  # Volume of CHoCH candle
        except KeyError:
            logger.warning(f"Cannot get volume data for pivots")
            return False, False

        # CHoCH conditions on previous bar (nến CHoCH - ĐÃ ĐÓNG)
        # CHoCH Up: low[prev] > low[pre_prev] AND close[prev] > high[pre_prev] AND close[prev] > pivot6 AND close[prev] < pivot2
        choch_up_bar = (prev['low'] > pre_prev['low'] and 
                       prev['close'] > pre_prev['high'] and 
                       prev['close'] > state.pivot6 and
                       prev['close'] < p2)
        
        # CHoCH Down: high[prev] < high[pre_prev] AND close[prev] < low[pre_prev] AND close[prev] < pivot6 AND close[prev] > pivot2
        choch_down_bar = (prev['high'] < pre_prev['high'] and 
                         prev['close'] < pre_prev['low'] and 
                         prev['close'] < state.pivot6 and
                         prev['close'] > p2)

        # ========== CHECK IF CHOCH BAR IS NEWEST PIVOT ==========
        # Nếu nến CHoCH (prev_idx) là pivot mới nhất, cần lấy pattern từ 8 pivot trước đó
        choch_bar_is_pivot = (prev_idx == state.last_eight_bar_idx)
        nine_ready = state.pivot_count() >= 9
        
        effective_last_eight_up = state.last_eight_up
        effective_last_eight_down = state.last_eight_down
        effective_eight_bar_idx = state.last_eight_bar_idx
        
        if choch_bar_is_pivot and nine_ready:
            logger.debug(f"[CHoCH] CHoCH bar {prev_idx} IS newest pivot (p8={state.last_eight_bar_idx})")
            logger.debug(f"[CHoCH] Recalculating pattern from previous 8 pivots (offset=1)")
            
            # Tính lại pattern từ 8 pivot trước đó (bỏ qua pivot mới nhất)
            pattern_result = self.check_eight_pattern(state, df, pivot_offset=1)
            
            if pattern_result[0] or pattern_result[1]:
                effective_last_eight_up = pattern_result[0]
                effective_last_eight_down = pattern_result[1]
                effective_eight_bar_idx = pattern_result[5]  # b8 from offset pivots
                
                # NOTE: KHÔNG recalculate choch_up_bar/choch_down_bar như Pine Script
                # Pine Script chỉ thay đổi effectiveLastEightUp/Down, không đổi điều kiện CHoCH
                
                logger.debug(f"[CHoCH] Effective pattern: up={effective_last_eight_up}, down={effective_last_eight_down}")
                logger.debug(f"[CHoCH] Effective eight_bar_idx: {effective_eight_bar_idx} (was {state.last_eight_bar_idx})")
            else:
                logger.debug(f"[CHoCH] No valid pattern found with offset=1, using current state")
        
        # Must be after eight pattern (use effective bar idx)
        is_after_eight = current_idx > effective_eight_bar_idx

        if not is_after_eight:
            return False, False

        # Basic confirmation conditions (KHÔNG phụ thuộc base):
        # CHoCH Up: close của confirmation > high của nến pre-CHoCH
        confirm_up_basic = (current['close'] > pre_prev['high'])
        
        # CHoCH Down: close của confirmation < low của nến pre-CHoCH
        confirm_down_basic = (current['close'] < pre_prev['low'])

        # Match with pattern direction (use effective values) - THÊM confirmation vào base như Pine Script
        base_up = is_after_eight and effective_last_eight_down and choch_up_bar and confirm_up_basic
        base_down = is_after_eight and effective_last_eight_up and choch_down_bar and confirm_down_basic

        # Pattern Group Specific Conditions for confirmation candle
        confirm_up = False
        confirm_down = False
        
        if base_up and state.pattern_group:
            # Downtrend → CHoCH Up (base_up đã bao gồm confirm_up_basic)
            price_condition = False
            volume_condition = False
            
            if state.pattern_group == "G1":
                # G1: Close_CF <= HIGH_5
                price_condition = current['close'] <= p5
                
                # Volume condition G1: (678_ok AND 456_ok) OR 45678_ok
                # 1. (Vol8 OR Vol6 OR Vol_CHoCH) là lớn nhất cụm 678
                max_678 = max(vol6, vol7, vol8)
                vol_678_ok = (vol8 == max_678) or (vol6 == max_678) or (vol_choch == max_678)
                
                # 2. (Vol4 OR Vol6) là lớn nhất cụm 456
                max_456 = max(vol4, vol5, vol6)
                vol_456_ok = (vol4 == max_456) or (vol6 == max_456)
                
                # 3. (Vol8 OR Vol_CHoCH) là lớn nhất cụm 45678
                max_45678 = max(vol4, vol5, vol6, vol7, vol8)
                vol_45678_ok = (vol8 == max_45678) or (vol_choch == max_45678)
                
                volume_condition = (vol_678_ok and vol_456_ok) or vol_45678_ok
                confirm_up = price_condition and volume_condition
                
                if not volume_condition:
                    logger.debug(f"[G1] Volume condition failed - 678_ok:{vol_678_ok} 456_ok:{vol_456_ok} 45678_ok:{vol_45678_ok}")
                
            elif state.pattern_group == "G2":
                # G2: Close_CF <= HIGH_7
                price_condition = current['close'] <= p7
                
                # Volume condition G2/G3:
                # (Vol4 OR Vol5 OR Vol_CHoCH) là lớn nhất cụm 456
                max_456 = max(vol4, vol5, vol6)
                volume_condition = (vol4 == max_456) or (vol5 == max_456) or (vol_choch >= max_456)
                confirm_up = price_condition and volume_condition
                
                if not volume_condition:
                    logger.debug(f"[G2] Volume condition failed - vol4={vol4:.0f} vol5={vol5:.0f} vol_choch={vol_choch:.0f} max={max_456:.0f}")
                
            elif state.pattern_group == "G3":
                # G3: Close_CF <= HIGH_5
                price_condition = current['close'] <= p5
                
                # Volume condition G2/G3:
                # (Vol4 OR Vol5 OR Vol_CHoCH) là lớn nhất cụm 456
                max_456 = max(vol4, vol5, vol6)
                volume_condition = (vol4 == max_456) or (vol5 == max_456) or (vol_choch >= max_456)
                confirm_up = price_condition and volume_condition
                
                if not volume_condition:
                    logger.debug(f"[G3] Volume condition failed - vol4={vol4:.0f} vol5={vol5:.0f} vol_choch={vol_choch:.0f} max={max_456:.0f}")
        
        if base_down and state.pattern_group:
            # Uptrend → CHoCH Down (base_down đã bao gồm confirm_down_basic)
            price_condition = False
            volume_condition = False
            
            if state.pattern_group == "G1":
                # G1: Close_CF >= LOW_5
                price_condition = current['close'] >= p5
                
                # Volume condition G1: (678_ok AND 456_ok) OR 45678_ok
                # 1. (Vol8 OR Vol6 OR Vol_CHoCH) là lớn nhất cụm 678
                max_678 = max(vol6, vol7, vol8)
                vol_678_ok = (vol8 == max_678) or (vol6 == max_678) or (vol_choch == max_678)
                
                # 2. (Vol4 OR Vol6) là lớn nhất cụm 456
                max_456 = max(vol4, vol5, vol6)
                vol_456_ok = (vol4 == max_456) or (vol6 == max_456)
                
                # 3. (Vol8 OR Vol_CHoCH) là lớn nhất cụm 45678
                max_45678 = max(vol4, vol5, vol6, vol7, vol8)
                vol_45678_ok = (vol8 == max_45678) or (vol_choch == max_45678)
                
                volume_condition = (vol_678_ok and vol_456_ok) or vol_45678_ok
                confirm_down = price_condition and volume_condition
                
                if not volume_condition:
                    logger.debug(f"[G1] Volume condition failed - 678_ok:{vol_678_ok} 456_ok:{vol_456_ok} 45678_ok:{vol_45678_ok}")
                
            elif state.pattern_group == "G2":
                # G2: Close_CF >= LOW_7
                price_condition = current['close'] >= p7
                
                # Volume condition G2/G3:
                # (Vol4 OR Vol5 OR Vol_CHoCH) là lớn nhất cụm 456
                max_456 = max(vol4, vol5, vol6)
                volume_condition = (vol4 == max_456) or (vol5 == max_456) or (vol_choch >= max_456)
                confirm_down = price_condition and volume_condition
                
                if not volume_condition:
                    logger.debug(f"[G2] Volume condition failed - vol4={vol4:.0f} vol5={vol5:.0f} vol_choch={vol_choch:.0f} max={max_456:.0f}")
                
            elif state.pattern_group == "G3":
                # G3: Close_CF >= LOW_5
                price_condition = current['close'] >= p5
                
                # Volume condition G2/G3:
                # (Vol4 OR Vol5 OR Vol_CHoCH) là lớn nhất cụm 456
                max_456 = max(vol4, vol5, vol6)
                volume_condition = (vol4 == max_456) or (vol5 == max_456) or (vol_choch >= max_456)
                confirm_down = price_condition and volume_condition
                
                if not volume_condition:
                    logger.debug(f"[G3] Volume condition failed - vol4={vol4:.0f} vol5={vol5:.0f} vol_choch={vol_choch:.0f} max={max_456:.0f}")

        # Fire signal nếu có confirmation và chưa lock
        if not state.choch_locked and (confirm_up or confirm_down):
            state.choch_locked = True
            state.choch_bar_idx = prev_idx  # CHoCH occurred at previous bar (ĐÃ ĐÓNG)
            state.choch_price = prev['close']  # CHoCH price (ĐÃ ĐÓNG)
            
            fire_choch_up = confirm_up
            fire_choch_down = confirm_down
            
            # Log pattern group condition with volume info
            if confirm_up:
                ref_pivot = p7 if state.pattern_group == "G2" else p5
                if state.pattern_group == "G1":
                    logger.info(f"[CHoCH-{state.pattern_group}] ✅ CONFIRMED UP @ {prev['close']:.6f} (Close_CF {current['close']:.6f} <= P5 {ref_pivot:.6f})")
                    logger.info(f"   Volume: vol4={vol4:.0f} vol5={vol5:.0f} vol6={vol6:.0f} vol7={vol7:.0f} vol8={vol8:.0f} vol_choch={vol_choch:.0f}")
                elif state.pattern_group == "G2":
                    logger.info(f"[CHoCH-{state.pattern_group}] ✅ CONFIRMED UP @ {prev['close']:.6f} (Close_CF {current['close']:.6f} <= P7 {ref_pivot:.6f})")
                    logger.info(f"   Volume 456: vol4={vol4:.0f} vol5={vol5:.0f} vol6={vol6:.0f} vol_choch={vol_choch:.0f}")
                else:  # G3
                    logger.info(f"[CHoCH-{state.pattern_group}] ✅ CONFIRMED UP @ {prev['close']:.6f} (Close_CF {current['close']:.6f} <= P5 {ref_pivot:.6f})")
                    logger.info(f"   Volume 456: vol4={vol4:.0f} vol5={vol5:.0f} vol6={vol6:.0f} vol_choch={vol_choch:.0f}")
            else:
                ref_pivot = p7 if state.pattern_group == "G2" else p5
                if state.pattern_group == "G1":
                    logger.info(f"[CHoCH-{state.pattern_group}] ✅ CONFIRMED DOWN @ {prev['close']:.6f} (Close_CF {current['close']:.6f} >= P5 {ref_pivot:.6f})")
                    logger.info(f"   Volume: vol4={vol4:.0f} vol5={vol5:.0f} vol6={vol6:.0f} vol7={vol7:.0f} vol8={vol8:.0f} vol_choch={vol_choch:.0f}")
                elif state.pattern_group == "G2":
                    logger.info(f"[CHoCH-{state.pattern_group}] ✅ CONFIRMED DOWN @ {prev['close']:.6f} (Close_CF {current['close']:.6f} >= P7 {ref_pivot:.6f})")
                    logger.info(f"   Volume 456: vol4={vol4:.0f} vol5={vol5:.0f} vol6={vol6:.0f} vol_choch={vol_choch:.0f}")
                else:  # G3
                    logger.info(f"[CHoCH-{state.pattern_group}] ✅ CONFIRMED DOWN @ {prev['close']:.6f} (Close_CF {current['close']:.6f} >= P5 {ref_pivot:.6f})")
                    logger.info(f"   Volume 456: vol4={vol4:.0f} vol5={vol5:.0f} vol6={vol6:.0f} vol_choch={vol_choch:.0f}")
            
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
        
        # Detect pivots CHỈ KHI match variant (giống Pine Script - không detect rồi mới filter)
        pivots = self.detect_pivots_with_variants(df)
        
        logger.info(f"[rebuild_pivots] {len(df)} bars → {len(pivots)} variant-matched pivots (NO pure pivot detection)")
        
        # Process ALL variant-matched pivots
        for check_idx, pivot_price, is_high, variant in pivots:
            pivot_idx = df.index[check_idx]
            
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
        pattern_result = self.check_eight_pattern(state, df)
        logger.debug(f"[rebuild_pivots] pattern_result type: {type(pattern_result)}, value: {pattern_result}")
        if pattern_result[0] or pattern_result[1]:  # If any pattern matched
            # Update state with results
            state.last_eight_up = pattern_result[0]
            state.last_eight_down = pattern_result[1]
            state.pattern_group = pattern_result[2]
            state.pivot5 = pattern_result[3]
            state.pivot6 = pattern_result[4]
            state.last_eight_bar_idx = pattern_result[5]
            # p2_price stored as pattern_result[6] but not saved to state (used in check_choch)
        
        pivot_after = state.pivot_count()
        logger.info(f"[rebuild_pivots] Final: {pivot_after} total pivots (with fakes)")
        
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
            result['pattern_group'] = state.pattern_group  # Add pattern group info
            # Use CHoCH price and timestamp (đã đóng)
            result['price'] = state.choch_price
            result['timestamp'] = current_idx
        
        return result
