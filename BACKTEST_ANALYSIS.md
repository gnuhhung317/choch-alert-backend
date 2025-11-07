# Backtest Analysis Tool

## Overview
This tool provides comprehensive analysis of CHoCH strategy backtest results. It processes backtest summary CSV files and generates detailed statistics, charts, and filtered exports.

## Features

### 📊 Statistical Analysis
- **Overall Performance**: Win rate, profit factor, total P&L, risk/reward ratio
- **Distribution Analysis**: Win rate ranges, trade count impact, profitability distribution
- **Timeframe Comparison**: Performance breakdown by 30m and 1h timeframes
- **Consistency Analysis**: Identifies reliable performers with multiple trades

### 🏆 Performance Ranking
- **Top Performers**: Best performing pairs by total P&L
- **Worst Performers**: Pairs with biggest losses
- **Perfect Win Rate**: All pairs with 100% win rate
- **Zero Win Rate**: All pairs with 0% win rate
- **Consistent Performers**: Pairs with 3+ trades, 60%+ WR, and profitable

### 📈 Visual Analytics
- P&L distribution histogram
- Win rate distribution
- Win rate vs P&L scatter plot
- Trade count distribution
- Timeframe comparison charts

### 📁 Filtered Exports
- Profitable pairs only
- Unprofitable pairs only
- High win rate pairs (≥70%)
- Consistent performers

## Usage

### Command Line

```bash
# Analyze specific file
python analyze_backtest.py io/output/backtest_SUMMARY_20251105_211313.csv

# Use default/latest file
python analyze_backtest.py

# Customize output
python analyze_backtest.py --top 20 --no-charts --no-export
```

### Windows Batch File

```cmd
# Run with automatic file detection
analyze_backtest.bat

# Run with specific file
analyze_backtest.bat io\output\backtest_SUMMARY_20251105_211313.csv
```

### Options

- `--top N`: Show top/bottom N performers (default: 10)
- `--no-charts`: Skip chart generation
- `--no-export`: Skip filtered CSV exports

## Output Files

All output files are saved to `io/output/` directory:

### Charts
- `backtest_analysis_YYYYMMDD_HHMMSS.png` - Main analysis charts (4 subplots)
- `timeframe_analysis_YYYYMMDD_HHMMSS.png` - Timeframe comparison charts

### Filtered CSVs
- `profitable_pairs_YYYYMMDD_HHMMSS.csv` - All profitable pairs
- `unprofitable_pairs_YYYYMMDD_HHMMSS.csv` - All unprofitable pairs
- `high_winrate_pairs_YYYYMMDD_HHMMSS.csv` - Pairs with ≥70% win rate
- `consistent_performers_YYYYMMDD_HHMMSS.csv` - 3+ trades, 60%+ WR, profitable

## Analysis Sections

### 1. Overall Statistics
- Total pairs, trades, wins, losses
- Overall win rate
- Total and average P&L
- Risk/reward ratio and profit factor
- Maximum and average drawdown

### 2. Performance by Timeframe
- Separate statistics for 30m and 1h timeframes
- Trade distribution
- Win rate comparison
- P&L breakdown

### 3. Top/Bottom Performers
- Ranked by total P&L
- Shows win rate, profit factor, and key metrics
- Configurable number of results (default: 10)

### 4. Win Rate Distribution
- Categorized into 0-25%, 25-50%, 50-75%, 75-100%
- Shows pair count, total trades, and total P&L per category

### 5. Trade Count Analysis
- Groups pairs by number of trades (1, 2, 3, 4-5, 6+)
- Shows win rate and average P&L per group
- Identifies if more trades = better consistency

### 6. Perfect Win Rate Pairs
- All pairs with 100% win rate
- Distribution by trade count
- Top 10 by P&L

### 7. Zero Win Rate Pairs
- All pairs with 0% win rate
- Distribution by trade count
- Worst 10 by loss amount

### 8. Consistency Analysis
- Focuses on pairs with 3+ trades
- Filters for 60%+ win rate and profitability
- Identifies most reliable trading pairs

## Example Analysis Output

```
================================================================================
BACKTEST ANALYSIS SUMMARY
================================================================================

📊 OVERALL STATISTICS:
  Total Trading Pairs: 396
  Total Trades: 542
  Winning Trades: 401
  Losing Trades: 141
  Overall Win Rate: 73.99%

💰 PROFITABILITY:
  Total P&L: +288.37%
  Average P&L per Pair: +0.73%
  Average Win: +1.21%
  Average Loss: -1.39%
  Risk/Reward Ratio: 1:0.87
  Profit Factor: 3.82

📈 DISTRIBUTION:
  Profitable Pairs: 293 (74.0%)
  Unprofitable Pairs: 103 (26.0%)
```

## Key Insights from Sample Data

Based on the analysis of XPINUSDT and the full market backtest:

### Strategy Performance
- **Win Rate**: 74% overall (very strong)
- **Profit Factor**: 3.82 (excellent - for every $1 lost, $3.82 is gained)
- **Average Win**: 1.21% per trade
- **Average Loss**: 1.39% per trade
- **Risk/Reward**: Slightly negative (1:0.87) but compensated by high win rate

### Best Performers
1. **XPINUSDT (1h)**: +34.16% in 1 trade - exceptional
2. **ZENUSDT (1h)**: +7.13% across 4 trades (75% WR) - consistent
3. **VIRTUALUSDT (30m)**: +5.61% across 4 trades (100% WR) - perfect

### Timeframe Analysis
- **30m**: 75.6% win rate, +137.51% total P&L
- **1h**: 72.2% win rate, +150.86% total P&L
- Both timeframes perform well, with 1h slightly higher total P&L

### Trade Distribution
- 75% of pairs with 1 trade have positive P&L
- Higher trade counts (4-5 trades) show better average P&L (+3.60%)
- 265 pairs achieved perfect 100% win rate

## Dependencies

```bash
pip install pandas numpy matplotlib seaborn
```

## Integration with Backtest Bot

This tool is designed to work with `backtest_bot.py` output:

1. Run backtest: `python backtest_bot.py`
2. Wait for completion (generates `backtest_SUMMARY_*.csv`)
3. Run analysis: `python analyze_backtest.py`
4. Review charts and filtered exports in `io/output/`

## Tips for Interpretation

### Good Signs
- ✅ Win rate > 60%
- ✅ Profit factor > 2.0
- ✅ Consistent performance across multiple trades
- ✅ Risk/reward ratio > 1:1 or high win rate compensating

### Warning Signs
- ⚠️ Win rate < 40%
- ⚠️ Profit factor < 1.5
- ⚠️ High drawdowns (>5%)
- ⚠️ Negative P&L on consistent performers

### Optimization Ideas
Based on analysis results, you can:
1. Filter pairs based on high win rate timeframes
2. Focus on consistent performers (3+ trades, 60%+ WR)
3. Exclude pairs with 0% win rate from live trading
4. Adjust entry/exit rules for pairs with poor risk/reward

## Future Enhancements

Potential additions:
- [ ] Pattern group analysis (G1, G2, G3 breakdown)
- [ ] Entry point analysis (Entry1 vs Entry2 fill rates)
- [ ] Time-of-day performance analysis
- [ ] Correlation analysis between pairs
- [ ] Monte Carlo simulation for risk assessment
- [ ] Real-time dashboard with live updates

## License

Part of CHoCH Alert Backend system - see main LICENSE file.
