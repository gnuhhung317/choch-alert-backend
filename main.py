"""
Main application - Coordinates multi-timeframe watchers, detection, and alert broadcasting
"""
import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict

import pandas as pd

# Import configuration
import config

# Import modules
from data.binance_fetcher import BinanceFetcher
from detectors.choch_detector import ChochDetector
from alert.telegram_sender import TelegramSender, create_alert_data
from web.app import broadcast_alert, start_flask_background
from visualization.chart_plotter import ChochChartPlotter
from utils.tradingview_helper import add_tradingview_link_to_alert
from utils.timeframe_scheduler import TimeframeScheduler

# Setup logging with UTF-8 encoding to handle emoji characters
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('choch_alert.log', encoding='utf-8')
    ]
)

# Configure stdout handler to use UTF-8 encoding on Windows
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
        try:
            # Try to reconfigure stdout to use UTF-8
            if sys.platform == 'win32':
                import io
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                handler.stream = sys.stdout
        except Exception:
            pass

logger = logging.getLogger(__name__)


class ChochAlertSystem:
    """Main CHoCH alert system coordinator"""
    
    def __init__(self):
        """Initialize the alert system"""
        logger.info("[*] Initializing CHoCH Alert System...")
        
        # Validate configuration
        try:
            config.validate_config()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize components
        self.fetcher = BinanceFetcher(
            api_key=config.BINANCE_API_KEY,
            secret=config.BINANCE_SECRET
        )
        
        self.detector = ChochDetector(
            left=config.PIVOT_LEFT,
            right=config.PIVOT_RIGHT,
            keep_pivots=config.KEEP_PIVOTS,
            use_variant_filter=config.USE_VARIANT_FILTER,
            allow_ph1=config.ALLOW_PH1,
            allow_ph2=config.ALLOW_PH2,
            allow_ph3=config.ALLOW_PH3,
            allow_pl1=config.ALLOW_PL1,
            allow_pl2=config.ALLOW_PL2,
            allow_pl3=config.ALLOW_PL3
        )
        
        self.telegram = TelegramSender(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_CHAT_ID
        )
        
        # Initialize chart plotter
        self.plotter = ChochChartPlotter(output_dir="charts")
        
        # State tracking
        self.running = False
        self.tasks = []
        
        # Initialize timeframe scheduler
        self.scheduler = TimeframeScheduler(config.TIMEFRAMES)
        
        logger.info("[OK] System initialized")

    async def on_new_data(self, symbol: str, timeframe: str, df: pd.DataFrame, is_new_bar: bool):
        """
        Callback when new data is received for a timeframe
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe identifier
            df: 50 bars dataframe (pivot đã được rebuild ở monitor_loop)
            is_new_bar: Always True in realtime mode
        
        Returns:
            True if CHoCH signal detected, False otherwise
        """
        key = f"{symbol}_{timeframe}"
        
        try:
            # ⬇️ DETECT CHoCH TRÊN BAR CUỐI - Pivot đã rebuild ở monitor_loop
            # Chỉ check CHoCH signal trên bar cuối
            state = self.detector.states.get(key)
            
            if state is None:
                logger.warning(f"[{symbol}][{timeframe}] No state found")
                return False
            
            # ⬇️ DETECT TRÊN BAR CUỐI - dùng state từ rebuild_pivots
            result = self.detector.process_new_bar(key, df)
            
            logger.debug(f"[{symbol}][{timeframe}] Detection: choch_up={result.get('choch_up')}, choch_down={result.get('choch_down')}")
            
            if result.get('choch_up') or result.get('choch_down'):
                logger.info(f"[SIGNAL] 🎯 CHoCH detected on {symbol} {timeframe}: {result.get('signal_type')}")
                logger.info(f"[{symbol}][{timeframe}] Bar: {df.index[-1]} | Close: {df['close'].iloc[-1]:.8f}")
                
                # Get pivot data for visualization
                pivots = []
                for i in range(state.pivot_count()):
                    bar, price, is_high = state.get_pivot_from_end(i)
                    pivots.append({
                        'bar': bar,
                        'price': price,
                        'is_high': is_high
                    })
                
                # CHoCH info
                choch_info = {
                    'type': result.get('signal_type', 'CHoCH'),
                    'price': result.get('price', df['close'].iloc[-1]),
                    'timestamp': result.get('timestamp', df.index[-1])
                }
                
                # Generate chart if enabled
                if config.ENABLE_CHART:
                    try:
                        chart_path = self.plotter.plot_choch_signal(
                            symbol=symbol,
                            timeframe=timeframe,
                            df=df,
                            pivots=pivots,
                            choch_info=choch_info,
                            save=True
                        )
                        
                        script_path = self.plotter.save_tradingview_script(
                            symbol=symbol,
                            timeframe=timeframe,
                            pivots=pivots,
                            choch_info=choch_info
                        )
                        
                        logger.info(f"[CHART] 📊 Chart: {chart_path}")
                        logger.info(f"[SCRIPT] 📝 Pine: {script_path}")
                    
                    except Exception as e:
                        logger.error(f"Error generating visualization: {e}")
                
                # Create alert data
                alert_data = create_alert_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type=result.get('signal_type', 'CHoCH'),
                    direction=result.get('direction', 'Long'),
                    price=result.get('price', df['close'].iloc[-1]),
                    timestamp=result.get('timestamp', df.index[-1])
                )
                
                # Add TradingView link to alert
                alert_data = add_tradingview_link_to_alert(alert_data, is_futures=True, region='in')
                
                logger.info(f"[TELEGRAM] 📤 Sending alert for {symbol} {timeframe}")
                
                # ⬇️ GỬI TELEGRAM ALERT
                self.telegram.send_alert(alert_data)
                logger.info(f"[TELEGRAM] ✓ Alert sent!")
                
                # Broadcast to web clients
                broadcast_alert(alert_data)
                
                return True  # Signal detected
            else:
                logger.debug(f"[{symbol}][{timeframe}] No CHoCH signal")
            
            return False  # No signal
        
        except Exception as e:
            logger.error(f"Error processing data for {symbol} {timeframe}: {e}", exc_info=True)
            return False
    
    async def start(self):
        """Start the alert system"""
        self.running = True
        
        logger.info("=" * 80)
        logger.info("CHoCH ALERT SYSTEM")
        logger.info("=" * 80)
        
        # Check which mode to run
        if config.ENABLE_CHART and config.CHART_MODE == 'history':
            # History mode: Load history, plot charts, exit
            logger.info("MODE: HISTORY - Vẽ chart toàn bộ lịch sử")
            await self.mode_history()
        else:
            # Realtime mode: Run continuously and send Telegram alerts
            logger.info("MODE: REALTIME - Chạy liên tục, gửi alert Telegram")
            await self.mode_realtime()
    
    async def mode_history(self):
        """
        History mode: Load all historical data and plot charts
        Chạy một lần để vẽ chart cho tất cả symbols
        """
        logger.info("[HISTORY] Starting history mode...")
        
        # Initialize fetcher
        await self.fetcher.initialize()
        
        # Get symbols to monitor
        symbols_to_monitor = config.get_symbols_list()
        
        if symbols_to_monitor == 'ALL':
            logger.info(f"Fetching all futures from Binance with {config.QUOTE_CURRENCY} pairs...")
            symbols_list = await self.fetcher.get_all_usdt_pairs(
                min_volume_24h=config.MIN_VOLUME_24H,
                quote=config.QUOTE_CURRENCY
            )
            logger.info(f"Found {len(symbols_list)} futures to plot")
        else:
            symbols_list = [s.replace('/', '') for s in symbols_to_monitor]
            logger.info(f"Plotting {len(symbols_list)} symbols: {', '.join(symbols_list)}")
        
        logger.info(f"Timeframes: {', '.join(config.TIMEFRAMES)}")
        logger.info("=" * 80)
        
        try:
            # Process each symbol/timeframe and plot charts
            for symbol in symbols_list:
                if not self.running:
                    break
                
                for timeframe in config.TIMEFRAMES:
                    try:
                        logger.info(f"\n[{symbol}][{timeframe}] Fetching historical data...")
                        df = await self.fetcher.fetch_historical(
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=config.HISTORICAL_LIMIT
                        )
                        
                        if len(df) == 0:
                            logger.warning(f"[{symbol}][{timeframe}] No data received")
                            continue
                        
                        # Process all historical data to build pivots
                        logger.info(f"[{symbol}][{timeframe}] Processing {len(df)} bars...")
                        key = f"{symbol}_{timeframe}"
                        result = self.detector.process_new_bar(key, df)
                        
                        # Get pivot data
                        state = self.detector.states.get(key)
                        pivots = []
                        if state:
                            for i in range(state.pivot_count()):
                                bar, price, is_high = state.get_pivot_from_end(i)
                                pivots.append({
                                    'bar': bar,
                                    'price': price,
                                    'is_high': is_high
                                })
                        
                        logger.info(f"[{symbol}][{timeframe}] Built {len(pivots)} pivots")
                        
                        # Prepare CHoCH info
                        choch_info = None
                        if result['choch_up'] or result['choch_down']:
                            logger.info(f"[{symbol}][{timeframe}] CHoCH found: {result['signal_type']}")
                            choch_info = {
                                'type': result['signal_type'],
                                'price': result['price'],
                                'timestamp': result['timestamp']
                            }
                        
                        # Plot chart
                        try:
                            chart_path = self.plotter.plot_choch_signal(
                                symbol=symbol,
                                timeframe=timeframe,
                                df=df,
                                pivots=pivots,
                                choch_info=choch_info,
                                save=True
                            )
                            logger.info(f"[CHART] 📊 Saved: {chart_path}")
                            
                            # Save Pine Script if CHoCH found
                            if choch_info:
                                script_path = self.plotter.save_tradingview_script(
                                    symbol=symbol,
                                    timeframe=timeframe,
                                    pivots=pivots,
                                    choch_info=choch_info
                                )
                                logger.info(f"[SCRIPT] 📝 Saved: {script_path}")
                        
                        except Exception as e:
                            logger.error(f"Error plotting chart: {e}")
                        
                        # Small delay
                        await asyncio.sleep(0.5)
                    
                    except Exception as e:
                        logger.error(f"Error processing {symbol} {timeframe}: {e}")
                        await asyncio.sleep(1)
            
            logger.info("\n[HISTORY] ✓ Done! All charts plotted.")
        
        except KeyboardInterrupt:
            logger.info("\n[STOP] Stopped")
        except Exception as e:
            logger.error(f"Error in history mode: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def mode_realtime(self):
        """
        Realtime mode: Continuously monitor and send Telegram alerts
        Quét theo interval của từng timeframe
        """
        logger.info("[REALTIME] Starting realtime mode...")
        
        # Test Telegram connection
        logger.info("Testing Telegram connection...")
        if not self.telegram.test_connection():
            logger.warning("[WARNING] Telegram connection failed, but continuing anyway...")
        
        # Start Flask web server in background
        logger.info("Starting web dashboard...")
        start_flask_background(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG
        )
        
        # Give Flask time to start
        await asyncio.sleep(2)
        logger.info(f"[WEB] Web dashboard available at http://{config.FLASK_HOST}:{config.FLASK_PORT}")
        
        # Initialize fetcher
        await self.fetcher.initialize()
        
        # Get symbols to monitor
        symbols_to_monitor = config.get_symbols_list()
        
        if symbols_to_monitor == 'ALL':
            logger.info(f"Fetching all futures from Binance with {config.QUOTE_CURRENCY} pairs...")
            symbols_list = await self.fetcher.get_all_usdt_pairs(
                min_volume_24h=config.MIN_VOLUME_24H,
                quote=config.QUOTE_CURRENCY
            )
            logger.info(f"Found {len(symbols_list)} futures to monitor")
        else:
            symbols_list = [s.replace('/', '') for s in symbols_to_monitor]
            logger.info(f"Monitoring {len(symbols_list)} specified futures: {', '.join(symbols_list)}")
        
        logger.info(f"Timeframes: {', '.join(config.TIMEFRAMES)}")
        logger.info(f"Pivot Settings: Left={config.PIVOT_LEFT}, Right={config.PIVOT_RIGHT}")
        logger.info(f"Historical Bars: {config.HISTORICAL_LIMIT}")
        logger.info(f"Variant Filter: {config.USE_VARIANT_FILTER}")
        logger.info(f"Total symbols: {len(symbols_list)}")
        logger.info("=" * 80)
        
        try:
            # Start sequential monitoring loop
            logger.info("[OK] Starting sequential monitoring loop...")
            logger.info("Press Ctrl+C to stop")
            
            await self.monitor_loop(symbols_list)
        
        except KeyboardInterrupt:
            logger.info("\n[STOP] Shutdown signal received...")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def monitor_loop(self, symbols: list):
        """
        Sequential monitoring loop with per-timeframe scheduling.
        Each timeframe is scanned only when its interval has passed.
        """
        loop_count = 0
        
        while self.running:
            loop_count += 1
            loop_start = asyncio.get_event_loop().time()
            
            # Get timeframes that are ready to scan
            scannable_timeframes = self.scheduler.get_scannable_timeframes()
            
            if not scannable_timeframes:
                # No timeframe ready yet, wait a bit
                await asyncio.sleep(1)
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Loop #{loop_count} - Scanning: {', '.join(scannable_timeframes)}")
            logger.info(f"Processing {len(symbols)} symbols × {len(scannable_timeframes)} timeframes")
            logger.info(f"{'='*60}")
            
            processed_count = 0
            signal_count = 0
            
            # Process each symbol sequentially
            for symbol in symbols:
                if not self.running:
                    break
                
                # Process only scannable timeframes for this symbol
                for timeframe in scannable_timeframes:
                    try:
                        # ⬇️ FETCH 50 BARS
                        logger.info(f"[{symbol}][{timeframe}] Fetching 50 bars...")
                        df = await self.fetcher.fetch_historical(
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=50  # ⬅️ CHỈ 50 BARS
                        )
                        
                        if len(df) == 0:
                            logger.warning(f"[{symbol}][{timeframe}] No data received")
                            continue
                        
                        key = f"{symbol}_{timeframe}"
                        
                        # ⬇️ REBUILD PIVOT TỪ 50 BARS
                        logger.info(f"[{symbol}][{timeframe}] Rebuilding pivots from {len(df)} bars...")
                        pivot_count = self.detector.rebuild_pivots(timeframe, df)
                        logger.info(f"[{symbol}][{timeframe}] ✓ Built {pivot_count} pivots")
                        
                        # ⬇️ DETECT CHoCH TRÊN BAR CUỐI (dùng state từ rebuild_pivots)
                        result = await self.on_new_data(symbol, timeframe, df, is_new_bar=True)
                        
                        if result:  # Signal detected
                            signal_count += 1
                        
                        processed_count += 1
                        
                        # ⬇️ BỎ DỮ LIỆU - KHÔNG LƯU LẠI
                        # Lần sau fetch dữ liệu mới xử lý lại
                        
                        # Small delay to respect rate limits
                        await asyncio.sleep(0.1)
                    
                    except Exception as e:
                        logger.error(f"Error processing {symbol} {timeframe}: {e}")
                        await asyncio.sleep(1)
                
                # After processing all scannable timeframes for this symbol, sleep a tiny bit
                await asyncio.sleep(0.1)
            
            # Mark timeframes as scanned
            for timeframe in scannable_timeframes:
                self.scheduler.mark_scanned(timeframe)
            
            # Calculate loop duration
            loop_duration = asyncio.get_event_loop().time() - loop_start
            
            # Get minimum wait time among all timeframes
            min_wait_time = min([self.scheduler.get_wait_time(tf) for tf in config.TIMEFRAMES])
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Loop #{loop_count} Summary:")
            logger.info(f"  Processed: {processed_count}/{len(symbols) * len(scannable_timeframes)}")
            logger.info(f"  Signals detected: {signal_count}")
            logger.info(f"  Duration: {loop_duration:.1f}s")
            logger.info(f"  Next scan in: {min_wait_time:.0f}s")
            logger.info(f"\n{self.scheduler.get_status_report()}")
            logger.info(f"{'='*60}\n")
            
            # Wait for minimum time until next scan
            if min_wait_time > 0:
                await asyncio.sleep(min(min_wait_time, 60))  # Check every 60s at most
            else:
                await asyncio.sleep(1)  # Check again quickly if something is ready
    
    async def stop(self):
        """Stop the alert system"""
        logger.info("Stopping alert system...")
        
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Close fetcher
        try:
            await self.fetcher.close()
        except Exception as e:
            logger.warning(f"Error closing fetcher: {e}")
        
        logger.info("[OK] Alert system stopped")


async def main():
    """Main entry point"""
    system = ChochAlertSystem()
    await system.start()


if __name__ == '__main__':
    try:
        # Check Python version
        if sys.version_info < (3, 10):
            logger.warning("[WARNING] Python 3.10+ recommended. Current version: {}.{}".format(
                sys.version_info.major, sys.version_info.minor
            ))
        
        # Run the system
        asyncio.run(main())
    
    except KeyboardInterrupt:
        logger.info("\n[EXIT] Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
