#!/usr/bin/env python3
"""
Database initialization and migration script for CHoCH Alert System
"""
import os
import sys
import logging
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import create_database_engine, create_tables, Alert, AlertArchive
from database.alert_db import AlertDatabase


def init_database(db_path: str = 'data/choch_alerts.db', force: bool = False):
    """
    Initialize database with tables
    
    Args:
        db_path: Path to database file
        force: If True, recreate tables even if they exist
    """
    print(f"Initializing database: {db_path}")
    
    # Check if database exists
    if os.path.exists(db_path) and not force:
        print(f"Database already exists at {db_path}")
        return
    
    # Create directory if needed
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Create engine and tables
    engine = create_database_engine(db_path)
    
    if force:
        print("Dropping existing tables...")
        from database.models import Base
        Base.metadata.drop_all(engine)
    
    print("Creating tables...")
    create_tables(engine)
    
    print(f"✅ Database initialized successfully at {db_path}")


def populate_sample_data(db_path: str = 'data/choch_alerts.db'):
    """
    Populate database with sample data for testing
    
    Args:
        db_path: Path to database file
    """
    print("Populating sample data...")
    
    db = AlertDatabase(db_path)
    
    # Sample alerts
    sample_alerts = [
        {
            'symbol': 'BTCUSDT',
            'khung': '5m',
            'hướng': 'Long',
            'loại': 'CHoCH Up',
            'price': 45234.56,
            'tradingview_link': 'https://in.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT.P&interval=5',
            'signal_timestamp': datetime.utcnow() - timedelta(hours=2)
        },
        {
            'symbol': 'ETHUSDT',
            'khung': '15m',
            'hướng': 'Short',
            'loại': 'CHoCH Down',
            'price': 3045.78,
            'tradingview_link': 'https://in.tradingview.com/chart/?symbol=BINANCE%3AETHUSDT.P&interval=15',
            'signal_timestamp': datetime.utcnow() - timedelta(hours=1, minutes=30)
        },
        {
            'symbol': 'BNBUSDT',
            'khung': '1h',
            'hướng': 'Long',
            'loại': 'CHoCH Up',
            'price': 234.12,
            'tradingview_link': 'https://in.tradingview.com/chart/?symbol=BINANCE%3ABNBUSDT.P&interval=60',
            'signal_timestamp': datetime.utcnow() - timedelta(hours=1)
        },
        {
            'symbol': 'XRPUSDT',
            'khung': '4h',
            'hướng': 'Short',
            'loại': 'CHoCH Down',
            'price': 0.6789,
            'tradingview_link': 'https://in.tradingview.com/chart/?symbol=BINANCE%3AXRPUSDT.P&interval=240',
            'signal_timestamp': datetime.utcnow() - timedelta(minutes=45)
        },
        {
            'symbol': 'ADAUSDT',
            'khung': '5m',
            'hướng': 'Long',
            'loại': 'CHoCH Up',
            'price': 0.4523,
            'tradingview_link': 'https://in.tradingview.com/chart/?symbol=BINANCE%3AADAUSDT.P&interval=5',
            'signal_timestamp': datetime.utcnow() - timedelta(minutes=20)
        }
    ]
    
    # Add sample alerts
    for i, alert_data in enumerate(sample_alerts, 1):
        alert = db.add_alert(alert_data)
        if alert:
            print(f"  {i}. Added: {alert.symbol} {alert.timeframe} {alert.direction}")
        else:
            print(f"  {i}. Failed to add alert for {alert_data['symbol']}")
    
    print(f"✅ Added {len(sample_alerts)} sample alerts")


def migrate_from_memory(old_alerts_data: list, db_path: str = 'data/choch_alerts.db'):
    """
    Migrate alerts from old memory-based storage to database
    
    Args:
        old_alerts_data: List of alert dictionaries from memory storage
        db_path: Path to database file
    """
    print(f"Migrating {len(old_alerts_data)} alerts from memory to database...")
    
    db = AlertDatabase(db_path)
    migrated_count = 0
    
    for alert_data in old_alerts_data:
        try:
            # Convert time_date string to datetime if needed
            if 'time_date' in alert_data and 'signal_timestamp' not in alert_data:
                try:
                    alert_data['signal_timestamp'] = datetime.strptime(
                        alert_data['time_date'], '%Y-%m-%d %H:%M:%S'
                    )
                except (ValueError, TypeError):
                    alert_data['signal_timestamp'] = datetime.utcnow()
            
            alert = db.add_alert(alert_data)
            if alert:
                migrated_count += 1
                
        except Exception as e:
            print(f"  Error migrating alert: {e}")
    
    print(f"✅ Successfully migrated {migrated_count}/{len(old_alerts_data)} alerts")


def database_info(db_path: str = 'data/choch_alerts.db'):
    """
    Show database information and statistics
    
    Args:
        db_path: Path to database file
    """
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return
    
    print(f"Database Information: {db_path}")
    print("=" * 50)
    
    db = AlertDatabase(db_path)
    
    # Get statistics
    stats = db.get_alert_stats()
    print(f"Total Alerts: {stats.get('total_alerts', 0)}")
    print(f"Long Alerts: {stats.get('long_alerts', 0)}")
    print(f"Short Alerts: {stats.get('short_alerts', 0)}")
    print(f"Today's Alerts: {stats.get('today_alerts', 0)}")
    
    print("\nTop Symbols:")
    for symbol_stat in stats.get('top_symbols', [])[:5]:
        print(f"  {symbol_stat['symbol']}: {symbol_stat['count']} alerts")
    
    print("\nTop Timeframes:")
    for tf_stat in stats.get('top_timeframes', [])[:5]:
        print(f"  {tf_stat['timeframe']}: {tf_stat['count']} alerts")
    
    # Get unique values
    unique = db.get_unique_values()
    print(f"\nUnique Symbols: {len(unique['symbols'])}")
    print(f"Unique Timeframes: {len(unique['timeframes'])}")
    print(f"Unique Directions: {len(unique['directions'])}")
    print(f"Unique Signal Types: {len(unique['signal_types'])}")
    
    # Recent alerts
    recent = db.get_recent_alerts(limit=5)
    print(f"\nMost Recent Alerts:")
    for alert in recent:
        print(f"  {alert['time_date']} - {alert['symbol']} {alert['khung']} {alert['hướng']}")


def cleanup_old_alerts(db_path: str = 'data/choch_alerts.db', days: int = 30):
    """
    Cleanup old alerts by archiving them
    
    Args:
        db_path: Path to database file
        days: Number of days to keep alerts
    """
    print(f"Cleaning up alerts older than {days} days...")
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return
    
    db = AlertDatabase(db_path)
    archived_count = db.cleanup_old_alerts(days_to_keep=days)
    
    print(f"✅ Archived {archived_count} old alerts")


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CHoCH Alert Database Management')
    parser.add_argument('--db-path', default='data/choch_alerts.db', 
                       help='Path to database file')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize database')
    init_parser.add_argument('--force', action='store_true', 
                           help='Force recreate tables')
    
    # Sample data command
    subparsers.add_parser('sample', help='Add sample data')
    
    # Info command
    subparsers.add_parser('info', help='Show database information')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old alerts')
    cleanup_parser.add_argument('--days', type=int, default=30,
                               help='Days to keep alerts (default: 30)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Execute commands
    try:
        if args.command == 'init':
            init_database(args.db_path, force=args.force)
            
        elif args.command == 'sample':
            populate_sample_data(args.db_path)
            
        elif args.command == 'info':
            database_info(args.db_path)
            
        elif args.command == 'cleanup':
            cleanup_old_alerts(args.db_path, args.days)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())