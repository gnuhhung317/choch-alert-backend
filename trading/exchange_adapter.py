"""
Exchange Adapter - Loose coupling interface for exchange operations
Supports both demo and live trading
"""
import ccxt.async_support as ccxt
import logging
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    TAKE_PROFIT_MARKET = "take_profit_market"


class PositionSide(Enum):
    """Position side for hedge mode"""
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"  # One-way mode


@dataclass
class OrderResult:
    """Order execution result"""
    success: bool
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[float] = None
    status: Optional[str] = None
    filled: float = 0.0
    remaining: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


@dataclass
class Position:
    """Position information"""
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    leverage: int
    liquidation_price: Optional[float] = None
    margin: Optional[float] = None


class ExchangeAdapter(ABC):
    """Abstract base class for exchange operations"""
    
    @abstractmethod
    async def initialize(self):
        """Initialize exchange connection"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close exchange connection"""
        pass
    
    @abstractmethod
    async def create_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                          quantity: float, price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          position_side: Optional[PositionSide] = None,
                          reduce_only: bool = False) -> OrderResult:
        """Create an order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> Optional[Dict]:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        pass
    
    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict:
        """Get account balance"""
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for symbol"""
        pass
    
    @abstractmethod
    async def set_margin_type(self, symbol: str, margin_type: str) -> bool:
        """Set margin type (CROSSED/ISOLATED)"""
        pass


