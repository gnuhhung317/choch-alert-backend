"""
Main application - Coordinates multi-timeframe watchers, detection, and alert broadcasting
"""
import asyncio
import logging
import sys
import random
from datetime import datetime
from typing import Dict

import pandas as pd

# Import configuration
import config

# Import modules
from data.binance_fetcher import BinanceFetcher
from data.timeframe_adapter import TimeframeAdapter
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
        base_fetcher = BinanceFetcher(
            api_key=config.BINANCE_API_KEY,
            secret=config.BINANCE_SECRET
        )
        
        # Wrap with TimeframeAdapter to support aggregated timeframes (10m, 20m, 40m, 50m)
        self.fetcher = TimeframeAdapter(base_fetcher)
        logger.info("[OK] Using TimeframeAdapter for automatic candle aggregation")
        
        self.detector = ChochDetector(
            left=config.PIVOT_LEFT,
            right=config.PIVOT_RIGHT,
            keep_pivots=config.KEEP_PIVOTS,
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

    async def on_new_data(self, symbol: str, timeframe: str, df: pd.DataFrame, has_enough_bars: bool):
        """
        Process CHoCH detection với 3-CANDLE CONFIRMATION (CLOSED CANDLES ONLY)
        
        Logic 3 nến:
        - Pre-CHoCH: df.index[-3] (nến thứ 3 từ cuối)  
        - CHoCH: df.index[-2] (nến thứ 2 từ cuối)
        - Confirmation: df.index[-1] (nến cuối cùng)
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe identifier  
            df: DataFrame với CLOSED bars only (≥ 3 bars cho confirmation)
            has_enough_bars: True nếu có đủ ≥ 3 bars cho 3-candle logic
        
        Returns:
            True if CHoCH signal detected and confirmed, False otherwise
        """
        key = f"{symbol}_{timeframe}"
        
        try:
            # ⬇️ VALIDATE: Cần đủ bars cho 3-candle confirmation
            if not has_enough_bars or len(df) < 3:
                logger.debug(f"[{symbol}][{timeframe}] Insufficient bars for 3-candle confirmation ({len(df)} bars)")
                return False
                
            # ⬇️ GET STATE - Pivot đã rebuild ở monitor_loop
            state = self.detector.states.get(key)
            if state is None:
                logger.warning(f"[{symbol}][{timeframe}] No detector state found")
                return False
            
            # ⬇️ CHoCH DETECTION với 3-CANDLE CONFIRMATION
            # process_new_bar sẽ check:
            # - Pre-CHoCH: df.index[-3] 
            # - CHoCH: df.index[-2]
            # - Confirmation: df.index[-1]
            result = self.detector.process_new_bar(key, df)
            
            logger.debug(f"[{symbol}][{timeframe}] 3-Candle Detection: choch_up={result.get('choch_up')}, choch_down={result.get('choch_down')}")
            
            if result.get('choch_up') or result.get('choch_down'):
                # ✅ CHoCH CONFIRMED với 3 NẾN ĐÃ ĐÓNG
                confirmation_idx = df.index[-1]  # Confirmation candle (cuối cùng)
                choch_idx = df.index[-2]  # CHoCH candle (thứ 2 từ cuối)
                pre_choch_idx = df.index[-3]  # Pre-CHoCH candle (thứ 3 từ cuối)
                
                logger.info(f"[SIGNAL] 🎯 CHoCH CONFIRMED on {symbol} {timeframe}: {result.get('signal_type')} (3-CANDLE LOGIC)")
                logger.info(f"[{symbol}][{timeframe}] Pre-CHoCH: {pre_choch_idx} | CHoCH: {choch_idx} | Confirm: {confirmation_idx}")
                logger.info(f"[{symbol}][{timeframe}] CHoCH Price: {result.get('price'):.8f} | CHoCH Time: {result.get('timestamp')}")
                
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
                    'price': result.get('price', df['close'].iloc[-2]),  # CHoCH price (nến thứ 2 từ cuối)
                    'timestamp': result.get('timestamp', choch_idx)  # CHoCH timestamp
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
                
                # Create alert data với CHoCH timing (không phải thời gian hiện tại)
                alert_data = create_alert_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type=result.get('signal_type', 'CHoCH'),
                    direction=result.get('direction', 'Long'),
                    price=result.get('price', df['close'].iloc[-2]),  # CHoCH price
                    timestamp=result.get('timestamp', choch_idx),  # CHoCH candle time (not current time)
                    pattern_group=result.get('pattern_group')  # G1, G2, or G3
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
                quote=config.QUOTE_CURRENCY,
                max_pairs=config.MAX_PAIRS
            )
            mode_text = "UNLIMITED" if config.MAX_PAIRS == 0 else f"LIMITED to {config.MAX_PAIRS}"
            logger.info(f"Found {len(symbols_list)} futures to plot ({mode_text})")
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
                        
                        # ⬇️ REBUILD PIVOTS FIRST
                        pivot_count = self.detector.rebuild_pivots(key, df)
                        logger.info(f"[{symbol}][{timeframe}] Built {pivot_count} pivots")
                        
                        # ⬇️ THEN CHECK CHoCH ON LAST BAR
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
        
        logger.info(f"Timeframes: {', '.join(config.TIMEFRAMES)}")
        logger.info(f"Pivot Settings: Left={config.PIVOT_LEFT}, Right={config.PIVOT_RIGHT}")
        logger.info(f"Historical Bars: {config.HISTORICAL_LIMIT}")
        logger.info(f"Variant Filter: {config.USE_VARIANT_FILTER}")
        logger.info("=" * 80)
        
        try:
            # Start sequential monitoring loop
            logger.info("[OK] Starting sequential monitoring loop with dynamic symbol fetching...")
            unlimited_text = "UNLIMITED symbols" if config.MAX_PAIRS == 0 else f"up to {config.MAX_PAIRS} symbols"
            logger.info(f"Each scan will fetch {unlimited_text} based on config")
            logger.info("Press Ctrl+C to stop")
            
            await self.monitor_loop()
        
        except KeyboardInterrupt:
            logger.info("\n[STOP] Shutdown signal received...")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def monitor_loop(self):
        """
        Sequential monitoring loop with per-timeframe scheduling and dynamic symbol fetching.
        Each scan will fetch symbol list according to UNLIMITED_PAIRS and MAX_PAIRS config.
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
            
            # ⬇️ FETCH SYMBOLS DYNAMICALLY FOR EACH SCAN
            try:
                symbols_to_monitor = config.get_symbols_list()
                
                if symbols_to_monitor == 'ALL':
                    logger.info(f"[Loop #{loop_count}] Fetching fresh symbol list from Binance...")
                    selected_symbols = await self.fetcher.get_all_usdt_pairs(
                        min_volume_24h=config.MIN_VOLUME_24H,
                        quote=config.QUOTE_CURRENCY,
                        max_pairs=config.MAX_PAIRS
                    )
                    mode_text = "UNLIMITED" if config.MAX_PAIRS == 0 else f"max_pairs={config.MAX_PAIRS}"
                    logger.info(f"[Loop #{loop_count}] Using {len(selected_symbols)} symbols ({mode_text})")
                else:
                    # Use specified symbols (no randomization)
                    selected_symbols = [s.replace('/', '') for s in symbols_to_monitor]
                    logger.info(f"[Loop #{loop_count}] Using {len(selected_symbols)} specified symbols")
                
            except Exception as e:
                logger.error(f"[Loop #{loop_count}] Error fetching symbols: {e}")
                await asyncio.sleep(10)  # Wait before retry
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Loop #{loop_count} - Scanning: {', '.join(scannable_timeframes)}")
            logger.info(f"Processing {len(selected_symbols)} symbols × {len(scannable_timeframes)} timeframes")
            logger.info(f"{'='*60}")
            
            processed_count = 0
            signal_count = 0
            
            # Process each selected symbol sequentially
            for symbol in selected_symbols:
                if not self.running:
                    break
                
                # Process only scannable timeframes for this symbol
                for timeframe in scannable_timeframes:
                    try:
                        # ⬇️ FETCH CLOSED BARS ONLY (open candle excluded)
                        logger.info(f"[{symbol}][{timeframe}] Fetching 50 CLOSED bars...")
                        df = await self.fetcher.fetch_historical(
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=50  # ⬅️ 50 CLOSED BARS (open candle excluded)
                        )
                        
                        if len(df) == 0:
                            logger.warning(f"[{symbol}][{timeframe}] No data received")
                            continue
                        
                        key = f"{symbol}_{timeframe}"
                        
                        # ⬇️ ALWAYS REBUILD PIVOTS from CLOSED bars (ensures accuracy)
                        # Rebuilding từ 50 bars đảm bảo tính chính xác cao hơn incremental update
                        logger.info(f"[{symbol}][{timeframe}] Rebuilding pivots from {len(df)} CLOSED bars...")
                        pivot_count = self.detector.rebuild_pivots(key, df)
                        logger.info(f"[{symbol}][{timeframe}] ✓ Built {pivot_count} pivots from CLOSED candles")
                        
                        # ⬇️ CHECK CHoCH với 3-CANDLE CONFIRMATION LOGIC
                        # Cần ít nhất 3 nến: pre-CHoCH, CHoCH, confirmation
                        if len(df) >= 3:
                            result = await self.on_new_data(symbol, timeframe, df, has_enough_bars=True)
                        else:
                            logger.debug(f"[{symbol}][{timeframe}] Not enough bars for 3-candle confirmation ({len(df)} < 3)")
                            result = False
                        
                        if result:  # Signal detected
                            signal_count += 1
                        
                        processed_count += 1
                        
                        # ⬇️ 50 CLOSED BARS processed với 3-CANDLE CONFIRMATION
                        # Lần sau fetch 50 bars mới và rebuild pivots từ đầu
                        
                        # Small delay to respect rate limits
                        await asyncio.sleep(0.1)
                    
                    except Exception as e:
                        logger.error(f"Error processing {symbol} {timeframe}: {e}")
                        await asyncio.sleep(1)
                
                # After processing all scannable timeframes for this symbol, sleep a tiny bit
                await asyncio.sleep(0.1)
            
            # Mark timeframes as scanned at their previous candle close
            for timeframe in scannable_timeframes:
                try:
                    prev_close = self.scheduler.get_prev_candle_close_time(timeframe)
                    # Some schedulers may accept only timeframe; fall back if signature differs
                    self.scheduler.last_scanned_close[timeframe] = prev_close
                except Exception:
                    # Fallback to simple mark
                    self.scheduler.mark_scanned(timeframe)
            
            # Calculate loop duration
            loop_duration = asyncio.get_event_loop().time() - loop_start
            
            # Compute next scan as nearest next candle close among all configured timeframes
            from datetime import datetime, timedelta
            next_close_times = []
            for tf in config.TIMEFRAMES:
                try:
                    next_close_times.append(self.scheduler.get_next_candle_close_time(tf))
                except Exception:
                    # Fallback: use now + wait
                    wait = self.scheduler.get_wait_time(tf)
                    next_close_times.append(datetime.now() + timedelta(seconds=wait))
            
            if next_close_times:
                next_scan_time = min(next_close_times)
            else:
                next_scan_time = datetime.now() + timedelta(seconds=60)
            
            # Seconds remaining until next scan
            actual_wait = max(0, (next_scan_time - datetime.now()).total_seconds())
            next_scan_str = next_scan_time.strftime('%H:%M:%S')
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Loop #{loop_count} Summary:")
            logger.info(f"  Processed: {processed_count}/{len(selected_symbols) * len(scannable_timeframes)}")
            logger.info(f"  Signals detected: {signal_count}")
            logger.info(f"  Duration: {loop_duration:.1f}s")
            logger.info(f"  Next scan at: {next_scan_str} ({actual_wait:.0f}s)")
            logger.info(f"\n{self.scheduler.get_status_report()}")
            logger.info(f"{'='*60}\n")
            
            # Wait in small chunks so we don't miss the boundary due to long sleep
            # Sleep up to 5 seconds at a time
            remaining = actual_wait
            while remaining > 0 and self.running:
                chunk = 5 if remaining > 5 else remaining
                await asyncio.sleep(chunk)
                remaining -= chunk
    
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
