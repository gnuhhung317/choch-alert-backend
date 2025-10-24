#!/usr/bin/env python3
"""
Detailed analysis of 25m candle timing
"""
from datetime import datetime, timedelta

# 25m candles: mỗi nến kéo dài 25 phút
# Pattern trong 1 giờ: không chia đều (25 + 25 = 50, còn 10 phút)
# Pattern trong 5 giờ: 12 nến × 25m = 300 phút = 5 giờ (chu kỳ lặp lại)

# Starting from midnight (00:00):
start = datetime(2025, 10, 23, 0, 0, 0)
print("25m candle boundaries (first 20 candles from 00:00):")
print("="*60)

for i in range(20):
    candle_start = start + timedelta(minutes=25*i)
    candle_end = candle_start + timedelta(minutes=25)
    print(f"Candle {i+1:2}: {candle_start.strftime('%H:%M')} - {candle_end.strftime('%H:%M')}")

print("\n" + "="*60)
print("At 16:23:34, which candle are we in?")
print("="*60)

current = datetime(2025, 10, 23, 16, 23, 34)
minutes_since_midnight = current.hour * 60 + current.minute + current.second / 60
candle_number = int(minutes_since_midnight // 25)
candle_start = start + timedelta(minutes=25*candle_number)
candle_end = candle_start + timedelta(minutes=25)

print(f"Current time: {current.strftime('%H:%M:%S')}")
print(f"Minutes since midnight: {minutes_since_midnight:.2f}")
print(f"Candle number: {candle_number + 1}")
print(f"Current candle: {candle_start.strftime('%H:%M')} - {candle_end.strftime('%H:%M')} (OPEN)")
print(f"Previous closed candle: {(candle_start - timedelta(minutes=25)).strftime('%H:%M')} - {candle_start.strftime('%H:%M')} (CLOSED)")

print("\n" + "="*60)
print("Expected values at 16:23:34:")
print("="*60)
print(f"prev_close should be: {candle_start.strftime('%H:%M:%S')} (start of current candle = end of previous)")
print(f"next_close should be: {candle_end.strftime('%H:%M:%S')} (end of current candle)")
print(f"should_scan: False (current candle not closed yet)")
