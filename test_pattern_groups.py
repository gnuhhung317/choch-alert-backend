"""
Quick test to verify pattern groups implementation
"""
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_detector():
    """Test if detector returns pattern_group"""
    logger.info("=" * 60)
    logger.info("TEST 1: Detector Pattern Group")
    logger.info("=" * 60)
    
    from detectors.choch_detector import ChochDetector, TimeframeState
    
    # Create detector
    detector = ChochDetector()
    
    # Create state
    state = detector.get_state('5m')
    
    # Check if pattern_group field exists
    assert hasattr(state, 'pattern_group'), "❌ pattern_group field missing in TimeframeState"
    logger.info("✓ TimeframeState has pattern_group field")
    
    # Check initial value
    assert state.pattern_group is None, "❌ Initial pattern_group should be None"
    logger.info("✓ Initial pattern_group is None")
    
    return True

def test_database():
    """Test if database has pattern_group column"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Database Schema")
    logger.info("=" * 60)
    
    import sqlite3
    
    conn = sqlite3.connect('data/choch_alerts.db')
    cursor = conn.cursor()
    
    # Check alerts table
    cursor.execute("PRAGMA table_info(alerts)")
    columns = [col[1] for col in cursor.fetchall()]
    
    assert 'pattern_group' in columns, "❌ pattern_group column missing in alerts table"
    logger.info("✓ alerts table has pattern_group column")
    
    # Check alert_archive table
    cursor.execute("PRAGMA table_info(alert_archive)")
    archive_columns = [col[1] for col in cursor.fetchall()]
    
    assert 'pattern_group' in archive_columns, "❌ pattern_group column missing in alert_archive table"
    logger.info("✓ alert_archive table has pattern_group column")
    
    conn.close()
    return True

def test_alert_creation():
    """Test if create_alert_data accepts pattern_group"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Alert Creation")
    logger.info("=" * 60)
    
    from alert.telegram_sender import create_alert_data
    
    # Create test alert with pattern_group
    alert_data = create_alert_data(
        symbol='BTCUSDT',
        timeframe='5m',
        signal_type='CHoCH Up',
        direction='Long',
        price=50000.0,
        timestamp=datetime.now(),
        pattern_group='G2'
    )
    
    # Check if pattern_group is included
    assert 'nhóm' in alert_data, "❌ 'nhóm' key missing in alert_data"
    assert alert_data['nhóm'] == 'G2', f"❌ Expected G2, got {alert_data['nhóm']}"
    logger.info("✓ create_alert_data includes pattern_group")
    logger.info(f"  Alert data keys: {list(alert_data.keys())}")
    
    return True

def test_model():
    """Test if Alert model has pattern_group field"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Alert Model")
    logger.info("=" * 60)
    
    from database.models import Alert
    from datetime import datetime
    
    # Check if Alert has pattern_group column
    assert hasattr(Alert, 'pattern_group'), "❌ Alert model missing pattern_group field"
    logger.info("✓ Alert model has pattern_group field")
    
    # Test creating alert with pattern_group
    test_alert = Alert(
        symbol='TESTUSDT',
        timeframe='15m',
        signal_type='CHoCH Up',
        direction='Long',
        pattern_group='G3',
        price=100.0,
        signal_timestamp=datetime.now(),
        created_at=datetime.now()  # Add created_at
    )
    
    assert test_alert.pattern_group == 'G3', "❌ pattern_group not set correctly"
    logger.info("✓ Alert instance can store pattern_group")
    
    # Test to_dict
    alert_dict = test_alert.to_dict()
    assert 'nhóm' in alert_dict, "❌ to_dict() missing 'nhóm' key"
    assert alert_dict['nhóm'] == 'G3', f"❌ Expected G3, got {alert_dict['nhóm']}"
    logger.info("✓ Alert.to_dict() includes pattern_group")
    
    return True

def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PATTERN GROUPS VERIFICATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Detector", test_detector),
        ("Database", test_database),
        ("Alert Creation", test_alert_creation),
        ("Model", test_model)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, True, None))
        except Exception as e:
            logger.error(f"❌ Test {name} failed: {e}")
            results.append((name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{name:20s}: {status}")
        if error:
            print(f"  Error: {error}")
    
    print("\n" + "=" * 60)
    print(f"RESULT: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n✅ All tests passed! System is ready.")
        return 0
    else:
        print("\n❌ Some tests failed. Check errors above.")
        return 1

if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
