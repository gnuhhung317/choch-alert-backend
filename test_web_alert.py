"""
Test script to verify web alert broadcasting
"""
import logging
from datetime import datetime
from web.app import broadcast_alert
from alert.telegram_sender import create_alert_data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create test alert data
test_alert = create_alert_data(
    symbol='BTCUSDT',
    timeframe='5m',
    signal_type='CHoCH Up',
    direction='Long',
    price=67432.50,
    timestamp=datetime.now(),
    pattern_group='G1'
)

logger.info("=" * 60)
logger.info("TEST ALERT DATA")
logger.info("=" * 60)
for key, value in test_alert.items():
    logger.info(f"  {key}: {value}")

logger.info("\n" + "=" * 60)
logger.info("BROADCASTING ALERT...")
logger.info("=" * 60)

# Test broadcast
try:
    broadcast_alert(test_alert)
    logger.info("✅ Broadcast successful!")
except Exception as e:
    logger.error(f"❌ Broadcast failed: {e}", exc_info=True)

logger.info("\n" + "=" * 60)
logger.info("CHECK DATABASE")
logger.info("=" * 60)

from database.alert_db import get_database
db = get_database('data/choch_alerts.db')

recent = db.get_recent_alerts(limit=1)
if recent:
    alert = recent[0]
    logger.info("Latest alert from DB:")
    for key, value in alert.items():
        logger.info(f"  {key}: {value}")
else:
    logger.warning("No alerts in database")

logger.info("\n✅ Test completed!")
