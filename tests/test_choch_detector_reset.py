import pandas as pd
import numpy as np
from detectors.choch_detector import ChochDetector


def make_sine_df(n=50):
    idx = pd.date_range('2025-01-01', periods=n, freq='5T')
    t = np.arange(n)
    price = 1.0 + 0.01 * np.sin(2 * np.pi * t / 8)
    df = pd.DataFrame({
        'open': price,
        'high': price + 0.001,
        'low': price - 0.001,
        'close': price
    }, index=idx)
    return df


def test_reset_behavior():
    det = ChochDetector(left=1, right=1, keep_pivots=200)
    df = make_sine_df(50)

    # First build
    r1 = det.process_new_bar('5m', df)
    state = det.states.get('5m')
    assert state is not None
    pivots_after_first = state.pivot_count()

    # Build again from same df - should not grow beyond reasonable bounds
    r2 = det.process_new_bar('5m', df)
    pivots_after_second = det.states.get('5m').pivot_count()

    # With reset, counts should be equal
    assert pivots_after_first == pivots_after_second

    print('Pivots:', pivots_after_first)


if __name__ == '__main__':
    test_reset_behavior()
    print('OK')
