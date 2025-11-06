"""
Live Trading Bot - CHoCH Strategy Execution on Binance Futures Testnet/Production

This bot executes the CHoCH trading strategy in real-time:
- Monitors multiple symbols and timeframes
- Detects CHoCH signals using the same logic as backtest
- Places limit orders for Entry 1, Entry 2, TP, and SL
- Manages open positions with proper risk controls
- Supports both testnet and production environments

Strategy for LONG:
- Entry 1 (en1): Limit order at High pivot 6 (50% position)
- Entry 2 (en2): Limit order at CHoCH close (50% position)
- Take Profit (TP): Limit order at High pivot 5
- Stop Loss (SL): Stop market order at Low pivot 8

Strategy for SHORT:
- Entry 1 (en1): Limit order at Low pivot 6 (50% position)
- Entry 2 (en2): Limit order at CHoCH close (50% position)
- Take Profit (TP): Limit order at Low pivot 5
- Stop Loss (SL): Stop market order at High pivot 8
"""
import asyncio
import logging
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import ccxt.async_support as ccxt

# Import configuration
import config

# Import modules
from data.binance_fetcher_simple import BinanceFetcher
from data.timeframe_adapter import TimeframeAdapter
from detectors.choch_detector import ChochDetector
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

# Giảm log level cho các module ít quan trọng
logging.getLogger('detectors.choch_detector').setLevel(logging.WARNING)  # Chỉ show warning/error
logging.getLogger('data.binance_fetcher_simple').setLevel(logging.WARNING)
logging.getLogger('data.timeframe_adapter').setLevel(logging.WARNING)
logging.getLogger('data.aligned_candle_aggregator').setLevel(logging.WARNING)
logging.getLogger('ccxt').setLevel(logging.ERROR)  # CCXT chỉ show error
logging.getLogger('asyncio').setLevel(logging.ERROR)


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PositionSide(Enum):
    """Position side for futures"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class LiveOrder:
    """Live trading order"""
    order_id: str  # Exchange order ID
    client_order_id: str  # Our unique ID
    symbol: str
    order_type: str  # 'LIMIT', 'STOP_MARKET'
    side: str  # 'BUY', 'SELL'
    price: float
    quantity: float
    position_side: str  # 'LONG', 'SHORT'
    purpose: str  # 'ENTRY1', 'ENTRY2', 'TP', 'SL'
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime] = None
    exchange_data: Optional[Dict] = None


@dataclass
class Position:
    """Active trading position"""
    symbol: str
    timeframe: str
    direction: str  # 'Long', 'Short'
    pattern_group: str
    
    # Signal data
    signal_timestamp: datetime
    pivot5: float
    pivot6: float
    pivot8: float
    choch_price: float
    
    # TP/SL prices
    tp_price: float = 0.0
    sl_price: float = 0.0
    
    # Entry orders
    entry1_order: Optional[LiveOrder] = None
    entry2_order: Optional[LiveOrder] = None
    entry1_filled: bool = False
    entry2_filled: bool = False
    
    # Exit orders
    tp_order: Optional[LiveOrder] = None
    sl_order: Optional[LiveOrder] = None
    
    # Position tracking
    total_quantity: float = 0.0
    avg_entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    
    # State
    is_closed: bool = False
    closed_reason: Optional[str] = None
    closed_at: Optional[datetime] = None
    realized_pnl: float = 0.0


class TradingBot:
    """Live trading bot for CHoCH strategy"""
    
    def __init__(self, 
                 api_key: str,
                 api_secret: str,
                 testnet: bool = True,
                 position_size_usdt: float = 100,
                 max_positions: int = 3,
                 leverage: int = 1,
                 max_daily_trades: int = 20,
                 max_daily_loss: float = -500):
        """
        Initialize trading bot
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (True) or production (False)
            position_size_usdt: Position size in USDT per signal
            max_positions: Maximum concurrent positions
            leverage: Leverage to use (1-125)
            max_daily_trades: Maximum trades per day
            max_daily_loss: Maximum daily loss (negative number)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.position_size_usdt = position_size_usdt
        self.max_positions = max_positions
        self.leverage = leverage
        
        # Components
        self.exchange: Optional[ccxt.binance] = None
        self.fetcher: Optional[TimeframeAdapter] = None
        self.detector: Optional[ChochDetector] = None
        self.telegram: Optional[TelegramSender] = None
        
        # Trading state
        self.positions: Dict[str, Position] = {}  # key: symbol_timeframe
        self.orders: Dict[str, LiveOrder] = {}  # key: client_order_id
        
        # Risk management
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_daily_loss = max_daily_loss
        self.max_daily_trades = max_daily_trades
        
        # Running state
        self.is_running = False
        self.last_scan_times: Dict[str, datetime] = {}  # key: symbol_timeframe
        
    async def initialize(self):
        """Initialize bot components"""
        logger.info("="*80)
        logger.info("INITIALIZING LIVE TRADING BOT")
        logger.info("="*80)
        logger.info(f"Testnet: {self.testnet}")
        logger.info(f"Position Size: ${self.position_size_usdt} USDT")
        logger.info(f"Max Positions: {self.max_positions}")
        logger.info(f"Leverage: {self.leverage}x")
        logger.info(f"Max Daily Loss: ${abs(self.max_daily_loss)}")
        logger.info(f"Max Daily Trades: {self.max_daily_trades}")
        
        # Initialize exchange
        await self._init_exchange()
        
        # Initialize data fetcher
        base_fetcher = BinanceFetcher(
            api_key=self.api_key,
            secret=self.api_secret,
            testnet=self.testnet
        )
        self.fetcher = TimeframeAdapter(base_fetcher)
        await self.fetcher.initialize()
        
        # Initialize detector
        self.detector = ChochDetector(
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
        
        # Initialize Telegram
        self.telegram = TelegramSender(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_CHAT_ID
        )
        
        logger.info("✓ Bot initialized successfully")
        
    async def _init_exchange(self):
        """Initialize CCXT exchange connection"""
        config_dict = {
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'rateLimit': 50,
            'options': {
                'defaultType': 'future',
            }
        }
        

        self.exchange = ccxt.binance(config_dict)
        self.exchange.enable_demo_trading(True)
        await self.exchange.load_markets()
        
        logger.info(f"✓ Connected to Binance Futures")
        
        # Set position mode to One-Way (không dùng hedge mode)
        try:
            # Check current position mode
            response = await self.exchange.fapiPrivateGetPositionSideDual()
            dual_side = response.get('dualSidePosition', False)
            
            if dual_side:
                # Switch to One-Way mode
                await self.exchange.fapiPrivatePostPositionSideDual({'dualSidePosition': 'false'})
                logger.info("✓ Switched to One-Way position mode")
            else:
                logger.info("✓ Already in One-Way position mode")
        except Exception as e:
            logger.warning(f"⚠️  Could not set position mode: {e}")
        
        # Test connection
        try:
            balance = await self.exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            logger.info(f"✓ Account Balance: {usdt_balance:.2f} USDT")
        except Exception as e:
            logger.warning(f"⚠️  Could not fetch balance: {e}")
    
    async def start(self, symbols: List[str], timeframes: List[str]):
        """
        Start trading bot
        
        Args:
            symbols: List of symbols to monitor (e.g., ['BTCUSDT', 'ETHUSDT'])
            timeframes: List of timeframes (e.g., ['15m', '30m', '1h'])
        """
        logger.info("\n" + "="*80)
        logger.info("STARTING TRADING BOT")
        logger.info("="*80)
        logger.info(f"Monitoring {len(symbols)} symbols: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
        logger.info(f"Timeframes: {', '.join(timeframes)}")
        logger.info("="*80 + "\n")
        
        self.is_running = True
        
        # Send startup notification
        await self.telegram.send_message(
            f"🤖 <b>Trading Bot Started</b>\n\n"
            f"Environment: {'Testnet' if self.testnet else '🔴 PRODUCTION'}\n"
            f"Symbols: {len(symbols)}\n"
            f"Timeframes: {', '.join(timeframes)}\n"
            f"Position Size: ${self.position_size_usdt}\n"
            f"Max Positions: {self.max_positions}"
        )
        
        try:
            while self.is_running:
                # Check risk limits
                if not self._check_risk_limits():
                    logger.warning("Risk limits reached, pausing trading for today")
                    await asyncio.sleep(3600)  # Wait 1 hour
                    continue
                
                # Scan all symbol/timeframe combinations
                for symbol in symbols:
                    for timeframe in timeframes:
                        try:
                            await self._scan_market(symbol, timeframe)
                            await asyncio.sleep(0.1)  # Rate limiting
                        except Exception as e:
                            logger.error(f"Error scanning {symbol} {timeframe}: {e}")
                
                # Update all open positions
                await self._update_positions()
                
                # Wait before next scan cycle
                await asyncio.sleep(10)  # Scan every 10 seconds
        
        except KeyboardInterrupt:
            logger.info("\n⚠️  Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def _scan_market(self, symbol: str, timeframe: str):
        """Scan market for CHoCH signals"""
        key = f"{symbol}_{timeframe}"
        
        # Avoid scanning too frequently
        last_scan = self.last_scan_times.get(key)
        if last_scan:
            time_since_scan = (datetime.now() - last_scan).total_seconds()
            min_interval = self._timeframe_to_seconds(timeframe)
            if time_since_scan < min_interval * 0.8:  # Scan at 80% of candle interval
                return
        
        # Fetch latest data
        df = await self.fetcher.fetch_historical(
            symbol=symbol,
            timeframe=timeframe,
            limit=100
        )
        
        # ⬇️ VALIDATE: Cần đủ bars cho 3-candle confirmation
        if len(df) < 50:
            return
        
        # Rebuild pivots
        pivot_count = self.detector.rebuild_pivots(key, df)
        
        # ⬇️ CHECK STATE
        state = self.detector.states.get(key)
        if state is None or state.pivot_count() < 8:
            return  # Not enough pivots
        
        # Check for CHoCH signal với 3-candle confirmation
        result = self.detector.process_new_bar(key, df)
        
        if result.get('choch_up') or result.get('choch_down'):
            logger.info(f"\n{'='*80}")
            logger.info(f"🎯 CHoCH SIGNAL DETECTED: {symbol} {timeframe}")
            logger.info(f"Direction: {result.get('direction')}")
            logger.info(f"Pattern: {result.get('pattern_group')}")
            logger.info(f"CHoCH Price: {result.get('price', 0):.8f}")
            logger.info(f"CHoCH Time: {result.get('timestamp')}")
            logger.info(f"{'='*80}")
            
            # Process signal
            await self._handle_choch_signal(symbol, timeframe, df, result)
        
        self.last_scan_times[key] = datetime.now()
    
    async def _handle_choch_signal(self, symbol: str, timeframe: str, 
                                   df: pd.DataFrame, result: Dict):
        """Handle CHoCH signal and place orders"""
        key = f"{symbol}_{timeframe}"
        
        # Check if we already have a position for this symbol_timeframe
        if key in self.positions and not self.positions[key].is_closed:
            logger.warning(f"⚠️  Already have open position for {key}, skipping signal")
            return
        
        # Check max positions limit
        open_positions = sum(1 for p in self.positions.values() if not p.is_closed)
        if open_positions >= self.max_positions:
            logger.warning(f"⚠️  Max positions ({self.max_positions}) reached, skipping signal")
            return
        
        # Get pivot data
        state = self.detector.states.get(key)
        if state is None or state.pivot_count() < 8:
            logger.warning("Not enough pivots for trade setup")
            return
        
        b8, p8, h8 = state.get_pivot_from_end(0)  # Pivot 8
        b6, p6, h6 = state.get_pivot_from_end(2)  # Pivot 6
        b5, p5, h5 = state.get_pivot_from_end(3)  # Pivot 5
        b4, p4, h4 = state.get_pivot_from_end(4)  # Pivot 4
        
        direction = result.get('direction')
        pattern_group = result.get('pattern_group', 'Unknown')
        choch_price = result.get('price')
        choch_timestamp = result.get('timestamp')
        
        # Get bar 8 and bar 5 OHLC data
        try:
            bar8_data = df.iloc[b8]
            bar5_data = df.iloc[b5]
            bar4_data = df.iloc[b4]
        except Exception as e:
            logger.error(f"Error getting bar data: {e}")
            return
        
        # Setup trade parameters
        # Entry1 = High8/Low8 (swing high/low)
        # Entry2 = Body8 (open or close of bar 8)
        # TP = Body5 (open or close of bar 5)
        # SL = Body4 (open or close of bar 4)
        
        if direction == 'Long':
            en1 = bar8_data['low']      # Low of pivot 8 bar
            en2 = max(bar8_data['open'], bar8_data['close'])  # Body high of bar 8
            tp = max(bar5_data['open'], bar5_data['close'])   # Body high of bar 5
            sl = min(bar4_data['open'], bar4_data['close'])   # Body low of bar 4
            position_side = PositionSide.LONG
        else:  # Short
            en1 = bar8_data['high']     # High of pivot 8 bar
            en2 = min(bar8_data['open'], bar8_data['close'])  # Body low of bar 8
            tp = min(bar5_data['open'], bar5_data['close'])   # Body low of bar 5
            sl = max(bar4_data['open'], bar4_data['close'])   # Body high of bar 4
            position_side = PositionSide.SHORT
        
        logger.info(f"\n[{direction.upper()} SETUP]")
        logger.info(f"  Entry 1 (High8/Low8): {en1:.8f}")
        logger.info(f"  Entry 2 (Body8): {en2:.8f}")
        logger.info(f"  TP (Body5): {tp:.8f}")
        logger.info(f"  SL (Body4): {sl:.8f}")
        
        # Calculate position size
        try:
            # Get current price and calculate quantity
            ticker = await self.exchange.fetch_ticker(self._to_ccxt_symbol(symbol))
            current_price = ticker['last']
            
            # ⬇️ CHECK: Nếu giá đã vượt TP → skip signal (đã quá muộn)
            if direction == 'Long' and current_price >= tp:
                logger.warning(f"⚠️  Price already above TP ({current_price:.8f} >= {tp:.8f}), skipping signal")
                return
            elif direction == 'Short' and current_price <= tp:
                logger.warning(f"⚠️  Price already below TP ({current_price:.8f} <= {tp:.8f}), skipping signal")
                return
            
            # Each entry = 50% of total position size
            entry_size_usdt = self.position_size_usdt / 2
            
            # ⬇️ Calculate quantity for WORST CASE price (entry with lower notional)
            # For LONG: Entry2 (lower price) is worst case
            # For SHORT: Entry2 (lower price) is worst case
            worst_case_price = min(en1, en2) if direction == 'Long' else min(en1, en2)
            
            # Add 2% buffer to ensure notional >= $5 even with price fluctuation
            min_notional = 5.0  # Binance Futures minimum
            quantity_per_entry = (entry_size_usdt * 1.02) / worst_case_price
            
            # Verify both entries meet minimum notional
            notional1 = quantity_per_entry * en1
            notional2 = quantity_per_entry * en2
            
            if notional1 < min_notional or notional2 < min_notional:
                # Increase quantity to meet minimum
                required_qty = min_notional / worst_case_price
                quantity_per_entry = required_qty * 1.02  # +2% safety margin
            
            # Round to exchange precision
            quantity_per_entry = self._round_quantity(symbol, quantity_per_entry)
            
            logger.info(f"  Current Price: {current_price:.8f}")
            logger.info(f"  Quantity per entry: {quantity_per_entry}")
            logger.info(f"  Notional Entry1: ${quantity_per_entry * en1:.2f}")
            logger.info(f"  Notional Entry2: ${quantity_per_entry * en2:.2f}")
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return
        
        # Create position object
        position = Position(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            pattern_group=pattern_group,
            signal_timestamp=choch_timestamp,
            pivot5=p5,
            pivot6=p6,
            pivot8=p8,
            choch_price=choch_price
        )
        
        # Store TP/SL for later use when entry fills
        position.tp_price = tp
        position.sl_price = sl
        
        # Place orders
        try:
            # Entry 1 order (High8/Low8)
            entry1_order = await self._place_limit_order(
                symbol=symbol,
                side='BUY' if direction == 'Long' else 'SELL',
                price=en1,
                quantity=quantity_per_entry,
                position_side=position_side.value,
                purpose='ENTRY1'
            )
            position.entry1_order = entry1_order
            
            # Entry 2 order (Body8)
            entry2_order = await self._place_limit_order(
                symbol=symbol,
                side='BUY' if direction == 'Long' else 'SELL',
                price=en2,
                quantity=quantity_per_entry,
                position_side=position_side.value,
                purpose='ENTRY2'
            )
            position.entry2_order = entry2_order
            
            # Store position (TP/SL will be placed after entry fills)
            self.positions[key] = position
            
            logger.info(f"✓ Entry orders placed successfully for {key}")
            logger.info(f"  - Entry1: {entry1_order.order_id}")
            logger.info(f"  - Entry2: {entry2_order.order_id}")
            logger.info(f"  - TP/SL will be placed after entry fills")
            
            # Send Telegram notification
            await self.telegram.send_message(
                f"🎯 <b>New {direction.upper()} Signal</b>\n\n"
                f"Symbol: {symbol}\n"
                f"Timeframe: {timeframe}\n"
                f"Pattern: {pattern_group}\n\n"
                f"Entry 1: {en1:.8f}\n"
                f"Entry 2: {en2:.8f}\n"
                f"TP: {tp:.8f}\n"
                f"SL: {sl:.8f}\n\n"
                f"Position Size: ${self.position_size_usdt}\n"
                f"Orders: {len(self.positions)} active"
            )
            
        except Exception as e:
            logger.error(f"Error placing orders: {e}", exc_info=True)
            await self.telegram.send_message(
                f"❌ <b>Error Placing Orders</b>\n\n"
                f"Symbol: {symbol} {timeframe}\n"
                f"Error: {str(e)}"
            )
    
    async def _place_limit_order(self, symbol: str, side: str, price: float,
                                quantity: float, position_side: str, purpose: str) -> LiveOrder:
        """Place a limit order"""
        client_order_id = f"{purpose}_{symbol}_{int(datetime.now().timestamp()*1000)}"
        
        try:
            # Set leverage first
            await self.exchange.set_leverage(self.leverage, self._to_ccxt_symbol(symbol))
            
            # Place order (One-Way mode - không dùng positionSide)
            order = await self.exchange.create_order(
                symbol=self._to_ccxt_symbol(symbol),
                type='limit',
                side=side.lower(),
                amount=quantity,
                price=price,
                params={
                    'newClientOrderId': client_order_id
                }
            )
            
            # Create order object
            live_order = LiveOrder(
                order_id=order['id'],
                client_order_id=client_order_id,
                symbol=symbol,
                order_type='LIMIT',
                side=side,
                price=price,
                quantity=quantity,
                position_side=position_side,
                purpose=purpose,
                status=OrderStatus.OPEN,
                created_at=datetime.now(),
                exchange_data=order
            )
            
            # Store in orders dict
            self.orders[client_order_id] = live_order
            
            logger.info(f"✓ {purpose} order placed: {side} {quantity} @ {price}")
            
            return live_order
            
        except Exception as e:
            logger.error(f"Error placing {purpose} order: {e}")
            raise
    
    async def _place_stop_order(self, symbol: str, side: str, stop_price: float,
                               quantity: float, position_side: str, purpose: str) -> LiveOrder:
        """Place a stop-market order"""
        client_order_id = f"{purpose}_{symbol}_{int(datetime.now().timestamp()*1000)}"
        
        try:
            # Place stop-market order (One-Way mode - không dùng positionSide)
            order = await self.exchange.create_order(
                symbol=self._to_ccxt_symbol(symbol),
                type='STOP_MARKET',
                side=side.lower(),
                amount=quantity,
                params={
                    'stopPrice': stop_price,
                    'newClientOrderId': client_order_id
                }
            )
            
            # Create order object
            live_order = LiveOrder(
                order_id=order['id'],
                client_order_id=client_order_id,
                symbol=symbol,
                order_type='STOP_MARKET',
                side=side,
                price=stop_price,
                quantity=quantity,
                position_side=position_side,
                purpose=purpose,
                status=OrderStatus.OPEN,
                created_at=datetime.now(),
                exchange_data=order
            )
            
            # Store in orders dict
            self.orders[client_order_id] = live_order
            
            logger.info(f"✓ {purpose} order placed: {side} {quantity} @ stop {stop_price}")
            
            return live_order
            
        except Exception as e:
            logger.error(f"Error placing {purpose} stop order: {e}")
            raise
    
    async def _place_take_profit_order(self, symbol: str, side: str, stop_price: float,
                                      quantity: float, position_side: str, purpose: str) -> LiveOrder:
        """Place a take-profit limit order (TAKE_PROFIT_MARKET)"""
        client_order_id = f"{purpose}_{symbol}_{int(datetime.now().timestamp()*1000)}"
        
        try:
            # Place take-profit market order
            order = await self.exchange.create_order(
                symbol=self._to_ccxt_symbol(symbol),
                type='TAKE_PROFIT_MARKET',
                side=side.lower(),
                amount=quantity,
                params={
                    'stopPrice': stop_price,
                    'newClientOrderId': client_order_id
                }
            )
            
            live_order = LiveOrder(
                order_id=order['id'],
                client_order_id=client_order_id,
                symbol=symbol,
                order_type='TAKE_PROFIT_MARKET',
                side=side,
                price=stop_price,
                quantity=quantity,
                position_side=position_side,
                purpose=purpose,
                status=OrderStatus.OPEN,
                created_at=datetime.now(),
                exchange_data=order
            )
            
            self.orders[client_order_id] = live_order
            logger.info(f"✓ {purpose} order placed: {side} {quantity} @ TP {stop_price}")
            return live_order
            
        except Exception as e:
            logger.error(f"Error placing {purpose} TP order: {e}")
            raise
    
    async def _place_stop_loss_order(self, symbol: str, side: str, stop_price: float,
                                     quantity: float, position_side: str, purpose: str) -> LiveOrder:
        """Place a stop-loss market order (STOP_MARKET)"""
        client_order_id = f"{purpose}_{symbol}_{int(datetime.now().timestamp()*1000)}"
        
        try:
            # Place stop-loss market order
            order = await self.exchange.create_order(
                symbol=self._to_ccxt_symbol(symbol),
                type='STOP_MARKET',
                side=side.lower(),
                amount=quantity,
                params={
                    'stopPrice': stop_price,
                    'newClientOrderId': client_order_id
                }
            )
            
            live_order = LiveOrder(
                order_id=order['id'],
                client_order_id=client_order_id,
                symbol=symbol,
                order_type='STOP_MARKET',
                side=side,
                price=stop_price,
                quantity=quantity,
                position_side=position_side,
                purpose=purpose,
                status=OrderStatus.OPEN,
                created_at=datetime.now(),
                exchange_data=order
            )
            
            self.orders[client_order_id] = live_order
            logger.info(f"✓ {purpose} order placed: {side} {quantity} @ SL {stop_price}")
            return live_order
            
        except Exception as e:
            logger.error(f"Error placing {purpose} SL order: {e}")
            raise
    
    async def _update_positions(self):
        """Update all open positions and check order statuses"""
        for key, position in list(self.positions.items()):
            if position.is_closed:
                continue
            
            try:
                # ⬇️ CHECK: Nếu price vượt TP → cancel pending entries
                ticker = await self.exchange.fetch_ticker(self._to_ccxt_symbol(position.symbol))
                current_price = ticker['last']
                
                # Check if price reached TP before any entry filled
                tp_reached = False
                if position.direction == 'Long' and current_price >= position.tp_price:
                    tp_reached = True
                elif position.direction == 'Short' and current_price <= position.tp_price:
                    tp_reached = True
                
                if tp_reached and not position.entry1_filled and not position.entry2_filled:
                    logger.warning(f"⚠️  Price reached TP before entry filled, cancelling orders for {key}")
                    await self._cancel_pending_entries(position)
                    position.is_closed = True
                    continue
                
                # Check entry orders
                if position.entry1_order and not position.entry1_filled:
                    filled = await self._check_order_filled(position.entry1_order)
                    if filled:
                        position.entry1_filled = True
                        position.total_quantity += position.entry1_order.quantity
                        await self._on_entry_filled(position, 1)
                
                if position.entry2_order and not position.entry2_filled:
                    filled = await self._check_order_filled(position.entry2_order)
                    if filled:
                        position.entry2_filled = True
                        position.total_quantity += position.entry2_order.quantity
                        await self._on_entry_filled(position, 2)
                
                # If one entry filled and price reached TP → cancel other pending entry
                if tp_reached and (position.entry1_filled or position.entry2_filled):
                    if position.entry1_order and not position.entry1_filled:
                        await self._cancel_order(position.entry1_order)
                    if position.entry2_order and not position.entry2_filled:
                        await self._cancel_order(position.entry2_order)
                
                # Check exit orders
                if position.tp_order:
                    filled = await self._check_order_filled(position.tp_order)
                    if filled:
                        await self._close_position(position, 'TP')
                
                if position.sl_order:
                    filled = await self._check_order_filled(position.sl_order)
                    if filled:
                        await self._close_position(position, 'SL')
                
            except Exception as e:
                logger.error(f"Error updating position {key}: {e}")
    
    async def _check_order_filled(self, order: LiveOrder) -> bool:
        """Check if an order has been filled"""
        if order.status == OrderStatus.FILLED:
            return True
        
        try:
            # Fetch order status from exchange
            exchange_order = await self.exchange.fetch_order(
                order.order_id,
                self._to_ccxt_symbol(order.symbol)
            )
            
            if exchange_order['status'] == 'closed':
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now()
                order.exchange_data = exchange_order
                logger.info(f"✓ {order.purpose} order filled: {order.symbol} @ {order.price}")
                return True
            
        except Exception as e:
            logger.error(f"Error checking order {order.order_id}: {e}")
        
        return False
    
    async def _on_entry_filled(self, position: Position, entry_num: int):
        """Handle entry order fill"""
        logger.info(f"📥 Entry {entry_num} filled for {position.symbol} {position.timeframe}")
        
        # Update average entry price
        total_cost = 0
        if position.entry1_filled:
            total_cost += position.entry1_order.price * position.entry1_order.quantity
        if position.entry2_filled:
            total_cost += position.entry2_order.price * position.entry2_order.quantity
        
        position.avg_entry_price = total_cost / position.total_quantity
        
        # Send notification
        await self.telegram.send_message(
            f"📥 <b>Entry {entry_num} Filled</b>\n\n"
            f"Symbol: {position.symbol} {position.timeframe}\n"
            f"Direction: {position.direction}\n"
            f"Price: {position.entry1_order.price if entry_num == 1 else position.entry2_order.price:.8f}\n"
            f"Quantity: {position.total_quantity}\n"
            f"Avg Entry: {position.avg_entry_price:.8f}"
        )
    
    async def _place_exit_orders(self, position: Position):
        """Place TP and SL orders after entry is filled"""
        try:
            # Calculate TP/SL prices and quantities
            if position.direction == 'Long':
                tp_side = 'SELL'
                sl_side = 'SELL'
                tp_price = position.pivot5
                sl_price = position.pivot8
            else:
                tp_side = 'BUY'
                sl_side = 'BUY'
                tp_price = position.pivot5
                sl_price = position.pivot8
            
            # We need total quantity (both entries) for TP/SL
            # But we'll place orders for current filled quantity
            # and update them if second entry fills
            total_expected_qty = position.total_quantity
            if position.entry1_order and not position.entry1_filled:
                total_expected_qty += position.entry1_order.quantity
            if position.entry2_order and not position.entry2_filled:
                total_expected_qty += position.entry2_order.quantity
            
            # Place TP order (limit)
            position.tp_order = await self._place_limit_order(
                symbol=position.symbol,
                side=tp_side,
                price=tp_price,
                quantity=total_expected_qty,
                position_side=position.direction.upper(),
                purpose='TP'
            )
            
            # Place SL order (stop-market)
            position.sl_order = await self._place_stop_order(
                symbol=position.symbol,
                side=sl_side,
                stop_price=sl_price,
                quantity=total_expected_qty,
                position_side=position.direction.upper(),
                purpose='SL'
            )
            
            logger.info(f"✓ TP/SL orders placed for {position.symbol} {position.timeframe}")
            
        except Exception as e:
            logger.error(f"Error placing exit orders: {e}")
    
    async def _close_position(self, position: Position, reason: str):
        """Close position and calculate P&L"""
        position.is_closed = True
        position.closed_reason = reason
        position.closed_at = datetime.now()
        
        # Calculate P&L
        if reason == 'TP':
            exit_price = position.pivot5
        elif reason == 'SL':
            exit_price = position.pivot8
        else:
            exit_price = position.avg_entry_price
        
        if position.direction == 'Long':
            pnl_pct = ((exit_price - position.avg_entry_price) / position.avg_entry_price) * 100
        else:
            pnl_pct = ((position.avg_entry_price - exit_price) / position.avg_entry_price) * 100
        
        pnl_usdt = (pnl_pct / 100) * self.position_size_usdt
        position.realized_pnl = pnl_usdt
        
        # Update daily P&L
        self.daily_pnl += pnl_usdt
        self.daily_trades += 1
        
        # Cancel unfilled orders
        if position.entry1_order and not position.entry1_filled:
            await self._cancel_order(position.entry1_order)
        if position.entry2_order and not position.entry2_filled:
            await self._cancel_order(position.entry2_order)
        if reason == 'TP' and position.sl_order:
            await self._cancel_order(position.sl_order)
        elif reason == 'SL' and position.tp_order:
            await self._cancel_order(position.tp_order)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔴 POSITION CLOSED: {position.symbol} {position.timeframe}")
        logger.info(f"Reason: {reason}")
        logger.info(f"P&L: {pnl_pct:+.2f}% (${pnl_usdt:+.2f})")
        logger.info(f"Daily P&L: ${self.daily_pnl:+.2f}")
        logger.info(f"{'='*80}\n")
        
        # Send notification
        await self.telegram.send_message(
            f"{'🎉' if pnl_usdt > 0 else '😞'} <b>Position Closed - {reason}</b>\n\n"
            f"Symbol: {position.symbol} {position.timeframe}\n"
            f"Direction: {position.direction}\n"
            f"Entry: {position.avg_entry_price:.8f}\n"
            f"Exit: {exit_price:.8f}\n"
            f"P&L: {pnl_pct:+.2f}% (${pnl_usdt:+.2f})\n\n"
            f"Daily P&L: ${self.daily_pnl:+.2f}\n"
            f"Daily Trades: {self.daily_trades}"
        )
    
    async def _cancel_order(self, order: LiveOrder):
        """Cancel an order"""
        try:
            await self.exchange.cancel_order(
                order.order_id,
                self._to_ccxt_symbol(order.symbol)
            )
            order.status = OrderStatus.CANCELLED
            logger.info(f"✓ Cancelled {order.purpose} order: {order.symbol}")
        except Exception as e:
            logger.error(f"Error cancelling order {order.order_id}: {e}")
    
    async def _cancel_pending_entries(self, position: Position):
        """Cancel all pending entry orders"""
        cancelled_count = 0
        
        if position.entry1_order and not position.entry1_filled:
            await self._cancel_order(position.entry1_order)
            cancelled_count += 1
        
        if position.entry2_order and not position.entry2_filled:
            await self._cancel_order(position.entry2_order)
            cancelled_count += 1
        
        logger.info(f"✓ Cancelled {cancelled_count} pending entry orders for {position.symbol}")
    
    def _check_risk_limits(self) -> bool:
        """Check if risk limits are breached"""
        if self.daily_pnl <= self.max_daily_loss:
            logger.error(f"❌ Daily loss limit reached: ${self.daily_pnl:.2f}")
            return False
        
        if self.daily_trades >= self.max_daily_trades:
            logger.warning(f"⚠️  Daily trade limit reached: {self.daily_trades}")
            return False
        
        return True
    
    async def stop(self):
        """Stop trading bot"""
        logger.info("\n" + "="*80)
        logger.info("STOPPING TRADING BOT")
        logger.info("="*80)
        
        self.is_running = False
        
        # Cancel all open orders
        for position in self.positions.values():
            if not position.is_closed:
                logger.info(f"Closing position: {position.symbol} {position.timeframe}")
                # Cancel all orders for this position
                for order in [position.entry1_order, position.entry2_order, 
                             position.tp_order, position.sl_order]:
                    if order and order.status == OrderStatus.OPEN:
                        await self._cancel_order(order)
        
        # Close exchange connection
        if self.exchange:
            await self.exchange.close()
        
        if self.fetcher:
            await self.fetcher.close()
        
        # Send shutdown notification
        await self.telegram.send_message(
            f"🛑 <b>Trading Bot Stopped</b>\n\n"
            f"Final Daily P&L: ${self.daily_pnl:+.2f}\n"
            f"Total Trades: {self.daily_trades}\n"
            f"Open Positions: {sum(1 for p in self.positions.values() if not p.is_closed)}"
        )
        
        logger.info("✓ Bot stopped successfully")
    
    def _to_ccxt_symbol(self, symbol: str) -> str:
        """Convert BTCUSDT to BTC/USDT:USDT"""
        if '/' in symbol or ':' in symbol:
            return symbol
        
        for quote in ['USDT', 'BUSD', 'BTC', 'ETH']:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}:{quote}"
        
        return symbol
    
    def _round_quantity(self, symbol: str, quantity: float) -> float:
        """Round quantity to exchange precision"""
        # Simplified - in production, fetch from exchange.markets
        return round(quantity, 3)
    
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convert timeframe to seconds"""
        mapping = {
            '1m': 60, '5m': 300, '15m': 900, '30m': 1800,
            '1h': 3600, '4h': 14400, '1d': 86400
        }
        return mapping.get(timeframe, 3600)


async def main():
    """Main entry point"""
    logger.info("="*80)
    logger.info("CHoCH LIVE TRADING BOT")
    logger.info("="*80 + "\n")
    
    # Configuration
    USE_TESTNET = os.getenv('USE_TESTNET', '1') == '1'
    POSITION_SIZE = float(os.getenv('POSITION_SIZE_USDT', '10'))
    MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', '999'))
    LEVERAGE = int(os.getenv('LEVERAGE', '20'))
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '999'))
    MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', '-999999'))
    
    # Get API credentials
    if not config.BINANCE_API_KEY or not config.BINANCE_SECRET:
        logger.error("❌ API credentials not found!")
        logger.error("Please set BINANCE_API_KEY and BINANCE_SECRET in .env file")
        return
    
    # Initialize bot
    bot = TradingBot(
        api_key=config.BINANCE_API_KEY,
        api_secret=config.BINANCE_SECRET,
        testnet=USE_TESTNET,
        position_size_usdt=POSITION_SIZE,
        max_positions=MAX_POSITIONS,
        leverage=LEVERAGE,
        max_daily_trades=MAX_DAILY_TRADES,
        max_daily_loss=MAX_DAILY_LOSS
    )
    
    await bot.initialize()
    
    # Get symbols to monitor
    symbols = config.get_symbols_list()
    if symbols == 'ALL':
        symbols = await bot.fetcher.get_all_usdt_pairs(
            min_volume_24h=config.MIN_VOLUME_24H,
            quote=config.QUOTE_CURRENCY
        )

    
    timeframes = config.TIMEFRAMES
    
    # Start bot
    await bot.start(symbols, timeframes)


if __name__ == '__main__':
    import os
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n[STOP] Bot interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
