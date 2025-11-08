"""
Trading Bot Demo - Test complete trading system with demo exchange

This script demonstrates:
1. Signal Bus (event-driven)
2. Trading Bot (signal consumer)
3. Position Manager (order management)
4. Exchange Adapter (demo mode)

Run: python trading_bot_demo.py
"""
import asyncio
import logging
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

import config
from detectors.choch_detector import ChochDetector
from data.timeframe_adapter import TimeframeAdapter
from data.binance_fetcher import BinanceFetcher
from trading.exchange_adapter import BinanceFuturesAdapter
from trading.position_manager import PositionManager
from trading.trading_bot import TradingBot
from trading.signal_bus import get_signal_bus
from trading.signal_converter import create_signal_from_choch

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_bot_demo.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


async def demo_signal_handler(signal):
    """Demo signal handler for testing"""
    logger.info(f"[DEMO HANDLER] Received signal: {signal.symbol} {signal.timeframe} {signal.direction}")


async def main():
    """Main demo function"""
    logger.info("\n" + "="*80)
    logger.info("TRADING BOT DEMO - Testing Complete System")
    logger.info("="*80 + "\n")
    
    # Configuration
    SYMBOLS = ["BTCUSDT", "ETHUSDT"]  # Test with 2 symbols only
    TIMEFRAMES = ["15m", "1h"]
    DEMO_MODE = True  # Use demo trading (testnet)
    ENABLE_TRADING = True  # False = simulation only
    SCAN_LIMIT = 100  # Bars per scan
    
    try:
        # 1. Initialize exchange adapter (DEMO MODE)
        logger.info("="*80)
        logger.info("STEP 1: Initialize Exchange Adapter")
        logger.info("="*80)
        
        exchange = BinanceFuturesAdapter(
            api_key=config.BINANCE_API_KEY or "demo_key",
            secret=config.BINANCE_SECRET or "demo_secret",
            demo_mode=True
        )
        
        # Don't initialize if no real API keys and trading disabled
        if not ENABLE_TRADING:
            logger.info("Trading disabled - Skipping exchange initialization")
            logger.info("Simulation mode: Orders will be logged only\n")
        else:
            exchange.initialize()
        
        # 2. Initialize position manager
        logger.info("="*80)
        logger.info("STEP 2: Initialize Position Manager")
        logger.info("="*80)
        
        position_manager = PositionManager(
            exchange=exchange,
            enable_trading=ENABLE_TRADING
        )
        logger.info("")
        
        # 3. Initialize trading bot
        logger.info("="*80)
        logger.info("STEP 3: Initialize Trading Bot")
        logger.info("="*80)
        
        trading_bot = TradingBot(
            position_manager=position_manager,
            enable_trading=ENABLE_TRADING
        )
        
        # 4. Get signal bus and subscribe
        logger.info("="*80)
        logger.info("STEP 4: Setup Signal Bus")
        logger.info("="*80)
        
        signal_bus = get_signal_bus()
        
        # Subscribe trading bot
        trading_bot.start()
        
        # Subscribe demo handler (for testing)
        signal_bus.subscribe(demo_signal_handler)
        
        logger.info(f"✓ Signal bus ready with {signal_bus.get_subscriber_count()} subscribers")
        logger.info("")
        
        # 5. Initialize data fetcher and detector
        logger.info("="*80)
        logger.info("STEP 5: Initialize Scanner")
        logger.info("="*80)
        
        base_fetcher = BinanceFetcher(
            api_key=config.BINANCE_API_KEY,
            secret=config.BINANCE_SECRET,
            testnet=DEMO_MODE
        )
        fetcher = TimeframeAdapter(base_fetcher)
        await fetcher.initialize()
        
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
        
        logger.info("✓ Scanner ready")
        logger.info("")
        
        # 6. Start monitoring loop in background
        logger.info("="*80)
        logger.info("STEP 6: Start Position Monitoring")
        logger.info("="*80)
        
        monitoring_task = asyncio.create_task(
            trading_bot.run_monitoring_loop(update_interval=10.0)
        )
        logger.info("✓ Monitoring loop started (10s interval)\n")
        
        # 7. Main scanning loop
        logger.info("="*80)
        logger.info("STEP 7: Start Market Scanning")
        logger.info("="*80)
        logger.info(f"Symbols: {SYMBOLS}")
        logger.info(f"Timeframes: {TIMEFRAMES}")
        logger.info(f"Scan limit: {SCAN_LIMIT} bars")
        logger.info("="*80 + "\n")
        
        scan_count = 0
        
        while True:
            scan_count += 1
            logger.info(f"\n{'#'*80}")
            logger.info(f"SCAN #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'#'*80}\n")
            
            for symbol in SYMBOLS:
                for timeframe in TIMEFRAMES:
                    try:
                        # Fetch data
                        df = await fetcher.fetch_historical(
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=SCAN_LIMIT
                        )
                        
                        if len(df) == 0:
                            continue
                        
                        # Rebuild pivots
                        key = f"{symbol}_{timeframe}"
                        pivot_count = detector.rebuild_pivots(key, df)
                        
                        # Check for CHoCH
                        result = detector.process_new_bar(key, df)
                        
                        if result.get('choch_up') or result.get('choch_down'):
                            logger.info(f"\n🔔 CHoCH DETECTED!")
                            logger.info(f"   {symbol} {timeframe} {result.get('signal_type')}")
                            
                            # Convert to Signal object
                            signal = create_signal_from_choch(
                                symbol=symbol,
                                timeframe=timeframe,
                                result=result,
                                detector=detector
                            )
                            
                            if signal:
                                # Publish to signal bus
                                await signal_bus.publish(signal)
                            else:
                                logger.error("Failed to create signal")
                        
                        # Small delay between requests
                        await asyncio.sleep(0.1)
                    
                    except Exception as e:
                        logger.error(f"Error scanning {symbol} {timeframe}: {e}")
            
            # Print statistics
            logger.info(f"\n{'='*80}")
            logger.info(f"SCAN #{scan_count} COMPLETE")
            trading_bot.print_statistics()
            logger.info(f"{'='*80}\n")
            
            # Wait before next scan (simulate real-time scanning)
            # In production, this would be coordinated with candle close times
            logger.info("Waiting 60 seconds before next scan...\n")
            await asyncio.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("\n[STOP] Demo interrupted by user")
    
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
    
    finally:
        # Cleanup
        logger.info("\n" + "="*80)
        logger.info("CLEANUP")
        logger.info("="*80)
        
        # Stop trading bot
        if 'trading_bot' in locals():
            trading_bot.stop()
        
        # Cancel monitoring task
        if 'monitoring_task' in locals():
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close connections
        if 'fetcher' in locals():
            await fetcher.close()
        
        if 'exchange' in locals() and ENABLE_TRADING:
            await exchange.close()
        
        logger.info("✓ Cleanup complete")
        logger.info("="*80 + "\n")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n[EXIT] Demo terminated")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
