"""
Position Manager - Manages trading positions and orders
Handles entry, TP, SL orders with loose coupling
"""
import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from trading.exchange_adapter import (
    ExchangeAdapter, OrderSide, OrderType, PositionSide, OrderResult
)

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """Trade status enumeration"""
    PENDING = "pending"  # Orders created, waiting for entry
    ENTRY1_FILLED = "entry1_filled"  # Entry 1 filled
    ENTRY2_FILLED = "entry2_filled"  # Entry 2 filled
    BOTH_FILLED = "both_filled"  # Both entries filled
    CLOSED = "closed"  # Position closed (TP/SL hit)
    CANCELLED = "cancelled"  # Trade cancelled


@dataclass
class ManagedOrder:
    """Managed order with tracking"""
    order_id: Optional[str]
    symbol: str
    side: str  # 'BUY' or 'SELL'
    order_type: str  # 'LIMIT', 'STOP_MARKET', 'TAKE_PROFIT_MARKET'
    quantity: float
    price: float
    position_side: str  # 'LONG' or 'SHORT'
    purpose: str  # 'ENTRY1', 'ENTRY2', 'TP', 'SL'
    status: str = "pending"  # 'pending', 'filled', 'cancelled'
    filled_price: Optional[float] = None
    filled_time: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class ManagedPosition:
    """Managed trading position"""
    position_id: str
    symbol: str
    direction: str  # 'Long' or 'Short'
    timeframe: str
    pattern_group: str  # 'G1', 'G2', 'G3'
    
    # Signal info
    signal_timestamp: datetime
    choch_price: float
    
    # Entry levels
    entry1_price: float
    entry2_price: float
    
    # Exit levels
    tp_price: float
    sl_price: float
    
    # Pivot references
    pivot5: float
    pivot6: float
    pivot8: float
    
    # Position state
    status: TradeStatus = TradeStatus.PENDING
    entry1_quantity: float = 0.0
    entry2_quantity: float = 0.0
    total_quantity: float = 0.0
    avg_entry_price: float = 0.0
    
    # Orders
    orders: List[ManagedOrder] = field(default_factory=list)
    
    # P&L tracking
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    
    def get_order_by_purpose(self, purpose: str) -> Optional[ManagedOrder]:
        """Get order by purpose (ENTRY1, ENTRY2, TP, SL)"""
        for order in self.orders:
            if order.purpose == purpose:
                return order
        return None
    
    def has_open_position(self) -> bool:
        """Check if position has any filled entries"""
        return self.entry1_quantity > 0 or self.entry2_quantity > 0
    
    def update_avg_entry(self):
        """Update average entry price based on filled entries"""
        if self.total_quantity > 0:
            total_cost = (self.entry1_price * self.entry1_quantity + 
                         self.entry2_price * self.entry2_quantity)
            self.avg_entry_price = total_cost / self.total_quantity
        else:
            self.avg_entry_price = 0.0


