"""
Analyze candle opening times to determine the alignment pattern
"""
from datetime import datetime, timedelta

# Reference candle opening times provided (UTC)
reference_times = {
    '25m': datetime(2025, 10, 24, 17, 5),   # 24-10-2025 17:05
    '40m': datetime(2025, 10, 24, 16, 40),  # 24-10-2025 16:40
    '10m': datetime(2025, 10, 24, 17, 10),  # 24-10-2025 17:10
    '20m': datetime(2025, 10, 24, 17, 20),  # 24-10-2025 17:20
}

print("=" * 80)
print("CANDLE ALIGNMENT ANALYSIS")
print("=" * 80)
print()

for tf, ref_time in reference_times.items():
    minutes = int(tf[:-1])
    
    print(f"\n{tf.upper()} TIMEFRAME (interval: {minutes} minutes)")
    print("-" * 60)
    print(f"Reference opening time: {ref_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Hour: {ref_time.hour}, Minute: {ref_time.minute}")
    
    # Calculate offset from midnight
    midnight = ref_time.replace(hour=0, minute=0, second=0)
    total_minutes = (ref_time - midnight).total_seconds() / 60
    offset_minutes = total_minutes % minutes
    
    print(f"  Minutes since midnight: {total_minutes:.0f}")
    print(f"  Offset from {minutes}m boundary: {offset_minutes:.0f} minutes")
    
    # Generate next few candle times to verify pattern
    print(f"\n  Next 5 candle opening times:")
    for i in range(5):
        next_time = ref_time + timedelta(minutes=minutes * i)
        print(f"    {i+1}. {next_time.strftime('%H:%M')} (minute: {next_time.minute})")
    
    # Calculate the base offset (first candle of the day)
    first_candle_minute = int(offset_minutes)
    print(f"\n  Base offset from midnight: {first_candle_minute} minutes")
    print(f"  Pattern: Candles open at minutes: {first_candle_minute}, {first_candle_minute + minutes}, {first_candle_minute + 2*minutes}, ...")

print("\n" + "=" * 80)
print("SUMMARY - Offset Configuration for Each Timeframe")
print("=" * 80)

offsets = {}
for tf, ref_time in reference_times.items():
    minutes = int(tf[:-1])
    midnight = ref_time.replace(hour=0, minute=0, second=0)
    total_minutes = (ref_time - midnight).total_seconds() / 60
    offset_minutes = int(total_minutes % minutes)
    offsets[tf] = offset_minutes
    print(f"{tf:6} -> offset: {offset_minutes:2d} minutes (candles open at minute % {minutes} == {offset_minutes})")

print("\n" + "=" * 80)
print("VERIFICATION - Check if pattern holds")
print("=" * 80)

# Verify with actual 5m base candles
print("\nAssuming we fetch 5m candles from Binance (aligned to :00, :05, :10, :15, ...):")
print()

for tf, offset in offsets.items():
    minutes = int(tf[:-1])
    print(f"\n{tf.upper()} (offset={offset}m, interval={minutes}m):")
    
    # For aggregation, we need to find which 5m candles to combine
    # If offset is 5m and interval is 25m, we need candles at: 5, 10, 15, 20, 25 (next period)
    
    # Calculate which 5m candle indices to start from
    # 5m candles are at minutes: 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55
    # For 25m with offset 5: should start at 5, then combine 5,10,15,20,25 -> next starts at 30
    
    num_5m_candles = minutes // 5
    print(f"  Needs {num_5m_candles} x 5m candles per {tf} candle")
    print(f"  First {tf} candle starts at minute {offset}")
    
    # Show grouping for first few periods
    print(f"  5m candle groupings:")
    for period in range(3):
        start_minute = offset + (period * minutes)
        candle_minutes = [(start_minute + i*5) % 60 for i in range(num_5m_candles)]
        hour_offset = (start_minute + (num_5m_candles-1)*5) // 60
        print(f"    Period {period+1}: 5m candles at minutes {candle_minutes} (hour +{hour_offset})")

print("\n" + "=" * 80)
