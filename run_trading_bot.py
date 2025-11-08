"""
Trading Bot Runner - Production/Demo Mode
Integrates CHoCH scanner with automated trading

Configuration via .env:
- ENABLE_TRADING=1    # Enable real trading (0=simulation only)
- DEMO_TRADING=1      # Use testnet (1=testnet, 0=live)
- POSITION_SIZE=100   # Position size in USDT
- LEVERAGE=20         # Leverage multiplier

Run: python run_trading_bot.py
"""
import asyncio
import logging
import sys
from datetime import datetime

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
from alert.telegram_sender import TelegramSender

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

async def send_telegram_alert(message: str):
    """Send Telegram alert message"""
    sender = TelegramSender(
        bot_token=config.TELEGRAM_BOT_TOKEN,
        chat_id=config.TELEGRAM_CHAT_ID
    )
    await sender.send_message(message, parse_mode='Markdown')
async def telegram_alert_handler(signal):
    """Send Telegram alert for each signal"""
    try:
        message = (
            f"🔔 *CHoCH Alert*\n\n"
            f"Symbol: `{signal.symbol}`\n"
            f"Timeframe: `{signal.timeframe}`\n"
            f"Direction: *{signal.direction}*\n"
            f"Pattern: {signal.pattern_group}\n\n"
            f"Entry 1: `${signal.entry1_price:.2f}` (Conservative)\n"
            f"Entry 2: `${signal.entry2_price:.2f}` (Aggressive)\n"
            f"TP: `${signal.tp_price:.2f}`\n"
            f"SL: `${signal.sl_price:.2f}`\n\n"
            f"Time: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await send_telegram_alert(message)
        logger.info(f"✓ Telegram alert sent for {signal.symbol} {signal.timeframe}")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


async def main():
    """Main trading bot function"""
    logger.info("\n" + "="*80)
    logger.info("CHOCH TRADING BOT")
    logger.info("="*80)
    
    # Determine mode
    if config.ENABLE_TRADING:
        if config.DEMO_TRADING:
            mode = "DEMO TRADING 🧪 (Testnet)"
            warning = False
        else:
            mode = "LIVE TRADING ⚠️⚠️⚠️ (REAL MONEY!)"
            warning = True
    else:
        mode = "SIMULATION ONLY 💻 (No orders)"
        warning = False
    
    logger.info(f"Mode: {mode}")
    logger.info(f"Position: ${config.POSITION_SIZE} USDT @ {config.LEVERAGE}x leverage")
    logger.info(f"Symbols: {config.SYMBOLS or 'BTCUSDT,ETHUSDT'}")
    logger.info(f"Timeframes: {','.join(config.TIMEFRAMES)}")
    logger.info("="*80 + "\n")
    
    # Warning for live trading
    if warning:
        logger.warning("⚠️  LIVE TRADING - REAL MONEY AT RISK!")
        logger.warning("Press Ctrl+C within 10 seconds to cancel...\n")
        await asyncio.sleep(10)
    
    # Get symbols to monitor
    if config.SYMBOLS:
        symbols = [s.strip() for s in config.SYMBOLS.split(',') if s.strip()]
    else:
        symbols = ['BTCUSDT', 'ETHUSDT']  # Default symbols
    
    timeframes = config.TIMEFRAMES
    
    exchange = None
    fetcher = None
    monitoring_task = None
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        
        # Exchange
        exchange = BinanceFuturesAdapter(
            api_key=config.BINANCE_API_KEY,
            secret=config.BINANCE_SECRET,
            demo_mode=config.DEMO_TRADING
        )
        
        if config.ENABLE_TRADING:
            await exchange.initialize()
        
        # Position manager
        position_manager = PositionManager(
            exchange=exchange,
            enable_trading=config.ENABLE_TRADING
        )
        position_manager.position_size = config.POSITION_SIZE
        position_manager.leverage = config.LEVERAGE
        position_manager.margin = config.POSITION_SIZE / config.LEVERAGE
        
        # Trading bot
        trading_bot = TradingBot(
            position_manager=position_manager,
            enable_trading=config.ENABLE_TRADING
        )
        
        # Signal bus
        signal_bus = get_signal_bus()
        trading_bot.start()
        signal_bus.subscribe(telegram_alert_handler)
        logger.info(f"✓ Signal bus: {signal_bus.get_subscriber_count()} subscribers\n")
        
        # Scanner
        base_fetcher = BinanceFetcher(
            api_key=config.BINANCE_API_KEY,
            secret=config.BINANCE_SECRET,
            testnet=config.DEMO_TRADING
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
        
        # Start monitoring
        monitoring_task = asyncio.create_task(
            trading_bot.run_monitoring_loop(update_interval=10.0)
        )
        
        logger.info("="*80)
        logger.info("SCANNING STARTED")
        logger.info("="*80 + "\n")
        
        scan_count = 0
        scan_limit = 100
        
        while True:
            scan_count += 1
            logger.info(f"[Scan #{scan_count}] {datetime.now().strftime('%H:%M:%S')}")
            
            for symbol in symbols:
                for timeframe in timeframes:
                    try:
                        # Fetch data
                        df = await fetcher.fetch_historical(
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=scan_limit
                        )
                        
                        if len(df) == 0:
                            continue
                        
                        # Rebuild pivots
                        key = f"{symbol}_{timeframe}"
                        pivot_count = detector.rebuild_pivots(key, df)
                        
                        # Check for CHoCH
                        result = detector.process_new_bar(key, df)
                        
                        if result.get('choch_up') or result.get('choch_down'):
                            logger.info(f"🔔 {symbol} {timeframe} {result.get('signal_type')}")
                            
                            # Convert to Signal object
                            signal = create_signal_from_choch(
                                symbol=symbol,
                                timeframe=timeframe,
                                result=result,
                                detector=detector
                            )
                            
                            if signal:
                                # Publish to signal bus (trading bot + telegram)
                                await signal_bus.publish(signal)
                            else:
                                logger.error("Failed to create signal")
                        
                        # Small delay between requests
                        await asyncio.sleep(0.05)
                    
                    except Exception as e:
                        logger.error(f"Error: {symbol} {timeframe} - {e}")
            
            # Statistics every 10 scans
            if scan_count % 10 == 0:
                trading_bot.print_statistics()
            
            # Wait before next scan
            await asyncio.sleep(config.UPDATE_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("\n[STOP] Bot interrupted by user")
    
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    
    finally:
        # Cleanup
        logger.info("\nCleaning up...")
        
        if 'trading_bot' in locals():
            trading_bot.stop()
        
        if monitoring_task:
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
        
        if fetcher:
            await fetcher.close()
        
        if exchange and config.ENABLE_TRADING:
            await exchange.close()
        
        logger.info("✓ Shutdown complete\n")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n[EXIT] Bot terminated")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
