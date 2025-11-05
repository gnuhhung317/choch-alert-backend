"""
CHoCH Backtest Bot - Testing trading strategy with historical data

Strategy for LONG:
- Entry 1 (en1): High pivot 6
- Entry 2 (en2): Close CHoCH candle
- Take Profit (TP): High pivot 5
- Stop Loss (SL): Low pivot 8
- Cancel all orders if TP is hit

Strategy for SHORT:
- Entry 1 (en1): Low pivot 6
- Entry 2 (en2): Close CHoCH candle
- Take Profit (TP): Low pivot 5
- Stop Loss (SL): High pivot 8
- Cancel all orders if TP is hit
"""
import asyncio
import logging
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Import configuration
import config

# Import modules
from data.binance_fetcher import BinanceFetcher
from data.timeframe_adapter import TimeframeAdapter
from detectors.choch_detector import ChochDetector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backtest.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


class OrderType(Enum):
    """Order type enumeration"""
    ENTRY1 = "entry1"
    ENTRY2 = "entry2"
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"


@dataclass
class Order:
    """Trading order"""
    order_id: int
    order_type: OrderType
    direction: str  # 'Long' or 'Short'
    price: float
    timestamp: pd.Timestamp
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_timestamp: Optional[pd.Timestamp] = None
    quantity: float = 1.0  # Default position size


@dataclass
class Trade:
    """Completed trade record"""
    trade_id: int
    signal_timestamp: pd.Timestamp
    direction: str  # 'Long' or 'Short'
    pattern_group: str  # G1, G2, G3
    
    # Entry details
    entry1_price: float
    entry1_filled: bool
    entry1_timestamp: Optional[pd.Timestamp]
    
    entry2_price: float
    entry2_filled: bool
    entry2_timestamp: Optional[pd.Timestamp]
    
    # Exit details
    tp_price: float
    sl_price: float
    exit_price: float
    exit_timestamp: pd.Timestamp
    exit_reason: str  # 'TP', 'SL', 'FORCED_CLOSE_NEW_SIGNAL'
    
    # P&L
    pnl_percentage: float
    pnl_absolute: float
    
    # Pivot data for reference
    pivot5: float
    pivot6: float
    pivot8: float
    choch_price: float


@dataclass 
class BacktestResult:
    """Backtest results summary"""
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    total_bars: int
    
    # Trade statistics
    total_signals: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    
    # Performance metrics
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    avg_pnl_pct: float
    total_pnl_pct: float
    
    profit_factor: float
    max_drawdown_pct: float
    
    # Trade details
    trades: List[Trade] = field(default_factory=list)
    
    def print_summary(self):
        """Print backtest summary"""
        logger.info("\n" + "="*80)
        logger.info("BACKTEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Timeframe: {self.timeframe}")
        logger.info(f"Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Total Bars: {self.total_bars}")
        logger.info("-"*80)
        logger.info(f"Total Signals: {self.total_signals}")
        logger.info(f"Total Trades: {self.total_trades}")
        logger.info(f"Winning Trades: {self.winning_trades}")
        logger.info(f"Losing Trades: {self.losing_trades}")
        logger.info(f"Win Rate: {self.win_rate:.2%}")
        logger.info("-"*80)
        logger.info(f"Average Win: {self.avg_win_pct:+.2f}%")
        logger.info(f"Average Loss: {self.avg_loss_pct:+.2f}%")
        logger.info(f"Average P&L: {self.avg_pnl_pct:+.2f}%")
        logger.info(f"Total P&L: {self.total_pnl_pct:+.2f}%")
        logger.info(f"Profit Factor: {self.profit_factor:.2f}")
        logger.info(f"Max Drawdown: {self.max_drawdown_pct:.2f}%")
        logger.info("="*80 + "\n")


