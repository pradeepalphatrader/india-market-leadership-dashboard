import unittest
from india_market_dashboard.indicators import percent_return, range_percent, simple_moving_average, true_range_percent


class IndicatorTests(unittest.TestCase):
    def test_moving_average_uses_latest_period(self):
        self.assertEqual(simple_moving_average([1, 2, 3, 4, 5], 3), 4)

    def test_return_uses_prior_session_boundary(self):
        self.assertAlmostEqual(percent_return([100, 102, 110], 2), 10)

    def test_range_percent(self):
        self.assertEqual(round(range_percent([10, 12, 11], [9, 10, 10], 3), 2), 33.33)

    def test_true_range_percent_is_positive(self):
        closes = [100 + index for index in range(20)]
        highs = [value + 2 for value in closes]
        lows = [value - 2 for value in closes]
        self.assertGreater(true_range_percent(highs, lows, closes, 14), 0)
