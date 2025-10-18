"""
Unit tests for CHoCH detector
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from detectors.choch_detector import ChochDetector, TimeframeState


@pytest.fixture
def detector():
    """Create a CHoCH detector instance"""
    return ChochDetector(
        left=1,
        right=1,
        keep_pivots=200,
        use_variant_filter=True,
        allow_ph1=True,
        allow_ph2=True,
        allow_ph3=True,
        allow_pl1=True,
        allow_pl2=True,
        allow_pl3=True
    )


@pytest.fixture
def sample_uptrend_data():
    """Create sample uptrend OHLCV data"""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='5T')
    
    # Create uptrend with some pivots
    base_price = 50000
    data = []
    
    for i, date in enumerate(dates):
        # Uptrend with oscillations
        trend = i * 50
        oscillation = np.sin(i * 0.3) * 200
        
        close = base_price + trend + oscillation
        high = close + np.random.uniform(50, 150)
        low = close - np.random.uniform(50, 150)
        open_ = (high + low) / 2 + np.random.uniform(-50, 50)
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': date,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


@pytest.fixture
def sample_downtrend_data():
    """Create sample downtrend OHLCV data"""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='5T')
    
    # Create downtrend with some pivots
    base_price = 50000
    data = []
    
    for i, date in enumerate(dates):
        # Downtrend with oscillations
        trend = -i * 50
        oscillation = np.sin(i * 0.3) * 200
        
        close = base_price + trend + oscillation
        high = close + np.random.uniform(50, 150)
        low = close - np.random.uniform(50, 150)
        open_ = (high + low) / 2 + np.random.uniform(-50, 50)
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': date,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


@pytest.fixture
def pivot_pattern_data():
    """Create specific data with clear pivot patterns"""
    dates = pd.date_range(start='2025-01-01', periods=30, freq='5T')
    
    # Create specific pattern: PL-PH-PL-PH-PL-PH (6-pattern uptrend)
    prices = [
        50000, 50100, 50050,  # PL at idx 2
        50200, 50300, 50250,  # PH at idx 4
        50150, 50180, 50120,  # PL at idx 8
        50400, 50500, 50450,  # PH at idx 10
        50350, 50380, 50300,  # PL at idx 14
        50600, 50700, 50650,  # PH at idx 16
        50550, 50580, 50520,
        50750, 50800, 50780,
        50900, 51000, 51100   # CHoCH potential
    ]
    
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        high = close + np.random.uniform(10, 50)
        low = close - np.random.uniform(10, 50)
        open_ = (high + low) / 2
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': date,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


class TestChochDetector:
    """Test suite for CHoCH detector"""
    
    def test_initialization(self, detector):
        """Test detector initialization"""
        assert detector.left == 1
        assert detector.right == 1
        assert detector.keep_pivots == 200
        assert detector.use_variant_filter == True
        assert len(detector.states) == 0
    
    def test_get_state(self, detector):
        """Test state management per timeframe"""
        state_5m = detector.get_state('5m')
        state_15m = detector.get_state('15m')
        
        assert isinstance(state_5m, TimeframeState)
        assert isinstance(state_15m, TimeframeState)
        assert state_5m is not state_15m
        assert len(detector.states) == 2
    
    def test_detect_pivots(self, detector, sample_uptrend_data):
        """Test pivot detection"""
        ph, pl = detector.detect_pivots(sample_uptrend_data)
        
        # Should detect some pivots
        assert ph.notna().sum() > 0
        assert pl.notna().sum() > 0
        
        # Pivots should not be at edges
        assert pd.isna(ph.iloc[0])
        assert pd.isna(ph.iloc[-1])
    
    def test_classify_variant_ph1(self, detector):
        """Test PH1 variant classification"""
        # Create data with PH1 pattern
        data = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=3, freq='5T'),
            'high': [100, 110, 105],  # h2 > h1, h2 > h3
            'low': [90, 95, 92],       # l2 > l1, l2 > l3
            'close': [95, 105, 100],
            'open': [92, 98, 103],
            'volume': [100, 100, 100]
        }).set_index('timestamp')
        
        variant = detector.classify_variant(data, 1, is_high=True)
        assert variant == "PH1"
    
    def test_classify_variant_pl1(self, detector):
        """Test PL1 variant classification"""
        # Create data with PL1 pattern
        data = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=3, freq='5T'),
            'high': [110, 105, 108],   # h2 < h1, h2 < h3
            'low': [100, 90, 95],      # l2 < l1, l2 < l3
            'close': [105, 92, 100],
            'open': [108, 103, 97],
            'volume': [100, 100, 100]
        }).set_index('timestamp')
        
        variant = detector.classify_variant(data, 1, is_high=False)
        assert variant == "PL1"
    
    def test_process_new_bar_no_signal(self, detector, sample_uptrend_data):
        """Test processing bar without CHoCH signal"""
        # Take subset that won't have enough data for 6-pattern
        df_small = sample_uptrend_data.iloc[:20]
        
        result = detector.process_new_bar('5m', df_small)
        
        assert result['choch_up'] == False
        assert result['choch_down'] == False
        assert result['signal_type'] is None
    
    def test_process_new_bar_with_pivots(self, detector, pivot_pattern_data):
        """Test processing bar and storing pivots"""
        result = detector.process_new_bar('5m', pivot_pattern_data)
        
        state = detector.get_state('5m')
        
        # Should have detected some pivots
        assert state.pivot_count() > 0
    
    def test_timeframe_state_storage(self, detector):
        """Test pivot storage in state"""
        state = detector.get_state('test')
        
        # Store some pivots
        state.store_pivot(0, 50000.0, True)
        state.store_pivot(1, 49900.0, False)
        state.store_pivot(2, 50100.0, True)
        
        assert state.pivot_count() == 3
        
        # Get last pivot
        bar, price, is_high = state.get_pivot_from_end(0)
        assert bar == 2
        assert price == 50100.0
        assert is_high == True
    
    def test_pivot_maxlen(self, detector):
        """Test that pivot storage respects maxlen"""
        state = detector.get_state('test')
        
        # Store more than keep_pivots
        for i in range(250):
            state.store_pivot(i, 50000.0 + i, i % 2 == 0)
        
        assert state.pivot_count() == detector.keep_pivots
    
    def test_multiple_timeframes(self, detector, sample_uptrend_data, sample_downtrend_data):
        """Test processing multiple timeframes independently"""
        # Process 5m with uptrend
        result_5m = detector.process_new_bar('5m', sample_uptrend_data)
        
        # Process 15m with downtrend
        result_15m = detector.process_new_bar('15m', sample_downtrend_data)
        
        # States should be independent
        state_5m = detector.get_state('5m')
        state_15m = detector.get_state('15m')
        
        assert state_5m is not state_15m
    
    def test_choch_detection_structure(self, detector):
        """Test CHoCH detection result structure"""
        # Create minimal data
        dates = pd.date_range('2025-01-01', periods=10, freq='5T')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [50000] * 10,
            'high': [50100] * 10,
            'low': [49900] * 10,
            'close': [50000] * 10,
            'volume': [100] * 10
        }).set_index('timestamp')
        
        result = detector.process_new_bar('5m', data)
        
        # Check result structure
        assert 'choch_up' in result
        assert 'choch_down' in result
        assert 'signal_type' in result
        assert 'direction' in result
        assert 'price' in result
        assert 'timestamp' in result


class TestTimeframeState:
    """Test TimeframeState class"""
    
    def test_initialization(self):
        """Test state initialization"""
        state = TimeframeState(left=1, right=1, keep_pivots=200)
        
        assert state.left == 1
        assert state.right == 1
        assert state.keep_pivots == 200
        assert state.pivot_count() == 0
        assert state.last_pivot_bar is None
        assert state.choch_locked == False
    
    def test_store_and_retrieve_pivots(self):
        """Test storing and retrieving pivots"""
        state = TimeframeState(left=1, right=1, keep_pivots=200)
        
        state.store_pivot(0, 50000.0, True)
        state.store_pivot(5, 49900.0, False)
        state.store_pivot(10, 50100.0, True)
        
        # Get most recent
        bar, price, is_high = state.get_pivot_from_end(0)
        assert bar == 10
        assert price == 50100.0
        assert is_high == True
        
        # Get second most recent
        bar, price, is_high = state.get_pivot_from_end(1)
        assert bar == 5
        assert price == 49900.0
        assert is_high == False


def test_sample_data_generation(sample_uptrend_data, sample_downtrend_data):
    """Test that sample data is generated correctly"""
    assert len(sample_uptrend_data) == 100
    assert len(sample_downtrend_data) == 100
    
    # Check columns
    for df in [sample_uptrend_data, sample_downtrend_data]:
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
    
    # Uptrend should be generally increasing
    assert sample_uptrend_data['close'].iloc[-1] > sample_uptrend_data['close'].iloc[0]
    
    # Downtrend should be generally decreasing
    assert sample_downtrend_data['close'].iloc[-1] < sample_downtrend_data['close'].iloc[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
