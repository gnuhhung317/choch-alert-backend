"""
Database helper utilities for CHoCH Alert System
"""
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_, func
import logging

from .models import Alert, AlertArchive, create_database_engine, create_tables, get_session_maker

logger = logging.getLogger(__name__)


class AlertDatabase:
    """
    Database manager for CHoCH alerts
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.engine = create_database_engine(db_path)
        create_tables(self.engine)
        self.Session = get_session_maker(self.engine)
        
        logger.info(f"AlertDatabase initialized with engine: {self.engine.url}")
    
    def get_session(self) -> Session:
        """Get new database session"""
        return self.Session()
    
    def add_alert(self, alert_data: Dict) -> Optional[Alert]:
        """
        Add new alert to database
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            Alert: Created alert object or None if failed
        """
        session = self.get_session()
        try:
            alert = Alert.from_alert_data(alert_data)
            session.add(alert)
            session.commit()
            session.refresh(alert)  # Get the ID
            
            logger.info(f"Added alert: {alert.symbol} {alert.timeframe} {alert.direction}")
            return alert
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding alert: {e}")
            return None
        finally:
            session.close()
    
    def get_recent_alerts(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get recent alerts ordered by timestamp
        
        Args:
            limit: Maximum number of alerts to return
            offset: Number of alerts to skip
            
        Returns:
            List[Dict]: List of alert dictionaries
        """
        session = self.get_session()
        try:
            alerts = (session.query(Alert)
                     .order_by(desc(Alert.signal_timestamp))
                     .limit(limit)
                     .offset(offset)
                     .all())
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
        finally:
            session.close()
    
    def get_alerts_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        Get alerts for specific symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            limit: Maximum number of alerts
            
        Returns:
            List[Dict]: List of alert dictionaries
        """
        session = self.get_session()
        try:
            alerts = (session.query(Alert)
                     .filter(Alert.symbol == symbol)
                     .order_by(desc(Alert.signal_timestamp))
                     .limit(limit)
                     .all())
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting alerts for {symbol}: {e}")
            return []
        finally:
            session.close()
    
    def get_alerts_by_timeframe(self, timeframe: str, limit: int = 50) -> List[Dict]:
        """
        Get alerts for specific timeframe
        
        Args:
            timeframe: Timeframe (e.g., '5m', '1h')
            limit: Maximum number of alerts
            
        Returns:
            List[Dict]: List of alert dictionaries
        """
        session = self.get_session()
        try:
            alerts = (session.query(Alert)
                     .filter(Alert.timeframe == timeframe)
                     .order_by(desc(Alert.signal_timestamp))
                     .limit(limit)
                     .all())
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting alerts for timeframe {timeframe}: {e}")
            return []
        finally:
            session.close()
    
    def filter_alerts(self,
                     symbols: List[str] = None,
                     timeframes: List[str] = None,
                     directions: List[str] = None,
                     signal_types: List[str] = None,
                     start_date: datetime = None,
                     end_date: datetime = None,
                     limit: int = 100,
                     offset: int = 0) -> List[Dict]:
        """
        Filter alerts by multiple criteria
        
        Args:
            symbols: List of symbols to filter by
            timeframes: List of timeframes to filter by
            directions: List of directions to filter by
            signal_types: List of signal types to filter by
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List[Dict]: Filtered alert dictionaries
        """
        session = self.get_session()
        try:
            query = session.query(Alert)
            
            # Apply filters
            if symbols:
                query = query.filter(Alert.symbol.in_(symbols))
            
            if timeframes:
                query = query.filter(Alert.timeframe.in_(timeframes))
            
            if directions:
                query = query.filter(Alert.direction.in_(directions))
            
            if signal_types:
                query = query.filter(Alert.signal_type.in_(signal_types))
            
            if start_date:
                query = query.filter(Alert.signal_timestamp >= start_date)
            
            if end_date:
                query = query.filter(Alert.signal_timestamp <= end_date)
            
            # Order and limit
            alerts = (query.order_by(desc(Alert.signal_timestamp))
                     .limit(limit)
                     .offset(offset)
                     .all())
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error filtering alerts: {e}")
            return []
        finally:
            session.close()
    
    def get_alert_stats(self) -> Dict:
        """
        Get alert statistics
        
        Returns:
            Dict: Statistics about alerts
        """
        session = self.get_session()
        try:
            total_alerts = session.query(Alert).count()
            
            # Alerts by direction
            long_count = session.query(Alert).filter(Alert.direction == 'Long').count()
            short_count = session.query(Alert).filter(Alert.direction == 'Short').count()
            
            # Alerts today
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_count = session.query(Alert).filter(Alert.signal_timestamp >= today_start).count()
            
            # Most active symbols
            symbol_stats = (session.query(Alert.symbol, func.count(Alert.id).label('count'))
                           .group_by(Alert.symbol)
                           .order_by(desc('count'))
                           .limit(10)
                           .all())
            
            # Most active timeframes
            timeframe_stats = (session.query(Alert.timeframe, func.count(Alert.id).label('count'))
                              .group_by(Alert.timeframe)
                              .order_by(desc('count'))
                              .limit(10)
                              .all())
            
            return {
                'total_alerts': total_alerts,
                'long_alerts': long_count,
                'short_alerts': short_count,
                'today_alerts': today_count,
                'top_symbols': [{'symbol': s, 'count': c} for s, c in symbol_stats],
                'top_timeframes': [{'timeframe': t, 'count': c} for t, c in timeframe_stats]
            }
            
        except Exception as e:
            logger.error(f"Error getting alert stats: {e}")
            return {}
        finally:
            session.close()
    
    def get_unique_values(self) -> Dict[str, List[str]]:
        """
        Get unique values for filter dropdowns
        
        Returns:
            Dict: Dictionary with unique symbols, timeframes, directions, signal_types
        """
        session = self.get_session()
        try:
            symbols = [s[0] for s in session.query(Alert.symbol.distinct()).all()]
            timeframes = [t[0] for t in session.query(Alert.timeframe.distinct()).all()]
            directions = [d[0] for d in session.query(Alert.direction.distinct()).all()]
            signal_types = [st[0] for st in session.query(Alert.signal_type.distinct()).all()]
            
            return {
                'symbols': sorted(symbols),
                'timeframes': sorted(timeframes, key=lambda x: self._timeframe_sort_key(x)),
                'directions': sorted(directions),
                'signal_types': sorted(signal_types)
            }
            
        except Exception as e:
            logger.error(f"Error getting unique values: {e}")
            return {'symbols': [], 'timeframes': [], 'directions': [], 'signal_types': []}
        finally:
            session.close()
    
    def _timeframe_sort_key(self, timeframe: str) -> int:
        """Sort key for timeframes"""
        timeframe_order = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
            '1d': 1440, '3d': 4320, '1w': 10080, '1M': 43200
        }
        return timeframe_order.get(timeframe, 999999)
    
    def cleanup_old_alerts(self, days_to_keep: int = 30) -> int:
        """
        Archive and delete old alerts
        
        Args:
            days_to_keep: Number of days to keep alerts
            
        Returns:
            int: Number of alerts archived
        """
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Get old alerts
            old_alerts = (session.query(Alert)
                         .filter(Alert.signal_timestamp < cutoff_date)
                         .all())
            
            archived_count = 0
            for alert in old_alerts:
                # Create archive record
                archive = AlertArchive(
                    original_id=alert.id,
                    symbol=alert.symbol,
                    timeframe=alert.timeframe,
                    signal_type=alert.signal_type,
                    direction=alert.direction,
                    price=alert.price,
                    signal_timestamp=alert.signal_timestamp,
                    created_at=alert.created_at,
                    tradingview_link=alert.tradingview_link,
                    is_futures=alert.is_futures,
                    region=alert.region,
                    confidence_score=alert.confidence_score,
                    notes=alert.notes
                )
                session.add(archive)
                
                # Delete original alert
                session.delete(alert)
                archived_count += 1
            
            session.commit()
            logger.info(f"Archived {archived_count} old alerts")
            return archived_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error archiving old alerts: {e}")
            return 0
        finally:
            session.close()
    
    def delete_alert(self, alert_id: int) -> bool:
        """
        Delete specific alert
        
        Args:
            alert_id: Alert ID to delete
            
        Returns:
            bool: True if deleted successfully
        """
        session = self.get_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                session.delete(alert)
                session.commit()
                logger.info(f"Deleted alert {alert_id}")
                return True
            else:
                logger.warning(f"Alert {alert_id} not found")
                return False
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting alert {alert_id}: {e}")
            return False
        finally:
            session.close()
    
    def close(self):
        """Close database connections"""
        if hasattr(self, 'engine'):
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database instance
_db_instance = None


def get_database(db_path: str = None) -> AlertDatabase:
    """
    Get global database instance (singleton pattern)
    
    Args:
        db_path: Path to database file
        
    Returns:
        AlertDatabase: Database instance
    """
    global _db_instance
    
    if _db_instance is None:
        _db_instance = AlertDatabase(db_path)
    
    return _db_instance


if __name__ == '__main__':
    # Test database operations
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("Testing AlertDatabase...")
    
    # Initialize database
    db = AlertDatabase('test_alert_db.db')
    
    # Test data
    test_alerts = [
        {
            'symbol': 'BTCUSDT',
            'khung': '5m',
            'hướng': 'Long',
            'loại': 'CHoCH Up',
            'price': 45000.0,
            'tradingview_link': 'https://tradingview.com/test1',
            'signal_timestamp': datetime.utcnow() - timedelta(hours=1)
        },
        {
            'symbol': 'ETHUSDT',
            'khung': '15m',
            'hướng': 'Short',
            'loại': 'CHoCH Down',
            'price': 3000.0,
            'tradingview_link': 'https://tradingview.com/test2',
            'signal_timestamp': datetime.utcnow() - timedelta(minutes=30)
        }
    ]
    
    # Add test alerts
    print("\nAdding test alerts...")
    for alert_data in test_alerts:
        alert = db.add_alert(alert_data)
        if alert:
            print(f"  Added: {alert}")
    
    # Get recent alerts
    print("\nRecent alerts:")
    recent = db.get_recent_alerts(limit=10)
    for alert in recent:
        print(f"  {alert['symbol']} {alert['khung']} {alert['hướng']} @ {alert['price']}")
    
    # Get statistics
    print("\nAlert statistics:")
    stats = db.get_alert_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Get unique values
    print("\nUnique values:")
    unique = db.get_unique_values()
    for key, values in unique.items():
        print(f"  {key}: {values}")
    
    # Test filtering
    print("\nFiltering by symbol=BTCUSDT:")
    btc_alerts = db.filter_alerts(symbols=['BTCUSDT'])
    for alert in btc_alerts:
        print(f"  {alert['symbol']} {alert['khung']} {alert['hướng']}")
    
    print("\nDatabase test completed!")