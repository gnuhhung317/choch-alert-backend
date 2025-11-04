"""
Test CHoCH detection với 50 nến XRP 15m từ hiện tại
"""
import sys
import logging
import asyncio
from datetime import datetime
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from data.binance_fetcher import BinanceFetcher
from detectors.choch_detector import ChochDetector

async def test_xrp_15m():
    """Test CHoCH detection với XRP/USDT 15m"""
    
    symbol = 'XRPUSDT'
    timeframe = '15m'
    
    logger.info(f"=" * 80)
    logger.info(f"Testing CHoCH Detection: {symbol} - {timeframe}")
    logger.info(f"=" * 80)
    
    # Fetch data
    fetcher = BinanceFetcher()
    await fetcher.initialize()
    
    # Increase timeout for slow connections
    if fetcher.exchange:
        fetcher.exchange.timeout = 60000  # 60 seconds
    
    logger.info(f"Fetching 50 closed candles for {symbol} {timeframe}...")
    
    df = await fetcher.fetch_historical(symbol, timeframe, limit=50)
    
    # Slice to set the latest closed candle to 2025-11-04 02:30:00
    # (remove the last 4 candles: 02:45, 03:00, 03:15, 03:30) so the confirm candle at
    # 02:30 becomes the most-recent closed bar in our snapshot.
    if df is not None and len(df) > 4:
        df = df.iloc[:-19]
    
    if df is None or len(df) == 0:
        logger.error("Failed to fetch data")
        await fetcher.close()
        return
    
    logger.info(f"✅ Fetched {len(df)} closed candles")
    logger.info(f"   Time range: {df.index[0]} → {df.index[-1]}")
    logger.info(f"   Latest close: {df.iloc[-1]['close']}")
    
    # Enable detailed debug logging for the detector BEFORE initializing
    detector_logger = logging.getLogger('detectors.choch_detector')
    detector_logger.setLevel(logging.DEBUG)
    
    # Initialize detector
    detector = ChochDetector(
        left=1, 
        right=1,
        allow_ph1=True,
        allow_ph2=True, 
        allow_ph3=True,
        allow_pl1=True,
        allow_pl2=True,
        allow_pl3=True
    )
    
    # Rebuild pivots
    logger.info("\n" + "=" * 80)
    logger.info("REBUILDING PIVOTS")
    logger.info("=" * 80)
    
    pivot_count = detector.rebuild_pivots(timeframe, df)
    
    state = detector.get_state(timeframe)
    
    logger.info(f"\n📊 Pivot Summary:")
    logger.info(f"   Total pivots: {pivot_count}")
    logger.info(f"   Pattern found: {state.last_eight_up or state.last_eight_down}")
    logger.info(f"   - last_eight_up: {state.last_eight_up}")
    logger.info(f"   - last_eight_down: {state.last_eight_down}")
    logger.info(f"   - pattern_group: {state.pattern_group}")
    
    if state.last_eight_bar_idx:
        logger.info(f"   - last_eight_bar_idx: {state.last_eight_bar_idx}")
        logger.info(f"   - pivot5: {state.pivot5}")
        logger.info(f"   - pivot6: {state.pivot6}")
    
    # Check CHoCH
    logger.info("\n" + "=" * 80)
    logger.info("CHECKING CHOCH")
    logger.info("=" * 80)
    
    result = detector.process_new_bar(timeframe, df)
    
    logger.info(f"\n🎯 CHoCH Detection Result:")
    logger.info(f"   CHoCH Up: {result['choch_up']}")
    logger.info(f"   CHoCH Down: {result['choch_down']}")
    
    if result['choch_up'] or result['choch_down']:
        logger.info(f"   ✅ SIGNAL FIRED!")
        logger.info(f"   Direction: {result['direction']}")
        logger.info(f"   Price: {result['price']}")
        logger.info(f"   Timestamp: {result['timestamp']}")
        logger.info(f"   Pattern Group: {state.pattern_group}")
    else:
        logger.info(f"   ❌ No CHoCH signal")
    
    # Print last 5 candles for reference
    logger.info(f"\n📈 Last 5 Closed Candles:")
    for i in range(-5, 0):
        bar = df.iloc[i]
        logger.info(f"   [{i}] {df.index[i]} | O:{bar['open']:.6f} H:{bar['high']:.6f} L:{bar['low']:.6f} C:{bar['close']:.6f} V:{bar['volume']:.0f}")
    
    # Print all pivots
    if state.pivot_count() > 0:
        logger.info(f"\n📍 All Pivots ({state.pivot_count()}):")
        for i in range(state.pivot_count()):
            bar_idx, price, is_high = state.get_pivot_from_end(state.pivot_count() - 1 - i)
            pivot_type = "HIGH" if is_high else "LOW"
            logger.info(f"   P{i+1}: {bar_idx} | {pivot_type} @ {price:.6f}")
        
        # DEBUG: Check 8-pivot pattern P8-P15
        if state.pivot_count() >= 15:
            logger.info(f"\n🔍 DEBUG: Checking 8-pivot pattern P8-P15:")
            b15, p15, h15 = state.get_pivot_from_end(0)   # P15 (newest in pattern)
            b14, p14, h14 = state.get_pivot_from_end(1)   # P14
            b13, p13, h13 = state.get_pivot_from_end(2)   # P13
            b12, p12, h12 = state.get_pivot_from_end(3)   # P12
            b11, p11, h11 = state.get_pivot_from_end(4)   # P11
            b10, p10, h10 = state.get_pivot_from_end(5)   # P10
            b9, p9, h9 = state.get_pivot_from_end(6)      # P9
            b8, p8, h8 = state.get_pivot_from_end(7)     # P8 (oldest in pattern)
            
            logger.info(f"   P8:  {b8} | {'HIGH' if h8 else 'LOW'} @ {p8:.6f}")
            logger.info(f"   P9:  {b9} | {'HIGH' if h9 else 'LOW'} @ {p9:.6f}")
            logger.info(f"   P10: {b10} | {'HIGH' if h10 else 'LOW'} @ {p10:.6f}")
            logger.info(f"   P11: {b11} | {'HIGH' if h11 else 'LOW'} @ {p11:.6f}")
            logger.info(f"   P12: {b12} | {'HIGH' if h12 else 'LOW'} @ {p12:.6f}")
            logger.info(f"   P13: {b13} | {'HIGH' if h13 else 'LOW'} @ {p13:.6f}")
            logger.info(f"   P14: {b14} | {'HIGH' if h14 else 'LOW'} @ {p14:.6f}")
            logger.info(f"   P15: {b15} | {'HIGH' if h15 else 'LOW'} @ {p15:.6f}")
            
            # Check structure
            up_struct = (not h8) and h9 and (not h10) and h11 and (not h12) and h13 and (not h14) and h15
            logger.info(f"\n   Structure Check (UP pattern):")
            logger.info(f"   - Expected: L-H-L-H-L-H-L-H")
            logger.info(f"   - Actual: {['L' if not h else 'H' for h in [h8, h9, h10, h11, h12, h13, h14, h15]]}")
            logger.info(f"   - up_struct: {up_struct}")
            
            if up_struct:
                # Check order constraints
                logger.info(f"\n   Order Constraints:")
                logger.info(f"   G1 Up: p9 < p11 < p13 < p15: {p9:.6f} < {p11:.6f} < {p13:.6f} < {p15:.6f} = {p9 < p11 < p13 < p15}")
                logger.info(f"         p8 < p10 < p12 < p14: {p8:.6f} < {p10:.6f} < {p12:.6f} < {p14:.6f} = {p8 < p10 < p12 < p14}")
                g1_up = (p9 < p11 < p13 < p15) and (p8 < p10 < p12 < p14)
                
                # Check touch retest
                try:
                    hi14 = df.loc[b14, 'high']
                    lo14 = df.loc[b14, 'low']
                    hi11 = df.loc[b11, 'high']
                    touch_retest = (lo14 < hi11)
                    logger.info(f"\n   Touch Retest P14-P11:")
                    logger.info(f"   - lo14 < hi11: {lo14:.6f} < {hi11:.6f} = {touch_retest}")
                except KeyError as e:
                    logger.error(f"   - Cannot check touch retest: {e}")
                    touch_retest = False
                
                # Check P15 is extreme
                all_prices = [p8, p9, p10, p11, p12, p13, p14, p15]
                is_highest = p15 == max(all_prices)
                logger.info(f"\n   Extreme Check:")
                logger.info(f"   - p15 is highest: {p15:.6f} == {max(all_prices):.6f} = {is_highest}")
                
                # Check breakout
                try:
                    lo12 = df.loc[b12, 'low']
                    hi9 = df.loc[b9, 'high']
                    up_breakout = (lo12 > hi9)
                    logger.info(f"\n   Breakout Check:")
                    logger.info(f"   - lo12 > hi9: {lo12:.6f} > {hi9:.6f} = {up_breakout}")
                except KeyError as e:
                    logger.error(f"   - Cannot check breakout: {e}")
                    up_breakout = False
                
                logger.info(f"\n   ✅ Final Pattern Result:")
                logger.info(f"   - Structure: {up_struct}")
                logger.info(f"   - Order (G1): {g1_up}")
                logger.info(f"   - Touch Retest: {touch_retest}")
                logger.info(f"   - Extreme: {is_highest}")
                logger.info(f"   - Breakout: {up_breakout}")
                logger.info(f"   → Pattern Valid: {up_struct and g1_up and touch_retest and is_highest and up_breakout}")
    
    # DEBUG: Check specific candle at 2:30 GMT+0 (which is 09:30 GMT+7)
    logger.info(f"\n🔍 DEBUG: Checking candle at 2025-11-04 02:30:00 (2h30 GMT+0):")
    try:
        target_time = pd.Timestamp('2025-11-04 02:30:00')
        if target_time in df.index:
            candle = df.loc[target_time]
            logger.info(f"   Found candle: O:{candle['open']:.6f} H:{candle['high']:.6f} L:{candle['low']:.6f} C:{candle['close']:.6f}")
            
            # Get surrounding candles for CHoCH check
            loc = df.index.get_loc(target_time)
            if loc >= 2:
                pre_prev = df.iloc[loc - 2]
                prev = df.iloc[loc - 1]
                current = df.iloc[loc]
                
                logger.info(f"   Pre-CHoCH [loc-2]: {df.index[loc-2]} | C:{pre_prev['close']:.6f} H:{pre_prev['high']:.6f} L:{pre_prev['low']:.6f}")
                logger.info(f"   CHoCH bar [loc-1]: {df.index[loc-1]} | C:{prev['close']:.6f} H:{prev['high']:.6f} L:{prev['low']:.6f}")
                logger.info(f"   Confirm [loc]: {df.index[loc]} | C:{current['close']:.6f} H:{current['high']:.6f} L:{current['low']:.6f}")
                
                # Check CHoCH conditions
                if state.pivot6 and state.last_eight_bar_idx:
                    logger.info(f"\n   Pattern State:")
                    logger.info(f"   - pivot6: {state.pivot6:.6f}")
                    logger.info(f"   - last_eight_bar_idx: {state.last_eight_bar_idx}")
                    logger.info(f"   - last_eight_up: {state.last_eight_up}")
                    logger.info(f"   - last_eight_down: {state.last_eight_down}")
                    
                    # Manual check CHoCH conditions
                    logger.info(f"\n   CHoCH Up Conditions Check:")
                    logger.info(f"   - prev['low'] > pre_prev['low']: {prev['low']:.6f} > {pre_prev['low']:.6f} = {prev['low'] > pre_prev['low']}")
                    logger.info(f"   - prev['close'] > pre_prev['high']: {prev['close']:.6f} > {pre_prev['high']:.6f} = {prev['close'] > pre_prev['high']}")
                    logger.info(f"   - prev['close'] > pivot6: {prev['close']:.6f} > {state.pivot6:.6f} = {prev['close'] > state.pivot6}")
                    
                    # Get p2 from 8 pivots
                    if state.pivot_count() >= 8:
                        _, p2, _ = state.get_pivot_from_end(6)
                        logger.info(f"   - prev['close'] < p2: {prev['close']:.6f} < {p2:.6f} = {prev['close'] < p2}")
                        
                        choch_up_bar = (prev['low'] > pre_prev['low'] and 
                                       prev['close'] > pre_prev['high'] and 
                                       prev['close'] > state.pivot6 and
                                       prev['close'] < p2)
                        
                        logger.info(f"   → choch_up_bar: {choch_up_bar}")
                        
                        # Confirmation check
                        confirm_up_basic = (current['close'] > pre_prev['high'])
                        logger.info(f"\n   Confirmation Check:")
                        logger.info(f"   - current['close'] > pre_prev['high']: {current['close']:.6f} > {pre_prev['high']:.6f} = {confirm_up_basic}")
                        
                        # Base condition
                        is_after_eight = target_time > state.last_eight_bar_idx
                        logger.info(f"   - is_after_eight: {target_time} > {state.last_eight_bar_idx} = {is_after_eight}")
                        
                        base_up = is_after_eight and state.last_eight_down and choch_up_bar and confirm_up_basic
                        logger.info(f"   - base_up: {is_after_eight} AND {state.last_eight_down} AND {choch_up_bar} AND {confirm_up_basic} = {base_up}")
        else:
            logger.info(f"   ❌ Candle not found in dataframe")
    except Exception as e:
        logger.error(f"   Error checking candle: {e}", exc_info=True)
    
    # Cleanup
    await fetcher.close()
    
    logger.info("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_xrp_15m())
