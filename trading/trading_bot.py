"""
Trading Bot - Executes trades based on CHoCH signals
Subscribes to SignalBus and creates positions via PositionManager
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from trading.signal_bus import Signal, get_signal_bus
from trading.position_manager import PositionManager
from trading.exchange_adapter import ExchangeAdapter

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Trading bot that executes CHoCH signals
    Loose coupling via SignalBus subscription
    """
    
    def __init__(self, position_manager: PositionManager, 
                 enable_trading: bool = False):
        """
        Initialize trading bot
        
        Args:
            position_manager: Position manager instance
            enable_trading: If False, only simulate (no real orders)
        """
        self.position_manager = position_manager
        self.enable_trading = enable_trading
        
        # Statistics
        self.signals_received = 0
        self.trades_created = 0
        self.trades_rejected = 0
        
        # Get signal bus
        self.signal_bus = get_signal_bus()
        
        logger.info("="*80)
        logger.info("TRADING BOT INITIALIZED")
        logger.info("="*80)
        logger.info(f"  Trading Mode: {'ENABLED ⚠️' if enable_trading else 'SIMULATION 🧪'}")
        logger.info(f"  Position Size: ${position_manager.position_size}")
        logger.info(f"  Leverage: {position_manager.leverage}x")
        logger.info(f"  Margin: ${position_manager.margin}")
        logger.info("="*80 + "\n")
    
    def start(self):
        """Start trading bot by subscribing to signal bus"""
        self.signal_bus.subscribe(self.on_signal)
        logger.info("✓ Trading bot subscribed to signal bus")
        logger.info(f"  Total subscribers: {self.signal_bus.get_subscriber_count()}")
    
    def stop(self):
        """Stop trading bot by unsubscribing from signal bus"""
        self.signal_bus.unsubscribe(self.on_signal)
        logger.info("✓ Trading bot unsubscribed from signal bus")
    
    async def on_signal(self, signal: Signal):
        """
        Handle incoming CHoCH signal
        
        Args:
            signal: Signal from CHoCH detector
        """
        self.signals_received += 1
        
        logger.info(f"\n{'='*80}")
        logger.info(f"[TRADING BOT] Signal #{self.signals_received} received")
        logger.info(f"{'='*80}")
        logger.info(f"  Symbol: {signal.symbol}")
        logger.info(f"  Timeframe: {signal.timeframe}")
        logger.info(f"  Direction: {signal.direction}")
        logger.info(f"  Pattern: {signal.pattern_group}")
        logger.info(f"  CHoCH Price: {signal.choch_price:.8f}")
        logger.info(f"  Entry 1: {signal.entry1_price:.8f} (conservative)")
        logger.info(f"  Entry 2: {signal.entry2_price:.8f} (aggressive)")
        logger.info(f"  TP: {signal.tp_price:.8f}")
        logger.info(f"  SL: {signal.sl_price:.8f}")
        
        # Validate signal
        if not self._validate_signal(signal):
            self.trades_rejected += 1
            logger.warning(f"✗ Signal rejected (total rejected: {self.trades_rejected})")
            return
        
        # Create position via PositionManager
        try:
            position = await self.position_manager.create_position_from_signal(signal)
            
            if position:
                self.trades_created += 1
                logger.info(f"✓ Position created: {position.position_id}")
                logger.info(f"  Total trades: {self.trades_created} | Rejected: {self.trades_rejected}")
            else:
                self.trades_rejected += 1
                logger.error(f"✗ Failed to create position")
        
        except Exception as e:
            self.trades_rejected += 1
            logger.error(f"✗ Error creating position: {e}", exc_info=True)
    
    def _validate_signal(self, signal: Signal) -> bool:
        """
        Validate signal before creating position
        
        Args:
            signal: Signal to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Basic validation
        if not signal.symbol or not signal.timeframe:
            logger.error("Invalid signal: missing symbol or timeframe")
            return False
        
        if signal.direction not in ['Long', 'Short']:
            logger.error(f"Invalid direction: {signal.direction}")
            return False
        
        # Price validation
        if signal.entry1_price <= 0 or signal.entry2_price <= 0:
            logger.error("Invalid entry prices")
            return False
        
        if signal.tp_price <= 0 or signal.sl_price <= 0:
            logger.error("Invalid TP/SL prices")
            return False
        
        # Risk validation (TP should be better than SL)
        if signal.direction == 'Long':
            if signal.tp_price <= signal.entry1_price:
                logger.error(f"Invalid LONG: TP ({signal.tp_price}) <= Entry ({signal.entry1_price})")
                return False
            if signal.sl_price >= signal.entry2_price:
                logger.error(f"Invalid LONG: SL ({signal.sl_price}) >= Entry ({signal.entry2_price})")
                return False
        else:  # Short
            if signal.tp_price >= signal.entry1_price:
                logger.error(f"Invalid SHORT: TP ({signal.tp_price}) >= Entry ({signal.entry1_price})")
                return False
            if signal.sl_price <= signal.entry2_price:
                logger.error(f"Invalid SHORT: SL ({signal.sl_price}) <= Entry ({signal.entry2_price})")
                return False
        
        logger.debug("Signal validation passed")
        return True
    
    async def run_monitoring_loop(self, update_interval: float = 5.0):
        """
        Run monitoring loop to update positions
        
        Args:
            update_interval: Interval in seconds between position updates
        """
        logger.info(f"Starting position monitoring loop (interval: {update_interval}s)")
        
        try:
            while True:
                # Update all positions
                await self.position_manager.update_positions()
                
                # Log statistics
                position_count = self.position_manager.get_position_count()
                if position_count > 0:
                    logger.info(f"[MONITOR] Active positions: {position_count}")
                
                # Sleep
                await asyncio.sleep(update_interval)
        
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
    
    def get_statistics(self) -> dict:
        """Get trading bot statistics"""
        return {
            'signals_received': self.signals_received,
            'trades_created': self.trades_created,
            'trades_rejected': self.trades_rejected,
            'active_positions': self.position_manager.get_position_count(),
            'success_rate': self.trades_created / self.signals_received if self.signals_received > 0 else 0
        }
    
    def print_statistics(self):
        """Print trading bot statistics"""
        stats = self.get_statistics()
        
        logger.info("\n" + "="*80)
        logger.info("TRADING BOT STATISTICS")
        logger.info("="*80)
        logger.info(f"  Signals Received: {stats['signals_received']}")
        logger.info(f"  Trades Created: {stats['trades_created']}")
        logger.info(f"  Trades Rejected: {stats['trades_rejected']}")
        logger.info(f"  Success Rate: {stats['success_rate']:.1%}")
        logger.info(f"  Active Positions: {stats['active_positions']}")
        logger.info("="*80 + "\n")
