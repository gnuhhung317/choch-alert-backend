"""
Signal Bus - Event-driven signal distribution
Loose coupling between scanner and consumers (Telegram, Trading Bot)
"""
import asyncio
import logging
from typing import Callable, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Trading signal from CHoCH detector"""
    symbol: str
    timeframe: str
    direction: str  # 'Long' or 'Short'
    signal_type: str  # 'CHoCH Up' or 'CHoCH Down'
    pattern_group: str  # 'G1', 'G2', 'G3'
    
    # Price levels
    choch_price: float
    entry1_price: float  # Conservative entry
    entry2_price: float  # Aggressive entry
    tp_price: float
    sl_price: float
    
    # Pivot references
    pivot5: float
    pivot6: float
    pivot8: float
    
    # Timing
    timestamp: datetime
    
    # Additional metadata
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        """Convert signal to dictionary"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'direction': self.direction,
            'signal_type': self.signal_type,
            'pattern_group': self.pattern_group,
            'choch_price': self.choch_price,
            'entry1_price': self.entry1_price,
            'entry2_price': self.entry2_price,
            'tp_price': self.tp_price,
            'sl_price': self.sl_price,
            'pivot5': self.pivot5,
            'pivot6': self.pivot6,
            'pivot8': self.pivot8,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata
        }


class SignalBus:
    """
    Signal Bus for event-driven architecture
    Decouples signal producers (scanner) from consumers (telegram, trading bot)
    """
    
    def __init__(self):
        self.subscribers: List[Callable] = []
        self.signal_count = 0
        
    def subscribe(self, callback: Callable):
        """
        Subscribe to signals
        
        Args:
            callback: Async function to call when signal is published
                     Signature: async def callback(signal: Signal) -> None
        """
        if callback not in self.subscribers:
            self.subscribers.append(callback)
            logger.info(f"Subscriber added: {callback.__name__} (total: {len(self.subscribers)})")
        else:
            logger.warning(f"Subscriber already exists: {callback.__name__}")
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from signals"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"Subscriber removed: {callback.__name__} (total: {len(self.subscribers)})")
    
    async def publish(self, signal: Signal):
        """
        Publish signal to all subscribers
        
        Args:
            signal: Signal object to publish
        """
        self.signal_count += 1
        
        logger.info(f"\n{'='*80}")
        logger.info(f"[SIGNAL BUS] Publishing signal #{self.signal_count}")
        logger.info(f"  {signal.symbol} {signal.timeframe} {signal.signal_type} ({signal.pattern_group})")
        logger.info(f"  Subscribers: {len(self.subscribers)}")
        logger.info(f"{'='*80}")
        
        if len(self.subscribers) == 0:
            logger.warning("⚠️  No subscribers - signal will be ignored!")
            return
        
        # Call all subscribers in parallel (non-blocking)
        tasks = []
        for subscriber in self.subscribers:
            try:
                task = asyncio.create_task(
                    self._safe_call_subscriber(subscriber, signal)
                )
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating task for {subscriber.__name__}: {e}")
        
        # Wait for all subscribers to process
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            success_count = sum(1 for r in results if r is True)
            error_count = sum(1 for r in results if isinstance(r, Exception))
            
            logger.info(f"[SIGNAL BUS] Delivery complete: {success_count}/{len(tasks)} success, {error_count} errors")
    
    async def _safe_call_subscriber(self, subscriber: Callable, signal: Signal) -> bool:
        """
        Safely call subscriber with error handling
        
        Returns:
            True if successful, False otherwise
        """
        try:
            subscriber_name = subscriber.__name__
            logger.debug(f"  → Calling {subscriber_name}...")
            
            await subscriber(signal)
            
            logger.debug(f"  ✓ {subscriber_name} completed")
            return True
            
        except Exception as e:
            logger.error(f"  ✗ Error in {subscriber.__name__}: {e}", exc_info=True)
            return False
    
    def get_subscriber_count(self) -> int:
        """Get number of subscribers"""
        return len(self.subscribers)
    
    def get_signal_count(self) -> int:
        """Get total number of signals published"""
        return self.signal_count


# Global signal bus instance (singleton pattern)
_global_signal_bus: SignalBus = None


def get_signal_bus() -> SignalBus:
    """Get global signal bus instance"""
    global _global_signal_bus
    if _global_signal_bus is None:
        _global_signal_bus = SignalBus()
        logger.info("Global signal bus created")
    return _global_signal_bus
