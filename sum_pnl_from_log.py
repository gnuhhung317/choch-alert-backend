"""
Simple script to sum Total P&L values from backtest log file

Usage:
    python sum_pnl_from_log.py backtest.log
    python sum_pnl_from_log.py your_log_file.txt
"""
import sys
import re


def extract_pnl_from_log(log_file):
    """
    Extract all 'Total P&L' values from log file
    
    Args:
        log_file: Path to log file
        
    Returns:
        List of (timestamp, pnl_value, line) tuples
    """
    pnl_entries = []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Match pattern: "Total P&L: +0.16%" or "Total P&L: -0.11%"
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*:\s*([+-]?\d+\.\d+)%', line)
                
                if match:
                    timestamp = match.group(1)
                    pnl_value = float(match.group(2))
                    pnl_entries.append((timestamp, pnl_value, line.strip()))
    
    except FileNotFoundError:
        print(f"❌ Error: File '{log_file}' not found!")
        return []
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return []
    
    return pnl_entries


def main():
    """Main function"""
    log_file = "test.txt"
    
    print("="*80)
    print("TOTAL P&L CALCULATOR FROM LOG")
    print("="*80)
    print(f"Reading log file: {log_file}\n")
    
    # Extract P&L entries
    pnl_entries = extract_pnl_from_log(log_file)
    
    if not pnl_entries:
        print("No 'Total P&L' entries found in log file!")
        return
    
    print(f"Found {len(pnl_entries)} P&L entries:\n")
    print("-"*80)
    
    # Display all entries
    for i, (timestamp, pnl, line) in enumerate(pnl_entries, 1):
        print(f"{i:3d}. {timestamp} - Total P&L: {pnl:+.2f}%")
    
    print("-"*80)
    
    # Calculate statistics
    total_sum = sum(pnl for _, pnl, _ in pnl_entries)
    average = total_sum / len(pnl_entries)
    positive_count = sum(1 for _, pnl, _ in pnl_entries if pnl > 0)
    negative_count = sum(1 for _, pnl, _ in pnl_entries if pnl < 0)
    max_pnl = max(pnl for _, pnl, _ in pnl_entries)
    min_pnl = min(pnl for _, pnl, _ in pnl_entries)
    
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"Total Entries:     {len(pnl_entries)}")
    print(f"Positive P&L:      {positive_count}")
    print(f"Negative/Zero P&L: {negative_count}")
    print("-"*80)
    print(f"Sum of All P&L:    {total_sum:+.2f}%")
    print(f"Average P&L:       {average:+.2f}%")
    print(f"Max P&L:           {max_pnl:+.2f}%")
    print(f"Min P&L:           {min_pnl:+.2f}%")
    print("="*80)
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("1. This sum may NOT represent actual portfolio performance!")
    print("2. Each entry might be from DIFFERENT symbol/timeframe combinations")
    print("3. For accurate portfolio P&L, use the full backtest CSV output")
    print("4. This is just a simple arithmetic sum for reference\n")


if __name__ == '__main__':
    main()