class PositionManager:
    """Manages trading positions and orders"""
    
    def __init__(self, exchange: ExchangeAdapter, enable_trading: bool = False):
        """
        Initialize position manager
        
        Args:
            exchange: Exchange adapter
            enable_trading: If False, only simulate (no real orders)
        """
        self.exchange = exchange
        self.enable_trading = enable_trading
        
        # Fixed position parameters (simplified - no risk manager)
        self.position_size = 100.0  # $100 USDT total position
        self.leverage = 20  # 20x leverage
        self.margin = 5.0  # $5 USDT margin required
        
        # Active positions by symbol_timeframe key
        self.positions: Dict[str, ManagedPosition] = {}
        
        # Position counter
        self.position_counter = 0
        
        logger.info(f"Position Manager initialized:")
        logger.info(f"  Position Size: ${self.position_size} USDT (fixed)")
        logger.info(f"  Leverage: {self.leverage}x (fixed)")
        logger.info(f"  Margin Required: ${self.margin} USDT")
        logger.info(f"  Trading: {'ENABLED' if enable_trading else 'DISABLED (Simulation)'}")
    
    async def create_position_from_signal(self, signal) -> Optional[ManagedPosition]:
        """
        Create position from Signal object (simplified API)
        
        Args:
            signal: Signal object from signal_bus
        
        Returns:
            ManagedPosition if successful, None otherwise
        """
        return await self.create_position(
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            direction=signal.direction,
            pattern_group=signal.pattern_group,
            signal_timestamp=signal.timestamp,
            entry1_price=signal.entry1_price,
            entry2_price=signal.entry2_price,
            tp_price=signal.tp_price,
            sl_price=signal.sl_price,
            pivot5=signal.pivot5,
            pivot6=signal.pivot6,
            pivot8=signal.pivot8,
            choch_price=signal.choch_price
        )
    
    async def create_position(self, symbol: str, timeframe: str, direction: str,
                            pattern_group: str, signal_timestamp: datetime,
                            entry1_price: float, entry2_price: float,
                            tp_price: float, sl_price: float,
                            pivot5: float, pivot6: float, pivot8: float,
                            choch_price: float) -> Optional[ManagedPosition]:
        """
        Create new trading position with entry/TP/SL orders
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe
            direction: 'Long' or 'Short'
            pattern_group: Pattern group (G1, G2, G3)
            signal_timestamp: CHoCH signal timestamp
            entry1_price: Entry 1 price (conservative)
            entry2_price: Entry 2 price (aggressive)
            tp_price: Take profit price
            sl_price: Stop loss price
            pivot5-8: Pivot prices for reference
            choch_price: CHoCH candle close price
        
        Returns:
            ManagedPosition if successful, None otherwise
        """
        key = f"{symbol}_{timeframe}"
        
        # Check if position already exists
        if key in self.positions:
            logger.warning(f"Position already exists for {key} - Force closing old position")
            await self.close_position(key, "FORCED_CLOSE_NEW_SIGNAL", choch_price)
        
        # Create position object
        position = ManagedPosition(
            position_id=f"POS_{self.position_counter}",
            symbol=symbol,
            direction=direction,
            timeframe=timeframe,
            pattern_group=pattern_group,
            signal_timestamp=signal_timestamp,
            choch_price=choch_price,
            entry1_price=entry1_price,
            entry2_price=entry2_price,
            tp_price=tp_price,
            sl_price=sl_price,
            pivot5=pivot5,
            pivot6=pivot6,
            pivot8=pivot8
        )
        
        self.position_counter += 1
        
        # Calculate position sizes (50% each entry)
        # Total position = $100, split into 2 entries of $50 each
        # With 20x leverage: $50 * 20 = $1000 notional per entry
        # Convert to coin quantity: notional / price
        entry1_notional = (self.position_size / 2) * self.leverage  # $1000
        entry2_notional = (self.position_size / 2) * self.leverage  # $1000
        
        entry1_quantity = entry1_notional / entry1_price
        entry2_quantity = entry2_notional / entry2_price
        
        logger.info(f"\n{'='*80}")
        logger.info(f"[CREATE POSITION] {symbol} {timeframe} {direction} ({pattern_group})")
        logger.info(f"{'='*80}")
        logger.info(f"  Entry 1: {entry1_price:.8f} (qty: {entry1_quantity:.4f}, notional: ${entry1_notional:.2f})")
        logger.info(f"  Entry 2: {entry2_price:.8f} (qty: {entry2_quantity:.4f}, notional: ${entry2_notional:.2f})")
        logger.info(f"  TP: {tp_price:.8f}")
        logger.info(f"  SL: {sl_price:.8f}")
        logger.info(f"  Total Position: ${self.position_size} (Margin: ${self.margin})")
        logger.info(f"  Leverage: {self.leverage}x")
        
        # Determine order sides and position side
        if direction == 'Long':
            entry_side = OrderSide.BUY
            exit_side = OrderSide.SELL
            position_side = PositionSide.LONG
        else:  # Short
            entry_side = OrderSide.SELL
            exit_side = OrderSide.BUY
            position_side = PositionSide.SHORT
        
        # Set leverage for symbol
        if self.enable_trading:
            await self.exchange.set_leverage(symbol, self.leverage)
        
        # Create all 4 orders at once: 2 entries + 1 TP + 1 SL
        # Exchange will auto-manage: when TP/SL hits, it cancels all other orders
        success = True
        total_quantity = entry1_quantity + entry2_quantity
        
        # 1. Entry 1 order (LIMIT)
        if self.enable_trading:
            result1 = await self.exchange.create_order(
                symbol=symbol,
                side=entry_side,
                order_type=OrderType.LIMIT,
                quantity=entry1_quantity,
                price=entry1_price,
                position_side=position_side
            )
            if not result1.success:
                logger.error(f"Failed to create Entry 1 order: {result1.error}")
                success = False
        else:
            result1 = OrderResult(success=True, order_id="SIMULATED_ENTRY1")
        
        position.orders.append(ManagedOrder(
            order_id=result1.order_id if result1.success else None,
            symbol=symbol,
            side=entry_side.value,
            order_type="LIMIT",
            quantity=entry1_quantity,
            price=entry1_price,
            position_side=position_side.value,
            purpose="ENTRY1",
            status="pending" if result1.success else "failed",
            error=result1.error if not result1.success else None
        ))
        
        # 2. Entry 2 order (LIMIT)
        if self.enable_trading and success:
            result2 = await self.exchange.create_order(
                symbol=symbol,
                side=entry_side,
                order_type=OrderType.LIMIT,
                quantity=entry2_quantity,
                price=entry2_price,
                position_side=position_side
            )
            if not result2.success:
                logger.error(f"Failed to create Entry 2 order: {result2.error}")
                success = False
        else:
            result2 = OrderResult(success=True, order_id="SIMULATED_ENTRY2")
        
        position.orders.append(ManagedOrder(
            order_id=result2.order_id if result2.success else None,
            symbol=symbol,
            side=entry_side.value,
            order_type="LIMIT",
            quantity=entry2_quantity,
            price=entry2_price,
            position_side=position_side.value,
            purpose="ENTRY2",
            status="pending" if result2.success else "failed",
            error=result2.error if not result2.success else None
        ))
        
        # 3. Take Profit order (TAKE_PROFIT_MARKET with closePosition=true)
        # This will automatically close ALL positions when TP hits, regardless of how many entries filled
        if self.enable_trading and success:
            tp_result = await self.exchange.create_order(
                symbol=symbol,
                side=exit_side,
                order_type=OrderType.TAKE_PROFIT_MARKET,
                quantity=0,  # Not used when closePosition=true
                stop_price=tp_price,
                position_side=position_side,
                reduce_only=False,  # Cannot use with closePosition
                close_position=True  # Close all position when triggered
            )
            if not tp_result.success:
                logger.error(f"Failed to create TP order: {tp_result.error}")
                success = False
            else:
                logger.info(f"✓ TP order created @ {tp_price:.8f} (closePosition=true)")
        else:
            tp_result = OrderResult(success=True, order_id="SIMULATED_TP")
        
        position.orders.append(ManagedOrder(
            order_id=tp_result.order_id if tp_result.success else None,
            symbol=symbol,
            side=exit_side.value,
            order_type="TAKE_PROFIT_MARKET",
            quantity=0,  # closePosition=true, no quantity needed
            price=tp_price,
            position_side=position_side.value,
            purpose="TP",
            status="pending" if tp_result.success else "failed",
            error=tp_result.error if not tp_result.success else None
        ))
        
        # 4. Stop Loss order (STOP_MARKET with closePosition=true)
        # This will automatically close ALL positions when SL hits, regardless of how many entries filled
        if self.enable_trading and success:
            sl_result = await self.exchange.create_order(
                symbol=symbol,
                side=exit_side,
                order_type=OrderType.STOP_MARKET,
                quantity=0,  # Not used when closePosition=true
                stop_price=sl_price,
                position_side=position_side,
                reduce_only=False,  # Cannot use with closePosition
                close_position=True  # Close all position when triggered
            )
            if not sl_result.success:
                logger.error(f"Failed to create SL order: {sl_result.error}")
                success = False
            else:
                logger.info(f"✓ SL order created @ {sl_price:.8f} (closePosition=true)")
        else:
            sl_result = OrderResult(success=True, order_id="SIMULATED_SL")
        
        position.orders.append(ManagedOrder(
            order_id=sl_result.order_id if sl_result.success else None,
            symbol=symbol,
            side=exit_side.value,
            order_type="STOP_MARKET",
            quantity=0,  # closePosition=true, no quantity needed
            price=sl_price,
            position_side=position_side.value,
            purpose="SL",
            status="pending" if sl_result.success else "failed",
            error=sl_result.error if not sl_result.success else None
        ))
        
        if success:
            self.positions[key] = position
            logger.info(f"✓ Position created with {len(position.orders)} orders (2 entries + TP + SL)")
            logger.info(f"  Exchange will auto-cancel remaining orders when TP/SL hits")
            return position
        else:
            logger.error(f"✗ Failed to create position")
            # Cancel any created orders (only if trading enabled and not simulated)
            if self.enable_trading:
                for order in position.orders:
                    if order.order_id and order.status == "pending" and not order.order_id.startswith("SIMULATED"):
                        try:
                            await self.exchange.cancel_order(symbol, order.order_id)
                        except Exception as e:
                            logger.error(f"Error cancelling order {order.order_id}: {e}")
            return None
    
    async def update_positions(self):
        """Update all active positions (check order fills, update P&L)"""
        if len(self.positions) == 0:
            return
        
        for key, position in list(self.positions.items()):
            try:
                await self._update_position(position)
            except Exception as e:
                logger.error(f"Error updating position {key}: {e}")
    
    async def _update_position(self, position: ManagedPosition):
        """Update single position"""
        # Check entry orders
        entry1_order = position.get_order_by_purpose("ENTRY1")
        entry2_order = position.get_order_by_purpose("ENTRY2")
        
        # Check if entry orders are filled
        if entry1_order and entry1_order.status == "pending":
            if self.enable_trading:
                order_status = await self.exchange.get_order(position.symbol, entry1_order.order_id)
                if order_status and order_status['status'] == 'closed':
                    entry1_order.status = "filled"
                    entry1_order.filled_price = float(order_status.get('average', entry1_order.price))
                    entry1_order.filled_time = datetime.now()
                    position.entry1_quantity = entry1_order.quantity
                    position.total_quantity += entry1_order.quantity
                    position.update_avg_entry()
                    position.status = TradeStatus.ENTRY1_FILLED
                    logger.info(f"[{position.symbol}] Entry 1 FILLED @ {entry1_order.filled_price:.8f}")
                    # TP/SL already created at position creation, no need to create again
        
        if entry2_order and entry2_order.status == "pending":
            if self.enable_trading:
                order_status = await self.exchange.get_order(position.symbol, entry2_order.order_id)
                if order_status and order_status['status'] == 'closed':
                    entry2_order.status = "filled"
                    entry2_order.filled_price = float(order_status.get('average', entry2_order.price))
                    entry2_order.filled_time = datetime.now()
                    position.entry2_quantity = entry2_order.quantity
                    position.total_quantity += entry2_order.quantity
                    position.update_avg_entry()
                    
                    if position.status == TradeStatus.ENTRY1_FILLED:
                        position.status = TradeStatus.BOTH_FILLED
                    else:
                        position.status = TradeStatus.ENTRY2_FILLED
                    
                    logger.info(f"[{position.symbol}] Entry 2 FILLED @ {entry2_order.filled_price:.8f}")
                    # TP/SL already created at position creation, no need to create again
        
        # Check TP/SL orders
        tp_order = position.get_order_by_purpose("TP")
        sl_order = position.get_order_by_purpose("SL")
        
        # Check if TP hit
        if tp_order and tp_order.status == "pending":
            if self.enable_trading:
                order_status = await self.exchange.get_order(position.symbol, tp_order.order_id)
                if order_status and order_status['status'] == 'closed':
                    tp_order.status = "filled"
                    tp_order.filled_price = float(order_status.get('average', position.tp_price))
                    tp_order.filled_time = datetime.now()
                    logger.info(f"[{position.symbol}] 🎯 TP HIT @ {tp_order.filled_price:.8f}")
                    
                    # Close position and cancel all remaining orders
                    await self.close_position(f"{position.symbol}_{position.timeframe}", 
                                            "TP", tp_order.filled_price)
                    return  # Position closed, no need to check further
        
        # Check if SL hit
        if sl_order and sl_order.status == "pending":
            if self.enable_trading:
                order_status = await self.exchange.get_order(position.symbol, sl_order.order_id)
                if order_status and order_status['status'] == 'closed':
                    sl_order.status = "filled"
                    sl_order.filled_price = float(order_status.get('average', position.sl_price))
                    sl_order.filled_time = datetime.now()
                    logger.info(f"[{position.symbol}] 🛑 SL HIT @ {sl_order.filled_price:.8f}")
                    
                    # Close position and cancel all remaining orders
                    await self.close_position(f"{position.symbol}_{position.timeframe}", 
                                            "SL", sl_order.filled_price)
                    return  # Position closed, no need to check further
        
        position.updated_at = datetime.now()
    
    async def close_position(self, key: str, reason: str, exit_price: float):
        """
        Close position and calculate P&L
        
        Args:
            key: Position key (symbol_timeframe)
            reason: Close reason (TP, SL, FORCED_CLOSE_NEW_SIGNAL)
            exit_price: Exit price
        """
        if key not in self.positions:
            logger.warning(f"Position {key} not found")
            return
        
        position = self.positions[key]
        
        # Cancel all pending orders (entry orders not filled yet, and opposite exit order)
        cancelled_orders = []
        for order in position.orders:
            if order.status == "pending" and order.order_id:
                # Only cancel real orders, not simulated ones
                if self.enable_trading and not order.order_id.startswith("SIMULATED"):
                    try:
                        success = await self.exchange.cancel_order(position.symbol, order.order_id)
                        if success:
                            cancelled_orders.append(f"{order.purpose}@{order.price:.8f}")
                    except Exception as e:
                        logger.error(f"Error cancelling order {order.order_id}: {e}")
                else:
                    # Simulated orders - just mark as cancelled
                    cancelled_orders.append(f"{order.purpose}@{order.price:.8f}")
                order.status = "cancelled"
        
        if cancelled_orders:
            logger.info(f"  ✓ Cancelled orders: {', '.join(cancelled_orders)}")
        
        # Calculate P&L
        if position.has_open_position():
            if position.direction == 'Long':
                pnl_pct = ((exit_price - position.avg_entry_price) / position.avg_entry_price) * 100
            else:
                pnl_pct = ((position.avg_entry_price - exit_price) / position.avg_entry_price) * 100
            
            # Calculate P&L in USDT
            # P&L = (exit_price - entry_price) * quantity for Long
            # P&L = (entry_price - exit_price) * quantity for Short
            if position.direction == 'Long':
                pnl_usdt = (exit_price - position.avg_entry_price) * position.total_quantity
            else:
                pnl_usdt = (position.avg_entry_price - exit_price) * position.total_quantity
            
            position.realized_pnl = pnl_usdt
            
            logger.info(f"\n{'='*80}")
            logger.info(f"[POSITION CLOSED] {position.symbol} {position.timeframe} - {reason}")
            logger.info(f"{'='*80}")
            logger.info(f"  Direction: {position.direction}")
            logger.info(f"  Avg Entry: {position.avg_entry_price:.8f}")
            logger.info(f"  Exit: {exit_price:.8f}")
            logger.info(f"  Quantity: {position.total_quantity:.4f}")
            logger.info(f"  P&L: {pnl_pct:+.2f}% (${pnl_usdt:+.2f} USDT)")
            logger.info(f"  Entry1: {'✓' if position.entry1_quantity > 0 else '✗'}")
            logger.info(f"  Entry2: {'✓' if position.entry2_quantity > 0 else '✗'}")
            logger.info(f"{'='*80}\n")
        
        position.status = TradeStatus.CLOSED
        position.closed_at = datetime.now()
        
        # Remove from active positions
        del self.positions[key]
    
    def get_position(self, key: str) -> Optional[ManagedPosition]:
        """Get position by key"""
        return self.positions.get(key)
    
    def get_all_positions(self) -> List[ManagedPosition]:
        """Get all active positions"""
        return list(self.positions.values())
    
    def get_position_count(self) -> int:
        """Get number of active positions"""
        return len(self.positions)
