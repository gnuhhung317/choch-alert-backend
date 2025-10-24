"""
Verify alignment pattern - Check if timeframes align with midnight
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
print("VERIFY ALIGNMENT WITH MIDNIGHT")
print("=" * 80)

for tf, ref_time in reference_times.items():
    minutes = int(tf[:-1])
    
    print(f"\n{tf.upper()} TIMEFRAME")
    print("-" * 60)
    
    # Check if 1440 (24h) is divisible by interval
    can_align_midnight = (1440 % minutes == 0)
    print(f"Can align with midnight? {can_align_midnight} (1440 % {minutes} = {1440 % minutes})")
    
    if not can_align_midnight:
        print(f"⚠️  WARNING: 24 hours NOT divisible by {minutes} minutes!")
        print(f"   This means candles DON'T reset at midnight each day")
        print(f"   Need to track offset from a FIXED reference point!")
    
    # Calculate actual pattern by going backwards from reference time
    print(f"\nReference time: {ref_time.strftime('%Y-%m-%d %H:%M')}")
    
    # Go backwards to find the pattern
    print(f"\nGoing backwards from reference time:")
    current = ref_time
    for i in range(10):
        prev = current - timedelta(minutes=minutes)
        print(f"  {prev.strftime('%Y-%m-%d %H:%M')} (day: {prev.day}, minute: {prev.minute})")
        current = prev
        
        # Check if we crossed midnight
        if prev.day != ref_time.day:
            print(f"  ^^^ Crossed midnight! Day changed from {ref_time.day} to {prev.day}")
            
            # What minute did we land on after crossing midnight?
            print(f"  After midnight crossing: minute = {prev.minute}")
            break
    
    # Try to find pattern relative to some fixed point
    # Use Unix epoch or specific date as reference
    epoch = datetime(1970, 1, 1, 0, 0, 0)
    total_minutes_from_epoch = int((ref_time - epoch).total_seconds() / 60)
    offset_from_epoch = total_minutes_from_epoch % minutes
    
    print(f"\nOffset from epoch (1970-01-01 00:00): {offset_from_epoch} minutes")
    
    # Better: use a recent Monday 00:00 as reference
    # Find the Monday of the reference week
    days_since_monday = ref_time.weekday()  # 0=Monday, 6=Sunday
    monday = ref_time.replace(hour=0, minute=0, second=0) - timedelta(days=days_since_monday)
    
    total_minutes_from_monday = int((ref_time - monday).total_seconds() / 60)
    offset_from_monday = total_minutes_from_monday % minutes
    
    print(f"Monday of reference week: {monday.strftime('%Y-%m-%d %H:%M')}")
    print(f"Offset from that Monday 00:00: {offset_from_monday} minutes")
    
    # Try specific reference: 2025-10-20 00:00 (Monday before reference date)
    fixed_ref = datetime(2025, 10, 20, 0, 0, 0)
    total_minutes_from_ref = int((ref_time - fixed_ref).total_seconds() / 60)
    offset_from_ref = total_minutes_from_ref % minutes
    
    print(f"\nOffset from 2025-10-20 00:00: {offset_from_ref} minutes")
    
    # Verify by generating future candles
    print(f"\nNext 5 candles from reference time:")
    for i in range(5):
        next_time = ref_time + timedelta(minutes=minutes * i)
        print(f"  {next_time.strftime('%Y-%m-%d %H:%M')} (day: {next_time.day}, minute: {next_time.minute})")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

print("\nTimeframes that CAN align with midnight (1440 % interval == 0):")
for tf in reference_times.keys():
    minutes = int(tf[:-1])
    if 1440 % minutes == 0:
        print(f"  ✓ {tf}")

print("\nTimeframes that CANNOT align with midnight:")
for tf in reference_times.keys():
    minutes = int(tf[:-1])
    if 1440 % minutes != 0:
        print(f"  ✗ {tf} - need fixed reference point")

print("\n" + "=" * 80)
print("SOLUTION")
print("=" * 80)
print("""
For timeframes that don't divide evenly into 24h (25m, 40m):
- Cannot use midnight as reference point
- Must use a FIXED DATETIME as reference (e.g., the provided reference time)
- Calculate offset from that fixed reference point
- All future/past candles are calculated from this reference

Example for 25m:
- Reference: 2025-10-24 17:05:00
- Candle N: ref_time + (N × 25 minutes)
- Candle -N: ref_time - (N × 25 minutes)

This ensures PERFECT alignment with exchange candles regardless of time wrap-around.
""")
