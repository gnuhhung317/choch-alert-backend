"""
Chart Plotter - Visualize CHoCH signals with pivot points
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import Dict, List, Optional
import os
import logging

logger = logging.getLogger(__name__)


class ChochChartPlotter:
    """Plot price charts with CHoCH signals and pivot points"""
    
    def __init__(self, output_dir: str = "charts"):
        """
        Initialize chart plotter
        
        Args:
            output_dir: Directory to save chart images
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set style
        plt.style.use('dark_background')
    
    def plot_choch_signal(self, 
                          symbol: str,
                          timeframe: str,
                          df: pd.DataFrame,
                          pivots: List[Dict],
                          choch_info: Dict,
                          save: bool = True) -> Optional[str]:
        """
        Plot candlestick chart with pivots and CHoCH signal
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '5m', '1h')
            df: OHLCV DataFrame
            pivots: List of pivot points with format:
                    [{'bar': timestamp, 'price': float, 'is_high': bool}, ...]
            choch_info: CHoCH detection info with:
                       {'type': 'CHoCH Up/Down', 'price': float, 'timestamp': datetime}
            save: Whether to save the chart
        
        Returns:
            Path to saved chart file or None
        """
        try:
            # Create figure with custom size
            fig, ax = plt.subplots(figsize=(16, 9))
            
            # Plot candlesticks
            self._plot_candlesticks(ax, df)
            
            # Plot pivot points
            self._plot_pivots(ax, pivots)
            
            # Plot CHoCH signal
            self._plot_choch_signal(ax, choch_info, df)
            
            # Formatting
            ax.set_title(f"{symbol} {timeframe} - CHoCH Signal", fontsize=16, fontweight='bold')
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Price', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            if save:
                # Save chart
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{symbol}_{timeframe}_{timestamp}.png"
                filepath = os.path.join(self.output_dir, filename)
                plt.savefig(filepath, dpi=100, bbox_inches='tight')
                logger.info(f"[CHART] Saved to {filepath}")
                plt.close()
                return filepath
            else:
                plt.show()
                return None
        
        except Exception as e:
            logger.error(f"Error plotting chart: {e}", exc_info=True)
            plt.close()
            return None
    
    def _plot_candlesticks(self, ax, df: pd.DataFrame):
        """Plot candlestick chart"""
        # Use last 100 bars for clarity
        df_plot = df.tail(100).copy()
        
        # Convert index to matplotlib dates
        dates = mdates.date2num(df_plot.index.to_pydatetime())
        
        # Plot candles
        for i, (idx, row) in enumerate(df_plot.iterrows()):
            color = 'lime' if row['close'] >= row['open'] else 'red'
            
            # Candle body
            body_height = abs(row['close'] - row['open'])
            body_bottom = min(row['open'], row['close'])
            
            ax.add_patch(plt.Rectangle((dates[i] - 0.0003, body_bottom),
                                      0.0006, body_height,
                                      facecolor=color, edgecolor=color, alpha=0.8))
            
            # Wicks
            ax.plot([dates[i], dates[i]], [row['low'], row['high']],
                   color=color, linewidth=0.5, alpha=0.8)
        
        # Set limits
        y_min = df_plot['low'].min() * 0.999
        y_max = df_plot['high'].max() * 1.001
        ax.set_ylim(y_min, y_max)
        ax.set_xlim(dates[0] - 0.002, dates[-1] + 0.002)
    
    def _plot_pivots(self, ax, pivots: List[Dict]):
        """Plot pivot points and connect them (like Pine Script waves)"""
        if not pivots:
            return
        
        # Sort pivots by bar (oldest to newest)
        sorted_pivots = sorted(pivots, key=lambda p: mdates.date2num(p['bar']))
        
        # Plot all pivot points
        for p in sorted_pivots:
            date = mdates.date2num(p['bar'])
            price = p['price']
            
            if p['is_high']:
                color = 'cyan'
                marker = 'v'
                label = 'PH'
            else:
                color = 'yellow'
                marker = '^'
                label = 'PL'
            
            ax.scatter(date, price, 
                      color=color, s=100, marker=marker, 
                      zorder=5, edgecolors='white', linewidth=1)
        
        # Connect ALL pivots in sequence (like drawWaves in Pine Script)
        if len(sorted_pivots) > 1:
            dates_all = [mdates.date2num(p['bar']) for p in sorted_pivots]
            prices_all = [p['price'] for p in sorted_pivots]
            
            # Draw connecting lines between consecutive pivots
            ax.plot(dates_all, prices_all, 
                   color='blue', linewidth=2, alpha=0.6, 
                   zorder=4, label='Pivot Waves')
            
            # Add legend labels for first PH and PL
            has_high = any(p['is_high'] for p in sorted_pivots)
            has_low = any(not p['is_high'] for p in sorted_pivots)
            if has_high and not has_low:
                ax.scatter([], [], color='cyan', s=100, marker='v', label='Pivot High', zorder=5)
            elif has_low and not has_high:
                ax.scatter([], [], color='yellow', s=100, marker='^', label='Pivot Low', zorder=5)
            else:
                ax.scatter([], [], color='cyan', s=100, marker='v', label='Pivot High', zorder=5)
                ax.scatter([], [], color='yellow', s=100, marker='^', label='Pivot Low', zorder=5)
    
    def _plot_choch_signal(self, ax, choch_info: Dict, df: pd.DataFrame):
        """Plot CHoCH signal marker and annotation"""
        if not choch_info:
            return
        
        choch_type = choch_info.get('type', '')
        price = choch_info.get('price', 0)
        timestamp = choch_info.get('timestamp')
        
        if not timestamp:
            timestamp = df.index[-1]
        
        date = mdates.date2num(timestamp)
        
        # Determine color and marker
        if 'Up' in choch_type:
            color = 'lime'
            marker = '^'
            offset = -50  # Annotation below
        else:
            color = 'red'
            marker = 'v'
            offset = 50  # Annotation above
        
        # Plot CHoCH marker
        ax.scatter(date, price, 
                  color=color, s=300, marker='*', 
                  label=f'CHoCH {choch_type}', 
                  zorder=10, edgecolors='white', linewidth=2)
        
        # Add annotation
        ax.annotate(f'CHoCH\n${price:,.2f}',
                   xy=(date, price),
                   xytext=(0, offset),
                   textcoords='offset points',
                   fontsize=12,
                   fontweight='bold',
                   color=color,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.8),
                   arrowprops=dict(arrowstyle='->', color=color, lw=2))
    
    def generate_tradingview_script(self,
                                   symbol: str,
                                   timeframe: str,
                                   pivots: List[Dict],
                                   choch_info: Dict) -> str:
        """
        Generate Pine Script code for TradingView
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            pivots: List of pivot points
            choch_info: CHoCH detection info
        
        Returns:
            Pine Script code as string
        """
        # Convert pivots to arrays
        pivot_highs = [p for p in pivots if p['is_high']]
        pivot_lows = [p for p in pivots if not p['is_high']]
        
        # Format timestamps
        high_times = [int(p['bar'].timestamp() * 1000) for p in pivot_highs]
        high_prices = [p['price'] for p in pivot_highs]
        
        low_times = [int(p['bar'].timestamp() * 1000) for p in pivot_lows]
        low_prices = [p['price'] for p in pivot_lows]
        
        choch_time = int(choch_info.get('timestamp', datetime.now()).timestamp() * 1000)
        choch_price = choch_info.get('price', 0)
        choch_type = choch_info.get('type', '')
        
        script = f'''// CHoCH Signal for {symbol} {timeframe}
// Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

//@version=5
indicator("CHoCH Signal - {symbol}", overlay=true)

// Pivot Highs
var line[] highLines = array.new_line()
'''
        
        # Add pivot high lines
        for i in range(len(pivot_highs) - 1):
            script += f'''
line.new(
    x1={high_times[i]}, y1={high_prices[i]:.2f},
    x2={high_times[i+1]}, y2={high_prices[i+1]:.2f},
    color=color.new(color.aqua, 0),
    width=2,
    style=line.style_dashed
)
'''
        
        # Add pivot low lines
        script += '\n// Pivot Lows\n'
        for i in range(len(pivot_lows) - 1):
            script += f'''
line.new(
    x1={low_times[i]}, y1={low_prices[i]:.2f},
    x2={low_times[i+1]}, y2={low_prices[i+1]:.2f},
    color=color.new(color.yellow, 0),
    width=2,
    style=line.style_dashed
)
'''
        
        # Add CHoCH marker
        choch_color = 'color.lime' if 'Up' in choch_type else 'color.red'
        script += f'''
// CHoCH Signal
label.new(
    x={choch_time}, y={choch_price:.2f},
    text="CHoCH\\n${choch_price:,.2f}",
    color={choch_color},
    textcolor=color.white,
    size=size.large,
    style=label.style_label_{'up' if 'Up' in choch_type else 'down'}
)
'''
        
        return script
    
    def save_tradingview_script(self, 
                                symbol: str,
                                timeframe: str,
                                pivots: List[Dict],
                                choch_info: Dict) -> str:
        """
        Generate and save Pine Script to file
        
        Returns:
            Path to saved script file
        """
        script = self.generate_tradingview_script(symbol, timeframe, pivots, choch_info)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{symbol}_{timeframe}_{timestamp}.pine"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(script)
        
        logger.info(f"[SCRIPT] Saved Pine Script to {filepath}")
        return filepath


