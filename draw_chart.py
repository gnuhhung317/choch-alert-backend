"""
Script để vẽ biểu đồ pivot và CHoCH cho một symbol cụ thể
Sử dụng: python draw_chart.py JOEUSDT.P 15m 50
"""
import asyncio
import sys
import os
import logging
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from data.binance_fetcher import BinanceFetcher
from detectors.choch_detector import ChochDetector
from visualization.chart_plotter import ChochChartPlotter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def draw_single_chart(symbol: str, timeframe: str, bars: int = 50):
    """
    Vẽ biểu đồ cho một symbol cụ thể với pivots và CHoCH marks
    
    Args:
        symbol: Symbol cần vẽ (VD: 'JOEUSDT.P' -> sẽ convert thành 'JOEUSDT')
        timeframe: Khung thời gian (VD: '15m')
        bars: Số bars cần vẽ (default: 50)
    """
    print(f"🎯 Vẽ biểu đồ cho {symbol} khung {timeframe} với {bars} bars cuối")
    
    # Convert symbol format (remove .P suffix for Binance API)
    binance_symbol = symbol.replace('.P', '')
    print(f"📊 Binance symbol: {binance_symbol}")
    
    # Initialize components
    fetcher = BinanceFetcher(
        api_key=config.BINANCE_API_KEY,
        secret=config.BINANCE_SECRET
    )
    
    detector = ChochDetector(
        left=config.PIVOT_LEFT,
        right=config.PIVOT_RIGHT,
        keep_pivots=config.KEEP_PIVOTS,
        allow_ph1=config.ALLOW_PH1,
        allow_ph2=config.ALLOW_PH2,
        allow_ph3=config.ALLOW_PH3,
        allow_ph4=config.ALLOW_PH4,
        allow_ph5=config.ALLOW_PH5,
        allow_pl1=config.ALLOW_PL1,
        allow_pl2=config.ALLOW_PL2,
        allow_pl3=config.ALLOW_PL3,
        allow_pl4=config.ALLOW_PL4,
        allow_pl5=config.ALLOW_PL5
    )
    
    plotter = ChochChartPlotter(output_dir="charts")
    
    try:
        # Initialize fetcher
        await fetcher.initialize()
        print("✅ Kết nối Binance thành công")
        
        # Fetch data
        print(f"📥 Đang fetch {bars} bars cho {binance_symbol} {timeframe}...")
        df = await fetcher.fetch_historical(
            symbol=binance_symbol,
            timeframe=timeframe,
            limit=bars
        )
        
        if len(df) == 0:
            print(f"❌ Không có dữ liệu cho {binance_symbol} {timeframe}")
            return
        
        print(f"✅ Đã fetch {len(df)} bars từ {df.index[0]} đến {df.index[-1]}")
        
        # Process pivots
        print(f"🔍 Đang phân tích pivots...")
        key = f"{binance_symbol}_{timeframe}"
        pivot_count = detector.rebuild_pivots(key, df)
        print(f"✅ Đã tìm {pivot_count} pivot points")
        
        # Check for CHoCH
        print(f"🎯 Đang kiểm tra CHoCH...")
        result = detector.process_new_bar(key, df)
        
        # Get state and pivots
        state = detector.states.get(key)
        pivots = []
        if state and state.pivot_count() > 0:
            print(f"📊 Đang chuẩn bị {state.pivot_count()} pivots để vẽ...")
            for i in range(state.pivot_count()):
                bar, price, is_high = state.get_pivot_from_end(i)
                pivots.append({
                    'bar': bar,
                    'price': price,
                    'is_high': is_high
                })
        
        # Prepare CHoCH info
        choch_info = None
        if result.get('choch_up') or result.get('choch_down'):
            choch_info = {
                'type': result.get('signal_type', 'CHoCH'),
                'price': result.get('price'),
                'timestamp': result.get('timestamp')
            }
            print(f"🎯 Phát hiện CHoCH: {choch_info['type']} @ {choch_info['price']:.6f}")
        else:
            print("ℹ️  Không phát hiện CHoCH trong dữ liệu")
        
        # Plot chart
        print(f"🎨 Đang vẽ biểu đồ...")
        chart_path = plotter.plot_choch_signal(
            symbol=symbol,  # Use original symbol with .P
            timeframe=timeframe,
            df=df,
            pivots=pivots,
            choch_info=choch_info,
            save=True
        )
        
        if chart_path:
            print(f"✅ Đã lưu biểu đồ: {chart_path}")
            
            # Generate Pine Script (only if we have pivots)
            try:
                if pivots:  # Only generate if we have pivots to show
                    # Ensure choch_info is not None for Pine Script generation
                    safe_choch_info = choch_info if choch_info else {
                        'type': 'No CHoCH',
                        'price': None,
                        'timestamp': None
                    }
                    script_path = plotter.save_tradingview_script(
                        symbol=symbol,
                        timeframe=timeframe,
                        pivots=pivots,
                        choch_info=safe_choch_info
                    )
                    print(f"📝 Đã lưu Pine Script: {script_path}")
                else:
                    print("ℹ️  Bỏ qua Pine Script (không có pivots)")
            except Exception as e:
                print(f"⚠️  Lỗi tạo Pine Script: {e}")
        else:
            print("❌ Không thể lưu biểu đồ")
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        logger.exception("Chi tiết lỗi:")
        
    finally:
        # Close fetcher
        try:
            await fetcher.close()
        except:
            pass


async def main():
    """Main function"""
    # Default parameters
    default_symbol = "JOEUSDT.P"
    default_timeframe = "15m"
    default_bars = 20
    
    # Parse command line arguments
    if len(sys.argv) >= 2:
        symbol = sys.argv[1]
    else:
        symbol = default_symbol
        
    if len(sys.argv) >= 3:
        timeframe = sys.argv[2]
    else:
        timeframe = default_timeframe
        
    if len(sys.argv) >= 4:
        try:
            bars = int(sys.argv[3])
        except ValueError:
            bars = default_bars
    else:
        bars = default_bars
    
    print("=" * 60)
    print("🎨 CHoCH CHART DRAWER")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")
    print(f"Bars: {bars}")
    print("=" * 60)
    
    await draw_single_chart(symbol, timeframe, bars)
    
    print("\n" + "=" * 60)
    print("✨ Hoàn thành!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())