class BacktestEngine:
    """Backtest engine for CHoCH strategy"""
    
    def __init__(self, detector: ChochDetector, fetcher: TimeframeAdapter):
        self.detector = detector
        self.fetcher = fetcher
        
        # Backtest state
        self.current_trade: Optional[Dict] = None
        self.pending_orders: List[Order] = []
        self.completed_trades: List[Trade] = []
        self.trade_counter = 0
        self.order_counter = 0
        
    def reset(self):
        """Reset backtest state"""
        self.current_trade = None
        self.pending_orders = []
        self.completed_trades = []
        self.trade_counter = 0
        self.order_counter = 0
        
    async def run_backtest(self, symbol: str, timeframe: str, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          limit: int = 1000) -> BacktestResult:
        """
        Run backtest on historical data
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe to test
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Number of bars to fetch
        
        Returns:
            BacktestResult with performance metrics
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"STARTING BACKTEST: {symbol} {timeframe}")
        logger.info(f"{'='*80}\n")
        
        # Reset state
        self.reset()
        
        # Fetch historical data
        logger.info(f"Fetching {limit} bars of historical data...")
        df = await self.fetcher.fetch_historical(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )
        
        if len(df) == 0:
            logger.error("No data received")
            return None
        
        logger.info(f"Received {len(df)} bars from {df.index[0]} to {df.index[-1]}")
        
        # Initialize detector state
        key = f"{symbol}_{timeframe}"
        
        # Process historical data bar by bar
        logger.info("\nProcessing historical data...")
        signal_count = 0
        
        for i in range(50, len(df)):  # Start after 50 bars for pivot building
            # Get window of data up to current bar
            window_df = df.iloc[:i+1].copy()
            
            # Rebuild pivots from window (matching production logic)
            pivot_count = self.detector.rebuild_pivots(key, window_df)
            
            # ========== FIX BUG 2: PREVENT LOOK-AHEAD BIAS ==========
            # Check orders BEFORE detecting new signal on current bar
            # This ensures orders can only fill on bars AFTER signal creation
            current_bar = df.iloc[i]
            current_idx = df.index[i]
            await self.check_orders(current_bar, current_idx)
            
            # Check for CHoCH signal on CURRENT BAR (bar i)
            # Signal is based on CLOSED candle, so we know all OHLC
            if i >= 52:  # Need at least 3 bars for confirmation
                result = self.detector.process_new_bar(key, window_df)
                
                if result.get('choch_up') or result.get('choch_down'):
                    signal_count += 1
                    logger.info(f"\n[SIGNAL #{signal_count}] {result.get('signal_type')} @ {window_df.index[-1]}")
                    
                    # Process CHoCH signal - creates orders for FUTURE bars
                    await self.on_choch_signal(
                        symbol=symbol,
                        timeframe=timeframe,
                        df=window_df,
                        result=result
                    )
                    # NOTE: Orders created here can only fill on bar i+1 and later
                    # because check_orders was already called for bar i above
        
        # Calculate backtest results
        result = self.calculate_results(symbol, timeframe, df)
        
        # Print summary
        result.print_summary()
        
        # Print trade details
        self.print_trade_details()
        
        return result
    
    async def on_choch_signal(self, symbol: str, timeframe: str, 
                             df: pd.DataFrame, result: Dict):
        """
        Handle CHoCH signal and create orders
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            df: DataFrame up to signal bar
            result: CHoCH detection result
        """
        # Get detector state
        key = f"{symbol}_{timeframe}"
        state = self.detector.states.get(key)
        
        if state is None or state.pivot_count() < 8:
            logger.warning("Not enough pivots for trade setup")
            return
        
        # Get pivot data
        b8, p8, h8 = state.get_pivot_from_end(0)  # Pivot 8
        b7, p7, h7 = state.get_pivot_from_end(1)
        b6, p6, h6 = state.get_pivot_from_end(2)  # Pivot 6
        b5, p5, h5 = state.get_pivot_from_end(3)  # Pivot 5
        b4, p4, h4 = state.get_pivot_from_end(4)
        
        direction = result.get('direction')  # 'Long' or 'Short'
        pattern_group = result.get('pattern_group', 'Unknown')
        choch_price = result.get('price')
        choch_timestamp = result.get('timestamp')
        
        # ========== FIX BUG 1: HANDLE OVERLAPPING SIGNALS ==========
        # If there's an existing trade, we MUST close it first before opening new one
        if self.current_trade is not None:
            logger.warning("⚠️  OVERLAPPING SIGNAL DETECTED!")
            
            # Check if old trade has any position filled
            has_old_position = (self.current_trade['entry1_filled'] or 
                              self.current_trade['entry2_filled'])
            
            if has_old_position:
                logger.warning("⚠️  Old trade has OPEN POSITION - Force closing at market!")
                logger.info(f"   Old trade direction: {self.current_trade['direction']}")
                logger.info(f"   Entry1 filled: {self.current_trade['entry1_filled']}")
                logger.info(f"   Entry2 filled: {self.current_trade['entry2_filled']}")
                
                # Force close at current market price (use CHoCH bar close as approximation)
                # In reality, this would be a market order at next open
                force_exit_price = choch_price
                force_exit_reason = 'FORCED_CLOSE_NEW_SIGNAL'
                
                logger.info(f"   Force exit at: {force_exit_price:.8f}")
                
                # Cancel all pending orders first
                self.cancel_all_orders()
                
                # Close the old trade with market price
                self.close_trade(force_exit_reason, force_exit_price, choch_timestamp)
                
                logger.info("✓ Old position closed, ready for new signal")
            else:
                # No position filled yet, just cancel orders
                logger.info("   Old trade has no position - only cancelling orders")
                self.cancel_all_orders()
                # Reset current trade since no position to close
                self.current_trade = None
                self.pending_orders = []
        
        # Setup new trade
        if direction == 'Long':
            # LONG strategy
            en1 = p6  # High pivot 6 (should be high)
            en2 = choch_price  # Close CHoCH
            tp = p5   # High pivot 5 (should be high)
            sl = p8   # Low pivot 8 (should be low)
            
            # Validate pivot types
            if not h6:
                logger.warning(f"Pivot 6 is not a high! Using value anyway: {p6}")
            if not h5:
                logger.warning(f"Pivot 5 is not a high! Using value anyway: {p5}")
            if h8:
                logger.warning(f"Pivot 8 is not a low! Using value anyway: {p8}")
            
            logger.info(f"[LONG SETUP]")
            logger.info(f"  Entry 1: {en1:.8f} (High P6)")
            logger.info(f"  Entry 2: {en2:.8f} (CHoCH Close)")
            logger.info(f"  TP: {tp:.8f} (High P5)")
            logger.info(f"  SL: {sl:.8f} (Low P8)")
            
        else:  # Short
            # SHORT strategy
            en1 = p6  # Low pivot 6 (should be low)
            en2 = choch_price  # Close CHoCH
            tp = p5   # Low pivot 5 (should be low)
            sl = p8   # High pivot 8 (should be high)
            
            # Validate pivot types
            if h6:
                logger.warning(f"Pivot 6 is not a low! Using value anyway: {p6}")
            if h5:
                logger.warning(f"Pivot 5 is not a low! Using value anyway: {p5}")
            if not h8:
                logger.warning(f"Pivot 8 is not a high! Using value anyway: {p8}")
            
            logger.info(f"[SHORT SETUP]")
            logger.info(f"  Entry 1: {en1:.8f} (Low P6)")
            logger.info(f"  Entry 2: {en2:.8f} (CHoCH Close)")
            logger.info(f"  TP: {tp:.8f} (Low P5)")
            logger.info(f"  SL: {sl:.8f} (High P8)")
        
        # Create trade record
        self.current_trade = {
            'direction': direction,
            'pattern_group': pattern_group,
            'signal_timestamp': choch_timestamp,
            'en1': en1,
            'en2': en2,
            'tp': tp,
            'sl': sl,
            'pivot5': p5,
            'pivot6': p6,
            'pivot8': p8,
            'choch_price': choch_price,
            'entry1_filled': False,
            'entry2_filled': False,
            'tp_hit': False,
            'sl_hit': False
        }
        
        # Create orders
        self.create_orders(direction, en1, en2, tp, sl, choch_timestamp)
    
    def create_orders(self, direction: str, en1: float, en2: float, 
                     tp: float, sl: float, timestamp: pd.Timestamp):
        """Create entry, TP, and SL orders"""
        # Entry 1 order
        order1 = Order(
            order_id=self.order_counter,
            order_type=OrderType.ENTRY1,
            direction=direction,
            price=en1,
            timestamp=timestamp
        )
        self.pending_orders.append(order1)
        self.order_counter += 1
        
        # Entry 2 order
        order2 = Order(
            order_id=self.order_counter,
            order_type=OrderType.ENTRY2,
            direction=direction,
            price=en2,
            timestamp=timestamp
        )
        self.pending_orders.append(order2)
        self.order_counter += 1
        
        # Take Profit order
        tp_order = Order(
            order_id=self.order_counter,
            order_type=OrderType.TAKE_PROFIT,
            direction=direction,
            price=tp,
            timestamp=timestamp
        )
        self.pending_orders.append(tp_order)
        self.order_counter += 1
        
        # Stop Loss order
        sl_order = Order(
            order_id=self.order_counter,
            order_type=OrderType.STOP_LOSS,
            direction=direction,
            price=sl,
            timestamp=timestamp
        )
        self.pending_orders.append(sl_order)
        self.order_counter += 1
        
        logger.info(f"Created 4 orders: Entry1, Entry2, TP, SL")
    
    async def check_orders(self, bar: pd.Series, timestamp: pd.Timestamp):
        """Check if any pending orders should be filled"""
        if self.current_trade is None:
            return
        
        high = bar['high']
        low = bar['low']
        close = bar['close']
        direction = self.current_trade['direction']
        
        # Check if we have any position (at least 1 entry filled)
        has_position = self.current_trade['entry1_filled'] or self.current_trade['entry2_filled']
        
        # Check each pending order
        # Priority: ENTRY orders first, then TP/SL (only if has position)
        for order in self.pending_orders[:]:  # Copy list to allow modification
            if order.status != OrderStatus.PENDING:
                continue
            
            filled = False
            fill_price = None
            
            if direction == 'Long':
                # Long orders
                if order.order_type == OrderType.ENTRY1:
                    # Entry at or below en1 price
                    if low <= order.price:
                        filled = True
                        fill_price = order.price
                
                elif order.order_type == OrderType.ENTRY2:
                    # Entry at or below en2 price
                    if low <= order.price:
                        filled = True
                        fill_price = order.price
                
                elif order.order_type == OrderType.TAKE_PROFIT:
                    # TP only triggers if we have position
                    if has_position and high >= order.price:
                        filled = True
                        fill_price = order.price
                        self.current_trade['tp_hit'] = True
                        logger.info(f"[TP HIT] @ {fill_price:.8f} on {timestamp}")
                        # Cancel all other orders
                        self.cancel_all_orders(except_order=order)
                        # Close trade
                        self.close_trade('TP', fill_price, timestamp)
                
                elif order.order_type == OrderType.STOP_LOSS:
                    # SL only triggers if we have position
                    if has_position and low <= order.price:
                        filled = True
                        fill_price = order.price
                        self.current_trade['sl_hit'] = True
                        logger.info(f"[SL HIT] @ {fill_price:.8f} on {timestamp}")
                        # Cancel all other orders
                        self.cancel_all_orders(except_order=order)
                        # Close trade
                        self.close_trade('SL', fill_price, timestamp)
            
            else:  # Short
                # Short orders
                if order.order_type == OrderType.ENTRY1:
                    # Entry at or above en1 price
                    if high >= order.price:
                        filled = True
                        fill_price = order.price
                
                elif order.order_type == OrderType.ENTRY2:
                    # Entry at or above en2 price
                    if high >= order.price:
                        filled = True
                        fill_price = order.price
                
                elif order.order_type == OrderType.TAKE_PROFIT:
                    # TP only triggers if we have position
                    if has_position and low <= order.price:
                        filled = True
                        fill_price = order.price
                        self.current_trade['tp_hit'] = True
                        logger.info(f"[TP HIT] @ {fill_price:.8f} on {timestamp}")
                        # Cancel all other orders
                        self.cancel_all_orders(except_order=order)
                        # Close trade
                        self.close_trade('TP', fill_price, timestamp)
                
                elif order.order_type == OrderType.STOP_LOSS:
                    # SL only triggers if we have position
                    if has_position and high >= order.price:
                        filled = True
                        fill_price = order.price
                        self.current_trade['sl_hit'] = True
                        logger.info(f"[SL HIT] @ {fill_price:.8f} on {timestamp}")
                        # Cancel all other orders
                        self.cancel_all_orders(except_order=order)
                        # Close trade
                        self.close_trade('SL', fill_price, timestamp)
            
            # Mark order as filled
            if filled:
                order.status = OrderStatus.FILLED
                order.filled_price = fill_price
                order.filled_timestamp = timestamp
                
                if order.order_type in [OrderType.ENTRY1, OrderType.ENTRY2]:
                    if order.order_type == OrderType.ENTRY1:
                        self.current_trade['entry1_filled'] = True
                        self.current_trade['entry1_timestamp'] = timestamp
                        has_position = True  # Update position flag
                        logger.info(f"[ENTRY 1 FILLED] @ {fill_price:.8f} on {timestamp}")
                    else:
                        self.current_trade['entry2_filled'] = True
                        self.current_trade['entry2_timestamp'] = timestamp
                        has_position = True  # Update position flag
                        logger.info(f"[ENTRY 2 FILLED] @ {fill_price:.8f} on {timestamp}")
    
    def cancel_all_orders(self, except_order: Optional[Order] = None):
        """Cancel all pending orders"""
        for order in self.pending_orders:
            if order.status == OrderStatus.PENDING:
                if except_order is None or order.order_id != except_order.order_id:
                    order.status = OrderStatus.CANCELLED
    
    def close_trade(self, reason: str, exit_price: float, exit_timestamp: pd.Timestamp):
        """Close current trade and record result"""
        if self.current_trade is None:
            return
        
        trade = self.current_trade
        direction = trade['direction']
        
        # Calculate position-weighted entry price and total P&L
        entry1_filled = trade['entry1_filled']
        entry2_filled = trade['entry2_filled']
        
        # Validate: Must have at least one entry filled
        if not entry1_filled and not entry2_filled:
            logger.error("❌ CRITICAL ERROR: Trade closed but NO entries were filled!")
            logger.error(f"   Direction: {direction}, Exit: {exit_price}, Reason: {reason}")
            logger.error("   This should NEVER happen in real trading!")
            self.current_trade = None
            self.pending_orders = []
            return
        
        # Calculate weighted entry price based on position sizes
        # Each entry = 50% of total position
        total_position = 0
        weighted_entry = 0
        entry_timestamps = []
        
        if entry1_filled:
            entry1_size = 0.5  # 50% position
            weighted_entry += trade['en1'] * entry1_size
            total_position += entry1_size
            entry_timestamps.append(trade.get('entry1_timestamp'))
            logger.info(f"   Entry 1: {trade['en1']:.8f} (50% position)")
        
        if entry2_filled:
            entry2_size = 0.5  # 50% position
            weighted_entry += trade['en2'] * entry2_size
            total_position += entry2_size
            entry_timestamps.append(trade.get('entry2_timestamp'))
            logger.info(f"   Entry 2: {trade['en2']:.8f} (50% position)")
        
        avg_entry = weighted_entry / total_position
        first_entry_time = min([t for t in entry_timestamps if t is not None])
        
        logger.info(f"   Total Position: {total_position*100:.0f}%")
        logger.info(f"   Weighted Avg Entry: {avg_entry:.8f}")
        
        # Calculate P&L percentage based on weighted average entry
        if direction == 'Long':
            pnl_pct = ((exit_price - avg_entry) / avg_entry) * 100
        else:  # Short
            pnl_pct = ((avg_entry - exit_price) / avg_entry) * 100
        
        # Adjust P&L by actual position size (if only 1 entry filled, P&L is halved)
        actual_pnl_pct = pnl_pct * total_position
        
        pnl_abs = (exit_price - avg_entry) * total_position if direction == 'Long' else (avg_entry - exit_price) * total_position
        
        logger.info(f"   Full Position P&L: {pnl_pct:+.2f}%")
        logger.info(f"   Actual P&L ({total_position*100:.0f}% position): {actual_pnl_pct:+.2f}%")
        
        # Create trade record
        trade_record = Trade(
            trade_id=self.trade_counter,
            signal_timestamp=trade['signal_timestamp'],
            direction=direction,
            pattern_group=trade['pattern_group'],
            
            entry1_price=trade['en1'],
            entry1_filled=trade['entry1_filled'],
            entry1_timestamp=trade.get('entry1_timestamp'),
            
            entry2_price=trade['en2'],
            entry2_filled=trade['entry2_filled'],
            entry2_timestamp=trade.get('entry2_timestamp'),
            
            tp_price=trade['tp'],
            sl_price=trade['sl'],
            exit_price=exit_price,
            exit_timestamp=exit_timestamp,
            exit_reason=reason,
            
            pnl_percentage=actual_pnl_pct,  # Use position-adjusted P&L
            pnl_absolute=pnl_abs,
            
            pivot5=trade['pivot5'],
            pivot6=trade['pivot6'],
            pivot8=trade['pivot8'],
            choch_price=trade['choch_price']
        )
        
        self.completed_trades.append(trade_record)
        self.trade_counter += 1
        
        logger.info(f"[TRADE CLOSED] {reason} | P&L: {actual_pnl_pct:+.2f}% | Avg Entry: {avg_entry:.8f} | Exit: {exit_price:.8f}")
        
        # Reset current trade
        self.current_trade = None
        self.pending_orders = []
    
    def calculate_results(self, symbol: str, timeframe: str, df: pd.DataFrame) -> BacktestResult:
        """Calculate backtest performance metrics"""
        total_trades = len(self.completed_trades)
        
        if total_trades == 0:
            logger.warning("No completed trades!")
            return BacktestResult(
                symbol=symbol,
                timeframe=timeframe,
                start_date=df.index[0].to_pydatetime(),
                end_date=df.index[-1].to_pydatetime(),
                total_bars=len(df),
                total_signals=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_win_pct=0.0,
                avg_loss_pct=0.0,
                avg_pnl_pct=0.0,
                total_pnl_pct=0.0,
                profit_factor=0.0,
                max_drawdown_pct=0.0,
                trades=[]
            )
        
        # Calculate metrics
        winning_trades = [t for t in self.completed_trades if t.pnl_percentage > 0]
        losing_trades = [t for t in self.completed_trades if t.pnl_percentage <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        avg_win_pct = sum(t.pnl_percentage for t in winning_trades) / win_count if win_count > 0 else 0
        avg_loss_pct = sum(t.pnl_percentage for t in losing_trades) / loss_count if loss_count > 0 else 0
        
        total_pnl_pct = sum(t.pnl_percentage for t in self.completed_trades)
        avg_pnl_pct = total_pnl_pct / total_trades
        
        # Profit factor
        gross_profit = sum(t.pnl_percentage for t in winning_trades)
        gross_loss = abs(sum(t.pnl_percentage for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Max drawdown
        cumulative_pnl = []
        running_pnl = 0
        for trade in self.completed_trades:
            running_pnl += trade.pnl_percentage
            cumulative_pnl.append(running_pnl)
        
        max_drawdown = 0
        peak = cumulative_pnl[0] if cumulative_pnl else 0
        for pnl in cumulative_pnl:
            if pnl > peak:
                peak = pnl
            drawdown = peak - pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            start_date=df.index[0].to_pydatetime(),
            end_date=df.index[-1].to_pydatetime(),
            total_bars=len(df),
            total_signals=total_trades,  # Simplified
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            avg_pnl_pct=avg_pnl_pct,
            total_pnl_pct=total_pnl_pct,
            profit_factor=profit_factor,
            max_drawdown_pct=max_drawdown,
            trades=self.completed_trades
        )
    
    def print_trade_details(self):
        """Print detailed trade information"""
        if len(self.completed_trades) == 0:
            return
        
        logger.info("\n" + "="*80)
        logger.info("TRADE DETAILS")
        logger.info("="*80)
        
        for trade in self.completed_trades:
            logger.info(f"\nTrade #{trade.trade_id} - {trade.direction} ({trade.pattern_group})")
            logger.info(f"  Signal: {trade.signal_timestamp}")
            logger.info(f"  Entry 1: {trade.entry1_price:.8f} {'✓' if trade.entry1_filled else '✗'}")
            if trade.entry1_filled:
                logger.info(f"    Filled: {trade.entry1_timestamp}")
            logger.info(f"  Entry 2: {trade.entry2_price:.8f} {'✓' if trade.entry2_filled else '✗'}")
            if trade.entry2_filled:
                logger.info(f"    Filled: {trade.entry2_timestamp}")
            logger.info(f"  Exit: {trade.exit_price:.8f} ({trade.exit_reason})")
            logger.info(f"    Time: {trade.exit_timestamp}")
            logger.info(f"  P&L: {trade.pnl_percentage:+.2f}%")
            logger.info(f"  Pivots: P5={trade.pivot5:.8f} P6={trade.pivot6:.8f} P8={trade.pivot8:.8f}")
        
        logger.info("="*80 + "\n")


async def main():
    """Main entry point for backtest"""
    logger.info("="*80)
    logger.info("CHoCH BACKTEST BOT - FULL MARKET SCAN")
    logger.info("="*80 + "\n")
    
    # Configuration - FULL MARKET SCAN
    TIMEFRAMES = ["30m","1h"]  # Timeframes to test
    LIMIT = 1000        # Number of historical bars per symbol
    
    # Initialize components
    base_fetcher = BinanceFetcher(
        api_key=config.BINANCE_API_KEY,
        secret=config.BINANCE_SECRET
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
    
    # Create backtest engine
    engine = BacktestEngine(detector, fetcher)
    
    try:
        # Fetch all USDT pairs
        logger.info("Fetching all USDT futures pairs...")
        all_symbols = await fetcher.get_all_usdt_pairs(
            min_volume_24h=config.MIN_VOLUME_24H,
            quote=config.QUOTE_CURRENCY,
            max_pairs=0  # No limit - get ALL pairs
        )
        logger.info(f"Found {len(all_symbols)} USDT pairs\n")
        
        # Store all results
        all_results = []
        total_tests = len(all_symbols) * len(TIMEFRAMES)
        completed_tests = 0
        
        # Run backtest for each symbol and timeframe
        for symbol in all_symbols:
            for timeframe in TIMEFRAMES:
                completed_tests += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"[{completed_tests}/{total_tests}] Testing {symbol} {timeframe}")
                logger.info(f"{'='*80}")
                
                try:
                    # Reset detector state for new symbol/timeframe
                    key = f"{symbol}_{timeframe}"
                    if key in detector.states:
                        detector.states[key].reset()
                    
                    # Run backtest
                    result = await engine.run_backtest(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=LIMIT
                    )
                    
                    if result and result.total_trades > 0:
                        all_results.append(result)
                        logger.info(f"✓ {symbol} {timeframe}: {result.total_trades} trades, {result.win_rate:.1%} win rate, {result.total_pnl_pct:+.2f}% total P&L")
                    else:
                        logger.info(f"✗ {symbol} {timeframe}: No trades")
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)
                
                except Exception as e:
                    logger.error(f"Error testing {symbol} {timeframe}: {e}")
                    await asyncio.sleep(1)
        
        # Generate summary report
        logger.info("\n" + "="*80)
        logger.info("FULL MARKET BACKTEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Symbols Tested: {len(all_symbols)}")
        logger.info(f"Total Timeframes: {len(TIMEFRAMES)}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Tests with Trades: {len(all_results)}")
        logger.info("-"*80)
        
        if len(all_results) > 0:
            # Aggregate statistics
            total_trades = sum(r.total_trades for r in all_results)
            total_wins = sum(r.winning_trades for r in all_results)
            total_losses = sum(r.losing_trades for r in all_results)
            overall_win_rate = total_wins / total_trades if total_trades > 0 else 0
            
            avg_win_pct = sum(r.avg_win_pct * r.winning_trades for r in all_results) / total_wins if total_wins > 0 else 0
            avg_loss_pct = sum(r.avg_loss_pct * r.losing_trades for r in all_results) / total_losses if total_losses > 0 else 0
            
            total_pnl = sum(r.total_pnl_pct for r in all_results)
            
            logger.info(f"Total Trades: {total_trades}")
            logger.info(f"Winning Trades: {total_wins}")
            logger.info(f"Losing Trades: {total_losses}")
            logger.info(f"Overall Win Rate: {overall_win_rate:.2%}")
            logger.info(f"Average Win: {avg_win_pct:+.2f}%")
            logger.info(f"Average Loss: {avg_loss_pct:+.2f}%")
            logger.info(f"Total P&L (sum): {total_pnl:+.2f}%")
            logger.info("-"*80)
            
            # Top performers
            sorted_results = sorted(all_results, key=lambda r: r.total_pnl_pct, reverse=True)
            logger.info("\nTOP 10 PERFORMERS:")
            for i, r in enumerate(sorted_results[:10], 1):
                logger.info(f"{i}. {r.symbol} {r.timeframe}: {r.total_trades} trades, {r.win_rate:.1%} WR, {r.total_pnl_pct:+.2f}% P&L")
            
            # Bottom performers
            logger.info("\nBOTTOM 10 PERFORMERS:")
            for i, r in enumerate(sorted_results[-10:], 1):
                logger.info(f"{i}. {r.symbol} {r.timeframe}: {r.total_trades} trades, {r.win_rate:.1%} WR, {r.total_pnl_pct:+.2f}% P&L")
            
            # Export consolidated results
            all_trades = []
            for result in all_results:
                for trade in result.trades:
                    all_trades.append({
                        'symbol': result.symbol,
                        'timeframe': result.timeframe,
                        'trade_id': trade.trade_id,
                        'signal_time': trade.signal_timestamp,
                        'direction': trade.direction,
                        'pattern_group': trade.pattern_group,
                        'entry1_price': trade.entry1_price,
                        'entry1_filled': trade.entry1_filled,
                        'entry2_price': trade.entry2_price,
                        'entry2_filled': trade.entry2_filled,
                        'exit_price': trade.exit_price,
                        'exit_time': trade.exit_timestamp,
                        'exit_reason': trade.exit_reason,
                        'pnl_pct': trade.pnl_percentage,
                        'tp_price': trade.tp_price,
                        'sl_price': trade.sl_price
                    })
            
            if len(all_trades) > 0:
                trades_df = pd.DataFrame(all_trades)
                filename = f"backtest_FULL_MARKET_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                trades_df.to_csv(filename, index=False)
                logger.info(f"\n[EXPORT] All trades saved to: {filename}")
                
                # Export summary by symbol
                summary_data = []
                for result in sorted_results:
                    summary_data.append({
                        'symbol': result.symbol,
                        'timeframe': result.timeframe,
                        'total_trades': result.total_trades,
                        'winning_trades': result.winning_trades,
                        'losing_trades': result.losing_trades,
                        'win_rate': result.win_rate,
                        'avg_win_pct': result.avg_win_pct,
                        'avg_loss_pct': result.avg_loss_pct,
                        'total_pnl_pct': result.total_pnl_pct,
                        'profit_factor': result.profit_factor,
                        'max_drawdown_pct': result.max_drawdown_pct
                    })
                
                summary_df = pd.DataFrame(summary_data)
                summary_filename = f"backtest_SUMMARY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                summary_df.to_csv(summary_filename, index=False)
                logger.info(f"[EXPORT] Summary saved to: {summary_filename}")
        else:
            logger.info("No trades found in any symbol/timeframe combination")
        
        logger.info("="*80 + "\n")
    
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
    
    finally:
        await fetcher.close()
        logger.info("\n[EXIT] Full market backtest completed")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n[STOP] Backtest interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