class BinanceFuturesAdapter(ExchangeAdapter):
    """Binance Futures exchange adapter with demo trading support"""
    
    def __init__(self, api_key: str, secret: str, demo_mode: bool = True):
        """
        Initialize Binance Futures adapter
        
        Args:
            api_key: API key
            secret: API secret
            demo_mode: If True, use demo trading (testnet)
        """
        self.api_key = api_key
        self.secret = secret
        self.demo_mode = demo_mode
        self.exchange: Optional[ccxt.binanceusdm] = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize exchange connection"""
        try:
            self.exchange = ccxt.binanceusdm({
                'apiKey': self.api_key,
                'secret': self.secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'hedgeMode': True,  # Enable hedge mode for LONG/SHORT
                }
            })
            
            if self.demo_mode:
                # Enable demo trading (testnet)
                self.exchange.enable_demo_trading(True)
                logger.info("🧪 Demo trading mode enabled (Binance Testnet)")
            else:
                logger.warning("⚠️  LIVE TRADING MODE - Real money at risk!")
            
            # Load markets (not async in ccxt v4)
            markets = await self.exchange.load_markets()
            
            # Set position mode to Hedge/Dual mode (support both LONG and SHORT simultaneously)
            try:
                await self.exchange.set_position_mode(True)  # True = Hedge mode (dualSidePosition)
                logger.info("✓ Position mode set to HEDGE (Dual-side)")
            except Exception as e:
                logger.warning(f"Could not set position mode (may already be set): {e}")
            
            # Test connection
            balance = await self.exchange.fetch_balance()
            logger.info(f"✓ Connected to Binance Futures ({'DEMO' if self.demo_mode else 'LIVE'})")
            logger.info(f"  USDT Balance: {balance.get('USDT', {}).get('free', 0):.2f}")
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()
            self.initialized = False
            logger.info("Exchange connection closed")
    
    async def create_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                          quantity: float, price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          position_side: Optional[PositionSide] = None,
                          reduce_only: bool = False,
                          close_position: bool = False) -> OrderResult:
        """
        Create an order on Binance Futures
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET
            quantity: Order quantity (not used if close_position=True)
            price: Limit price (for LIMIT orders)
            stop_price: Stop price (for STOP_MARKET/TAKE_PROFIT_MARKET)
            position_side: LONG or SHORT (for hedge mode)
            reduce_only: If True, order will only reduce position
            close_position: If True, close all position when triggered (for TP/SL)
        
        Returns:
            OrderResult with execution details
        """
        if not self.initialized:
            return OrderResult(success=False, error="Exchange not initialized")
        
        try:
            params = {}
            
            # Set position side for hedge mode
            if position_side:
                params['positionSide'] = position_side.value
            
            # Set reduce only flag (cannot use with closePosition)
            if reduce_only and not close_position:
                params['reduceOnly'] = True
            
            # Set close position flag (for TP/SL to close all)
            if close_position:
                params['closePosition'] = 'true'  # Must be string 'true', not boolean
                # When closePosition=true, quantity is not needed
                quantity = 0
            
            # Create order based on type
            if order_type == OrderType.MARKET:
                order = await self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=side.value,
                    amount=quantity,
                    params=params
                )
            
            elif order_type == OrderType.LIMIT:
                if price is None:
                    return OrderResult(success=False, error="Price required for LIMIT order")
                order = await self.exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side=side.value,
                    amount=quantity,
                    price=price,
                    params=params
                )
            
            elif order_type == OrderType.STOP_MARKET:
                if stop_price is None:
                    return OrderResult(success=False, error="Stop price required for STOP_MARKET")
                params['stopPrice'] = stop_price
                
                # For STOP_MARKET with closePosition, don't send quantity
                if close_position:
                    order = await self.exchange.create_order(
                        symbol=symbol,
                        type='STOP_MARKET',
                        side=side.value,
                        amount=None,  # No amount when closePosition=true
                        params=params
                    )
                else:
                    order = await self.exchange.create_order(
                        symbol=symbol,
                        type='STOP_MARKET',
                        side=side.value,
                        amount=quantity,
                        params=params
                    )
            
            elif order_type == OrderType.TAKE_PROFIT_MARKET:
                if stop_price is None:
                    return OrderResult(success=False, error="Stop price required for TAKE_PROFIT_MARKET")
                params['stopPrice'] = stop_price
                
                # For TAKE_PROFIT_MARKET with closePosition, don't send quantity
                if close_position:
                    order = await self.exchange.create_order(
                        symbol=symbol,
                        type='TAKE_PROFIT_MARKET',
                        side=side.value,
                        amount=None,  # No amount when closePosition=true
                        params=params
                    )
                else:
                    order = await self.exchange.create_order(
                        symbol=symbol,
                        type='TAKE_PROFIT_MARKET',
                        side=side.value,
                        amount=quantity,
                        params=params
                    )
            
            else:
                return OrderResult(success=False, error=f"Unsupported order type: {order_type}")
            
            logger.info(f"✓ Order created: {symbol} {side.value} {quantity} @ {price or stop_price or 'MARKET'}")
            
            return OrderResult(
                success=True,
                order_id=order['id'],
                symbol=order['symbol'],
                side=order['side'],
                order_type=order['type'],
                price=order.get('price'),
                quantity=order['amount'],
                status=order['status'],
                filled=order.get('filled', 0),
                remaining=order.get('remaining', 0),
                raw_response=order
            )
            
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return OrderResult(success=False, error=str(e))
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        if not self.initialized:
            return False
        
        try:
            await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"✓ Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def get_order(self, symbol: str, order_id: str) -> Optional[Dict]:
        """Get order status"""
        if not self.initialized:
            return None
        
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        if not self.initialized:
            return []
        
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current positions"""
        if not self.initialized:
            return []
        
        try:
            # Fetch positions from Binance
            raw_positions = await self.exchange.fetch_positions(symbols=[symbol] if symbol else None)
            
            positions = []
            for pos in raw_positions:
                # Only include positions with size > 0
                size = abs(float(pos.get('contracts', 0)))
                if size > 0:
                    positions.append(Position(
                        symbol=pos['symbol'],
                        side=pos['side'],
                        size=size,
                        entry_price=float(pos.get('entryPrice', 0)),
                        mark_price=float(pos.get('markPrice', 0)),
                        unrealized_pnl=float(pos.get('unrealizedPnl', 0)),
                        leverage=int(pos.get('leverage', 1)),
                        liquidation_price=float(pos.get('liquidationPrice', 0)) if pos.get('liquidationPrice') else None,
                        margin=float(pos.get('initialMargin', 0)) if pos.get('initialMargin') else None
                    ))
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    async def get_balance(self) -> Dict:
        """Get account balance"""
        if not self.initialized:
            return {}
        
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return {}
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for symbol"""
        if not self.initialized:
            return False
        
        try:
            await self.exchange.set_leverage(leverage, symbol)
            logger.info(f"✓ Leverage set to {leverage}x for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            return False
    
    async def set_margin_type(self, symbol: str, margin_type: str) -> bool:
        """Set margin type (CROSSED/ISOLATED)"""
        if not self.initialized:
            return False
        
        try:
            await self.exchange.set_margin_mode(margin_type, symbol)
            logger.info(f"✓ Margin type set to {margin_type} for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to set margin type: {e}")
            return False
