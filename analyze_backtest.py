"""
Backtest Trade Analysis Tool
Analyzes trading performance from backtest results
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Configure matplotlib for Vietnamese fonts
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['axes.unicode_minus'] = False

class BacktestAnalyzer:
    """Comprehensive backtest analysis"""
    
    def __init__(self, summary_file: str):
        """
        Initialize analyzer with backtest summary file
        
        Args:
            summary_file: Path to CSV summary file
        """
        self.summary_file = summary_file
        self.df = None
        self.load_data()
    
    def load_data(self):
        """Load backtest summary data"""
        try:
            self.df = pd.read_csv(self.summary_file)
            print(f"✓ Loaded {len(self.df)} trading pairs")
            print(f"  Columns: {', '.join(self.df.columns)}")
        except Exception as e:
            print(f"✗ Error loading data: {e}")
            sys.exit(1)
    
    def print_summary_statistics(self):
        """Print overall summary statistics"""
        print("\n" + "="*80)
        print("BACKTEST ANALYSIS SUMMARY")
        print("="*80)
        
        # Overall statistics
        total_pairs = len(self.df)
        total_trades = self.df['total_trades'].sum()
        total_wins = self.df['winning_trades'].sum()
        total_losses = self.df['losing_trades'].sum()
        
        overall_win_rate = total_wins / total_trades if total_trades > 0 else 0
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"  Total Trading Pairs: {total_pairs}")
        print(f"  Total Trades: {total_trades}")
        print(f"  Winning Trades: {total_wins}")
        print(f"  Losing Trades: {total_losses}")
        print(f"  Overall Win Rate: {overall_win_rate:.2%}")
        
        # Performance metrics
        total_pnl = self.df['total_pnl_pct'].sum()
        avg_pnl_per_pair = self.df['total_pnl_pct'].mean()
        
        # Calculate weighted averages
        winners = self.df[self.df['winning_trades'] > 0]
        losers = self.df[self.df['losing_trades'] > 0]
        
        if len(winners) > 0:
            avg_win_pct = (winners['avg_win_pct'] * winners['winning_trades']).sum() / total_wins
        else:
            avg_win_pct = 0
        
        if len(losers) > 0:
            avg_loss_pct = (losers['avg_loss_pct'] * losers['losing_trades']).sum() / total_losses
        else:
            avg_loss_pct = 0
        
        print(f"\n💰 PROFITABILITY:")
        print(f"  Total P&L: {total_pnl:+.2f}%")
        print(f"  Average P&L per Pair: {avg_pnl_per_pair:+.2f}%")
        print(f"  Average Win: {avg_win_pct:+.2f}%")
        print(f"  Average Loss: {avg_loss_pct:+.2f}%")
        
        # Risk-reward ratio
        if avg_loss_pct != 0:
            risk_reward = abs(avg_win_pct / avg_loss_pct)
            print(f"  Risk/Reward Ratio: 1:{risk_reward:.2f}")
        
        # Profit factor
        gross_profit = winners['total_pnl_pct'].sum()
        gross_loss = abs(losers['total_pnl_pct'].sum())
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
            print(f"  Profit Factor: {profit_factor:.2f}")
        
        # Distribution analysis
        profitable_pairs = len(self.df[self.df['total_pnl_pct'] > 0])
        unprofitable_pairs = len(self.df[self.df['total_pnl_pct'] <= 0])
        
        print(f"\n📈 DISTRIBUTION:")
        print(f"  Profitable Pairs: {profitable_pairs} ({profitable_pairs/total_pairs*100:.1f}%)")
        print(f"  Unprofitable Pairs: {unprofitable_pairs} ({unprofitable_pairs/total_pairs*100:.1f}%)")
        
        # Max drawdown
        max_dd = self.df['max_drawdown_pct'].max()
        avg_dd = self.df['max_drawdown_pct'].mean()
        print(f"\n⚠️  RISK METRICS:")
        print(f"  Maximum Drawdown: {max_dd:.2f}%")
        print(f"  Average Drawdown: {avg_dd:.2f}%")
        
        print("="*80)
    
    def analyze_by_timeframe(self):
        """Analyze performance by timeframe"""
        print("\n" + "="*80)
        print("PERFORMANCE BY TIMEFRAME")
        print("="*80)
        
        for tf in sorted(self.df['timeframe'].unique()):
            tf_data = self.df[self.df['timeframe'] == tf]
            
            total_trades = tf_data['total_trades'].sum()
            total_wins = tf_data['winning_trades'].sum()
            total_losses = tf_data['losing_trades'].sum()
            win_rate = total_wins / total_trades if total_trades > 0 else 0
            total_pnl = tf_data['total_pnl_pct'].sum()
            avg_pnl = tf_data['total_pnl_pct'].mean()
            
            print(f"\n⏱️  {tf.upper()}:")
            print(f"  Pairs: {len(tf_data)}")
            print(f"  Total Trades: {total_trades}")
            print(f"  Win Rate: {win_rate:.2%}")
            print(f"  Total P&L: {total_pnl:+.2f}%")
            print(f"  Avg P&L per Pair: {avg_pnl:+.2f}%")
        
        print("="*80)
    
    def get_top_performers(self, n: int = 10) -> pd.DataFrame:
        """Get top performing pairs"""
        return self.df.nlargest(n, 'total_pnl_pct')
    
    def get_worst_performers(self, n: int = 10) -> pd.DataFrame:
        """Get worst performing pairs"""
        return self.df.nsmallest(n, 'total_pnl_pct')
    
    def print_top_performers(self, n: int = 10):
        """Print top performing pairs"""
        print(f"\n{'='*80}")
        print(f"TOP {n} PERFORMERS")
        print("="*80)
        
        top = self.get_top_performers(n)
        
        for i, (_, row) in enumerate(top.iterrows(), 1):
            print(f"\n{i}. {row['symbol']} ({row['timeframe']})")
            print(f"   Trades: {int(row['total_trades'])} | Win Rate: {row['win_rate']:.1%} | P&L: {row['total_pnl_pct']:+.2f}%")
            print(f"   Avg Win: {row['avg_win_pct']:+.2f}% | Avg Loss: {row['avg_loss_pct']:+.2f}%")
            if row['profit_factor'] == float('inf'):
                print(f"   Profit Factor: ∞ (no losses)")
            else:
                print(f"   Profit Factor: {row['profit_factor']:.2f}")
        
        print("="*80)
    
    def print_worst_performers(self, n: int = 10):
        """Print worst performing pairs"""
        print(f"\n{'='*80}")
        print(f"BOTTOM {n} PERFORMERS")
        print("="*80)
        
        worst = self.get_worst_performers(n)
        
        for i, (_, row) in enumerate(worst.iterrows(), 1):
            print(f"\n{i}. {row['symbol']} ({row['timeframe']})")
            print(f"   Trades: {int(row['total_trades'])} | Win Rate: {row['win_rate']:.1%} | P&L: {row['total_pnl_pct']:+.2f}%")
            print(f"   Avg Win: {row['avg_win_pct']:+.2f}% | Avg Loss: {row['avg_loss_pct']:+.2f}%")
            if row['profit_factor'] == 0:
                print(f"   Profit Factor: 0 (no wins)")
            else:
                print(f"   Profit Factor: {row['profit_factor']:.2f}")
        
        print("="*80)
    
    def analyze_win_rate_distribution(self):
        """Analyze win rate distribution"""
        print("\n" + "="*80)
        print("WIN RATE DISTRIBUTION")
        print("="*80)
        
        bins = [0, 0.25, 0.5, 0.75, 1.0]
        labels = ['0-25%', '25-50%', '50-75%', '75-100%']
        
        self.df['wr_category'] = pd.cut(self.df['win_rate'], bins=bins, labels=labels, include_lowest=True)
        
        distribution = self.df.groupby('wr_category', observed=True).agg({
            'symbol': 'count',
            'total_trades': 'sum',
            'total_pnl_pct': 'sum'
        }).rename(columns={'symbol': 'pair_count'})
        
        print("\nWin Rate Range | Pairs | Total Trades | Total P&L")
        print("-" * 60)
        for category, row in distribution.iterrows():
            print(f"{category:14} | {int(row['pair_count']):5} | {int(row['total_trades']):12} | {row['total_pnl_pct']:+9.2f}%")
        
        print("="*80)
    
    def analyze_trade_count_impact(self):
        """Analyze impact of trade count on profitability"""
        print("\n" + "="*80)
        print("TRADE COUNT ANALYSIS")
        print("="*80)
        
        # Group by trade count ranges
        bins = [0, 1, 2, 3, 5, float('inf')]
        labels = ['1 trade', '2 trades', '3 trades', '4-5 trades', '6+ trades']
        
        self.df['trade_category'] = pd.cut(self.df['total_trades'], bins=bins, labels=labels)
        
        distribution = self.df.groupby('trade_category', observed=True).agg({
            'symbol': 'count',
            'total_trades': 'sum',
            'winning_trades': 'sum',
            'losing_trades': 'sum',
            'total_pnl_pct': ['sum', 'mean']
        })
        
        print("\nTrade Count | Pairs | Total Trades | Wins | Losses | Win Rate | Avg P&L")
        print("-" * 80)
        for category in distribution.index:
            row = distribution.loc[category]
            pairs = int(row[('symbol', 'count')])
            total = int(row[('total_trades', 'sum')])
            wins = int(row[('winning_trades', 'sum')])
            losses = int(row[('losing_trades', 'sum')])
            wr = wins / total if total > 0 else 0
            total_pnl = row[('total_pnl_pct', 'sum')]
            avg_pnl = row[('total_pnl_pct', 'mean')]
            
            print(f"{category:11} | {pairs:5} | {total:12} | {wins:4} | {losses:6} | {wr:8.1%} | {avg_pnl:+7.2f}%")
        
        print("="*80)
    
    def find_perfect_pairs(self):
        """Find pairs with 100% win rate"""
        perfect = self.df[self.df['win_rate'] == 1.0].sort_values('total_pnl_pct', ascending=False)
        
        if len(perfect) > 0:
            print(f"\n{'='*80}")
            print(f"PERFECT WIN RATE PAIRS (100%)")
            print("="*80)
            print(f"\nFound {len(perfect)} pairs with 100% win rate")
            print(f"Combined P&L: {perfect['total_pnl_pct'].sum():+.2f}%")
            
            # Group by trade count
            print("\nDistribution by trade count:")
            for trades in sorted(perfect['total_trades'].unique()):
                subset = perfect[perfect['total_trades'] == trades]
                avg_pnl = subset['total_pnl_pct'].mean()
                print(f"  {int(trades)} trade(s): {len(subset)} pairs, Avg P&L: {avg_pnl:+.2f}%")
            
            print("\nTop 10 by P&L:")
            for i, (_, row) in enumerate(perfect.head(10).iterrows(), 1):
                print(f"  {i}. {row['symbol']:15} {row['timeframe']:4} | {int(row['total_trades'])} trades | {row['total_pnl_pct']:+6.2f}%")
            
            print("="*80)
    
    def find_zero_win_pairs(self):
        """Find pairs with 0% win rate"""
        losers = self.df[self.df['win_rate'] == 0.0].sort_values('total_pnl_pct')
        
        if len(losers) > 0:
            print(f"\n{'='*80}")
            print(f"ZERO WIN RATE PAIRS (0%)")
            print("="*80)
            print(f"\nFound {len(losers)} pairs with 0% win rate")
            print(f"Combined Loss: {losers['total_pnl_pct'].sum():+.2f}%")
            
            # Group by trade count
            print("\nDistribution by trade count:")
            for trades in sorted(losers['total_trades'].unique()):
                subset = losers[losers['total_trades'] == trades]
                avg_loss = subset['total_pnl_pct'].mean()
                print(f"  {int(trades)} trade(s): {len(subset)} pairs, Avg Loss: {avg_loss:+.2f}%")
            
            print("\nWorst 10 by loss:")
            for i, (_, row) in enumerate(losers.head(10).iterrows(), 1):
                print(f"  {i}. {row['symbol']:15} {row['timeframe']:4} | {int(row['total_trades'])} trades | {row['total_pnl_pct']:+6.2f}%")
            
            print("="*80)
    
    def analyze_consistency(self):
        """Analyze trading consistency"""
        print("\n" + "="*80)
        print("CONSISTENCY ANALYSIS")
        print("="*80)
        
        # Filter pairs with multiple trades
        multi_trade = self.df[self.df['total_trades'] >= 3].copy()
        
        if len(multi_trade) > 0:
            print(f"\nAnalyzing {len(multi_trade)} pairs with 3+ trades...")
            
            # Sort by win rate and profit factor
            consistent = multi_trade[
                (multi_trade['win_rate'] >= 0.6) & 
                (multi_trade['total_pnl_pct'] > 0)
            ].sort_values('total_pnl_pct', ascending=False)
            
            print(f"\nConsistent performers (60%+ WR, profitable):")
            print(f"  Found: {len(consistent)} pairs")
            
            if len(consistent) > 0:
                print(f"  Combined P&L: {consistent['total_pnl_pct'].sum():+.2f}%")
                print(f"  Average Win Rate: {consistent['win_rate'].mean():.1%}")
                print(f"\n  Top 10:")
                for i, (_, row) in enumerate(consistent.head(10).iterrows(), 1):
                    print(f"    {i}. {row['symbol']:15} {row['timeframe']:4} | "
                          f"WR: {row['win_rate']:.0%} | Trades: {int(row['total_trades'])} | "
                          f"P&L: {row['total_pnl_pct']:+6.2f}%")
        else:
            print("\n⚠️  Not enough multi-trade pairs for consistency analysis")
        
        print("="*80)
    
    def generate_charts(self, output_dir: str = "io/output"):
        """Generate analysis charts"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*80}")
        print("GENERATING CHARTS")
        print("="*80)
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # 1. P&L Distribution
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # P&L histogram
        axes[0, 0].hist(self.df['total_pnl_pct'], bins=50, edgecolor='black', alpha=0.7)
        axes[0, 0].axvline(0, color='red', linestyle='--', linewidth=2)
        axes[0, 0].set_xlabel('Total P&L (%)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('P&L Distribution')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Win rate histogram
        axes[0, 1].hist(self.df['win_rate'] * 100, bins=20, edgecolor='black', alpha=0.7, color='green')
        axes[0, 1].set_xlabel('Win Rate (%)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('Win Rate Distribution')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Win rate vs P&L scatter
        axes[1, 0].scatter(self.df['win_rate'] * 100, self.df['total_pnl_pct'], alpha=0.5)
        axes[1, 0].axhline(0, color='red', linestyle='--', linewidth=1)
        axes[1, 0].set_xlabel('Win Rate (%)')
        axes[1, 0].set_ylabel('Total P&L (%)')
        axes[1, 0].set_title('Win Rate vs P&L')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Trade count distribution
        trade_counts = self.df['total_trades'].value_counts().sort_index()
        axes[1, 1].bar(trade_counts.index, trade_counts.values, edgecolor='black', alpha=0.7)
        axes[1, 1].set_xlabel('Number of Trades')
        axes[1, 1].set_ylabel('Number of Pairs')
        axes[1, 1].set_title('Trade Count Distribution')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        chart_file = f"{output_dir}/backtest_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved chart: {chart_file}")
        plt.close()
        
        # 2. Timeframe comparison
        tf_data = self.df.groupby('timeframe').agg({
            'total_trades': 'sum',
            'winning_trades': 'sum',
            'losing_trades': 'sum',
            'total_pnl_pct': 'sum'
        })
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Trade distribution by timeframe
        tf_data[['winning_trades', 'losing_trades']].plot(kind='bar', ax=axes[0], 
                                                           color=['green', 'red'], alpha=0.7)
        axes[0].set_xlabel('Timeframe')
        axes[0].set_ylabel('Number of Trades')
        axes[0].set_title('Win/Loss Distribution by Timeframe')
        axes[0].legend(['Wins', 'Losses'])
        axes[0].grid(True, alpha=0.3)
        axes[0].tick_params(axis='x', rotation=0)
        
        # P&L by timeframe
        tf_data['total_pnl_pct'].plot(kind='bar', ax=axes[1], 
                                      color=['green' if x > 0 else 'red' for x in tf_data['total_pnl_pct']],
                                      alpha=0.7)
        axes[1].axhline(0, color='black', linestyle='-', linewidth=1)
        axes[1].set_xlabel('Timeframe')
        axes[1].set_ylabel('Total P&L (%)')
        axes[1].set_title('Profitability by Timeframe')
        axes[1].grid(True, alpha=0.3)
        axes[1].tick_params(axis='x', rotation=0)
        
        plt.tight_layout()
        tf_chart = f"{output_dir}/timeframe_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(tf_chart, dpi=300, bbox_inches='tight')
        print(f"✓ Saved chart: {tf_chart}")
        plt.close()
        
        print("="*80)
    
    def export_filtered_results(self, output_dir: str = "io/output"):
        """Export filtered results"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*80}")
        print("EXPORTING FILTERED RESULTS")
        print("="*80)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export profitable pairs
        profitable = self.df[self.df['total_pnl_pct'] > 0].sort_values('total_pnl_pct', ascending=False)
        if len(profitable) > 0:
            file = f"{output_dir}/profitable_pairs_{timestamp}.csv"
            profitable.to_csv(file, index=False)
            print(f"✓ Exported {len(profitable)} profitable pairs to: {file}")
        
        # Export unprofitable pairs
        unprofitable = self.df[self.df['total_pnl_pct'] <= 0].sort_values('total_pnl_pct')
        if len(unprofitable) > 0:
            file = f"{output_dir}/unprofitable_pairs_{timestamp}.csv"
            unprofitable.to_csv(file, index=False)
            print(f"✓ Exported {len(unprofitable)} unprofitable pairs to: {file}")
        
        # Export high win rate pairs
        high_wr = self.df[self.df['win_rate'] >= 0.7].sort_values('total_pnl_pct', ascending=False)
        if len(high_wr) > 0:
            file = f"{output_dir}/high_winrate_pairs_{timestamp}.csv"
            high_wr.to_csv(file, index=False)
            print(f"✓ Exported {len(high_wr)} high win rate pairs (≥70%) to: {file}")
        
        # Export consistent performers (3+ trades, 60%+ WR, profitable)
        consistent = self.df[
            (self.df['total_trades'] >= 3) & 
            (self.df['win_rate'] >= 0.6) & 
            (self.df['total_pnl_pct'] > 0)
        ].sort_values('total_pnl_pct', ascending=False)
        if len(consistent) > 0:
            file = f"{output_dir}/consistent_performers_{timestamp}.csv"
            consistent.to_csv(file, index=False)
            print(f"✓ Exported {len(consistent)} consistent performers to: {file}")
        
        print("="*80)
    
    def run_full_analysis(self):
        """Run complete analysis suite"""
        self.print_summary_statistics()
        self.analyze_by_timeframe()
        self.print_top_performers()
        self.print_worst_performers()
        self.analyze_win_rate_distribution()
        self.analyze_trade_count_impact()
        self.find_perfect_pairs()
        self.find_zero_win_pairs()
        self.analyze_consistency()
        self.generate_charts()
        self.export_filtered_results()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze backtest results')
    parser.add_argument('summary_file', nargs='?', 
                       default='backtest_SUMMARY_20251107_054957.csv',
                       help='Path to backtest summary CSV file')
    parser.add_argument('--top', type=int, default=10, 
                       help='Number of top/worst performers to show (default: 10)')
    parser.add_argument('--no-charts', action='store_true',
                       help='Skip chart generation')
    parser.add_argument('--no-export', action='store_true',
                       help='Skip filtered results export')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.summary_file).exists():
        print(f"✗ File not found: {args.summary_file}")
        print(f"\nSearching for backtest summary files...")
        
        # Search for CSV files
        output_dir = Path('io/output')
        if output_dir.exists():
            csv_files = list(output_dir.glob('backtest_SUMMARY_*.csv'))
            if csv_files:
                print(f"\nFound {len(csv_files)} backtest summary files:")
                for i, file in enumerate(sorted(csv_files, reverse=True), 1):
                    print(f"  {i}. {file.name}")
                
                print(f"\nUsage: python {sys.argv[0]} <filename>")
            else:
                print("✗ No backtest summary files found in io/output/")
        else:
            print("✗ Output directory not found: io/output/")
        
        sys.exit(1)
    
    print("="*80)
    print("BACKTEST ANALYSIS TOOL")
    print("="*80)
    print(f"File: {args.summary_file}\n")
    
    # Run analysis
    analyzer = BacktestAnalyzer(args.summary_file)
    
    # Print statistics
    analyzer.print_summary_statistics()
    analyzer.analyze_by_timeframe()
    analyzer.print_top_performers(args.top)
    analyzer.print_worst_performers(args.top)
    analyzer.analyze_win_rate_distribution()
    analyzer.analyze_trade_count_impact()
    analyzer.find_perfect_pairs()
    analyzer.find_zero_win_pairs()
    analyzer.analyze_consistency()
    
    # Generate charts
    if not args.no_charts:
        analyzer.generate_charts()
    
    # Export filtered results
    if not args.no_export:
        analyzer.export_filtered_results()
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
