"""
Database migration script to add pattern_group column to alerts table
Run this once to upgrade existing database
"""
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database(db_path: str = 'data/choch_alerts.db'):
    """
    Add pattern_group column to alerts and alert_archive tables
    
    Args:
        db_path: Path to SQLite database file
    """
    db_file = Path(db_path)
    
    if not db_file.exists():
        logger.error(f"Database file not found: {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists in alerts table
        cursor.execute("PRAGMA table_info(alerts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'pattern_group' not in columns:
            logger.info("Adding pattern_group column to alerts table...")
            cursor.execute("""
                ALTER TABLE alerts 
                ADD COLUMN pattern_group VARCHAR(10)
            """)
            
            # Create index on pattern_group
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_pattern_group 
                ON alerts(pattern_group)
            """)
            
            conn.commit()
            logger.info("✓ Successfully added pattern_group column to alerts table")
        else:
            logger.info("✓ pattern_group column already exists in alerts table")
        
        # Check if column exists in alert_archive table
        cursor.execute("PRAGMA table_info(alert_archive)")
        archive_columns = [column[1] for column in cursor.fetchall()]
        
        if 'pattern_group' not in archive_columns:
            logger.info("Adding pattern_group column to alert_archive table...")
            cursor.execute("""
                ALTER TABLE alert_archive 
                ADD COLUMN pattern_group VARCHAR(10)
            """)
            
            # Create index on pattern_group
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_archive_pattern_group 
                ON alert_archive(pattern_group)
            """)
            
            conn.commit()
            logger.info("✓ Successfully added pattern_group column to alert_archive table")
        else:
            logger.info("✓ pattern_group column already exists in alert_archive table")
        
        # Close connection
        cursor.close()
        conn.close()
        
        logger.info("=" * 60)
        logger.info("✓✓✓ Database migration completed successfully!")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("CHoCH Alert System - Database Migration")
    print("Adding pattern_group column (G1, G2, G3)")
    print("=" * 60)
    print()
    
    # Run migration
    success = migrate_database()
    
    if success:
        print()
        print("✓ Migration completed! You can now run the system.")
        print("  New alerts will include pattern group information (G1, G2, G3)")
    else:
        print()
        print("✗ Migration failed. Check the logs above.")
        exit(1)
