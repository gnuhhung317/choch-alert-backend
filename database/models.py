"""
SQLAlchemy models for CHoCH Alert System
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import pytz

logger = logging.getLogger(__name__)

# GMT+7 timezone for Vietnam/Thailand
GMT7 = pytz.timezone('Asia/Bangkok')

Base = declarative_base()


class Alert(Base):
    """
    Alert model for storing CHoCH signal alerts
    """
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Alert identification
    symbol = Column(String(20), nullable=False, index=True)  # BTCUSDT, ETHUSDT, etc.
    timeframe = Column(String(10), nullable=False, index=True)  # 5m, 1h, 4h, etc.
    
    # Signal information
    signal_type = Column(String(50), nullable=False)  # CHoCH Up, CHoCH Down, etc.
    direction = Column(String(10), nullable=False, index=True)  # Long, Short
    pattern_group = Column(String(10), nullable=True, index=True)  # G1, G2, G3
    price = Column(Float, nullable=False)  # Current price when signal occurred
    
    # Timestamps
    signal_timestamp = Column(DateTime, nullable=False, index=True)  # When signal occurred
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # When record was created
    
    # TradingView link
    tradingview_link = Column(Text, nullable=True)  # Full TradingView URL
    
    # Additional metadata
    is_futures = Column(Boolean, default=True, nullable=False)  # Futures vs Spot
    region = Column(String(5), default='in', nullable=False)  # TradingView region
    
    # Optional fields for future use
    confidence_score = Column(Float, nullable=True)  # Signal confidence (0-100)
    notes = Column(Text, nullable=True)  # Additional notes
    
    def __repr__(self):
        return (f"<Alert(id={self.id}, symbol='{self.symbol}', "
                f"timeframe='{self.timeframe}', direction='{self.direction}', "
                f"pattern='{self.pattern_group}', "
                f"price={self.price}, timestamp='{self.signal_timestamp}')>")
    
    def to_dict(self):
        """
        Convert Alert model to dictionary format for API/JSON response
        Timestamps are converted to GMT+7
        
        Returns:
            dict: Alert data in the format expected by frontend
        """
        # Convert UTC timestamp to GMT+7
        signal_time_gmt7 = self.signal_timestamp.replace(tzinfo=pytz.UTC).astimezone(GMT7)
        created_time_gmt7 = self.created_at.replace(tzinfo=pytz.UTC).astimezone(GMT7)
        
        return {
            'id': self.id,
            'time_date': signal_time_gmt7.strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': self.symbol,
            'mã': self.symbol,  # Vietnamese alias
            'khung': self.timeframe,  # Vietnamese for timeframe
            'hướng': self.direction,  # Vietnamese for direction
            'nhóm': self.pattern_group,  # Vietnamese for pattern group
            'loại': self.signal_type,  # Vietnamese for signal type
            'price': self.price,
            'tradingview_link': self.tradingview_link,
            'created_at': created_time_gmt7.isoformat(),
            'is_futures': self.is_futures,
            'region': self.region,
            'confidence_score': self.confidence_score,
            'notes': self.notes
        }
    
    @classmethod
    def from_alert_data(cls, alert_data: dict):
        """
        Create Alert model from alert data dictionary
        
        Args:
            alert_data: Dictionary containing alert information
            
        Returns:
            Alert: New Alert instance
        """
        # Parse timestamp
        signal_timestamp = alert_data.get('signal_timestamp')
        if isinstance(signal_timestamp, str):
            try:
                signal_timestamp = datetime.fromisoformat(signal_timestamp)
            except (ValueError, TypeError):
                signal_timestamp = datetime.utcnow()
        elif not isinstance(signal_timestamp, datetime):
            signal_timestamp = datetime.utcnow()
        
        return cls(
            symbol=alert_data.get('symbol') or alert_data.get('mã', ''),
            timeframe=alert_data.get('khung', ''),
            signal_type=alert_data.get('loại', ''),
            direction=alert_data.get('hướng', ''),
            pattern_group=alert_data.get('nhóm'),  # Pattern group
            price=float(alert_data.get('price', 0)),
            signal_timestamp=signal_timestamp,
            tradingview_link=alert_data.get('tradingview_link', ''),
            is_futures=alert_data.get('is_futures', True),
            region=alert_data.get('region', 'in'),
            confidence_score=alert_data.get('confidence_score'),
            notes=alert_data.get('notes')
        )


class AlertArchive(Base):
    """
    Archive table for old alerts (for performance)
    """
    __tablename__ = 'alert_archive'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_id = Column(Integer, nullable=False)  # Original alert ID
    
    # Same fields as Alert
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False)
    direction = Column(String(10), nullable=False, index=True)
    pattern_group = Column(String(10), nullable=True, index=True)  # G1, G2, G3
    price = Column(Float, nullable=False)
    signal_timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    tradingview_link = Column(Text, nullable=True)
    is_futures = Column(Boolean, default=True, nullable=False)
    region = Column(String(5), default='in', nullable=False)
    confidence_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Archive metadata
    archived_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    archive_reason = Column(String(100), default='automatic_cleanup', nullable=False)
    
    def __repr__(self):
        return (f"<AlertArchive(id={self.id}, original_id={self.original_id}, "
                f"symbol='{self.symbol}', archived_at='{self.archived_at}')>")


# Database configuration
class DatabaseConfig:
    """Database configuration"""
    
    # Default SQLite database path
    DEFAULT_DB_PATH = 'data/choch_alerts.db'
    
    # Connection settings
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DEFAULT_DB_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Pool settings for SQLite
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True
    }


def create_database_engine(db_path: str = None):
    """
    Create SQLAlchemy engine
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Engine: SQLAlchemy engine
    """
    if db_path is None:
        db_path = DatabaseConfig.DEFAULT_DB_PATH
    
    # Ensure directory exists
    import os
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Create engine
    database_uri = f'sqlite:///{db_path}'
    engine = create_engine(
        database_uri,
        echo=False,  # Set to True for SQL debugging
        **DatabaseConfig.SQLALCHEMY_ENGINE_OPTIONS
    )
    
    logger.info(f"Created database engine: {database_uri}")
    return engine


def create_tables(engine):
    """
    Create all database tables
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")


def get_session_maker(engine):
    """
    Get SQLAlchemy session maker
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        sessionmaker: SQLAlchemy session maker
    """
    return sessionmaker(bind=engine)


if __name__ == '__main__':
    # Test database creation
    logging.basicConfig(level=logging.INFO)
    
    print("Creating test database...")
    engine = create_database_engine('test_alerts.db')
    create_tables(engine)
    
    # Test session
    Session = get_session_maker(engine)
    session = Session()
    
    # Test alert creation
    test_alert = Alert(
        symbol='BTCUSDT',
        timeframe='5m',
        signal_type='CHoCH Up',
        direction='Long',
        price=45000.50,
        signal_timestamp=datetime.utcnow(),
        tradingview_link='https://tradingview.com/test'
    )
    
    session.add(test_alert)
    session.commit()
    
    # Query test
    alerts = session.query(Alert).all()
    print(f"Found {len(alerts)} alerts:")
    for alert in alerts:
        print(f"  {alert}")
        print(f"  Dict: {alert.to_dict()}")
    
    session.close()
    print("Database test completed successfully!")