# Example usage
if __name__ == "__main__":
    import numpy as np
    
    # Create sample data
    dates = pd.date_range(start='2025-10-18 08:00', periods=100, freq='5min')
    prices = 67000 + np.cumsum(np.random.randn(100) * 10)
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(100) * 5,
        'high': prices + np.abs(np.random.randn(100) * 10),
        'low': prices - np.abs(np.random.randn(100) * 10),
        'close': prices + np.random.randn(100) * 5,
        'volume': np.random.randint(100, 1000, 100)
    }, index=dates)
    
    # Sample pivots
    pivots = [
        {'bar': dates[20], 'price': df.iloc[20]['high'], 'is_high': True},
        {'bar': dates[30], 'price': df.iloc[30]['low'], 'is_high': False},
        {'bar': dates[50], 'price': df.iloc[50]['high'], 'is_high': True},
        {'bar': dates[70], 'price': df.iloc[70]['low'], 'is_high': False},
    ]
    
    # Sample CHoCH
    choch_info = {
        'type': 'CHoCH Up',
        'price': df.iloc[-1]['close'],
        'timestamp': dates[-1]
    }
    
    # Plot
    plotter = ChochChartPlotter()
    plotter.plot_choch_signal('BTCUSDT', '5m', df, pivots, choch_info)
    plotter.save_tradingview_script('BTCUSDT', '5m', pivots, choch_info)
