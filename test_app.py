import unittest
from unittest.mock import patch, MagicMock, call
import pandas as pd
from datetime import datetime, timedelta
import time
from cachetools import TTLCache, cached

# Adjust imports to the new structure
import sys
sys.path.append('.')
from app import app
# Import from the new module
from etf_calculator import calculate_etf_data, get_all_etf_data, cache

class TestEtfFunctions(unittest.TestCase):

    def setUp(self):
        # The Flask app context is needed for the logger to work
        self.app_context = app.app_context()
        self.app_context.push()
        # Clear cache before each test to ensure isolation
        cache.clear()

    def tearDown(self):
        self.app_context.pop()

    @patch('etf_calculator.yf.Ticker')
    @patch('etf_calculator.yf.download')
    def test_calculate_etf_data_success(self, mock_download, mock_ticker):
        """
        Tests the core data calculation logic for a single ETF.
        """
        # --- Mocking yfinance ---
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance

        hist_df = pd.DataFrame({'Close': [100.0, 105.0]})
        mock_ticker_instance.history.return_value = hist_df

        dividends_index = pd.to_datetime([(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')])
        dividends_series = pd.Series([1.0], index=dividends_index)
        mock_ticker_instance.dividends = dividends_series

        index_2m = pd.to_datetime([(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')])
        index_1m = pd.to_datetime([(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')])
        combined_index = index_2m.union(index_1m)
        combined_df = pd.DataFrame({'Close': [90.0, 95.0]}, index=combined_index)
        mock_download.return_value = combined_df

        # --- Call the function ---
        result = calculate_etf_data("TEST")

        # --- Assertions ---
        self.assertNotIn("error", result)
        self.assertAlmostEqual(result["current_price"], 105.0)
        self.assertAlmostEqual(result["one_month_return"], 11.578947368421053)
        self.assertAlmostEqual(result["two_month_return"], 17.77777777777778)

    @patch('etf_calculator.calculate_etf_data')
    def test_get_all_etf_data_concurrency(self, mock_calculate):
        """
        Tests that get_all_etf_data calls the calculator for each symbol.
        """
        # --- Mocking ---
        mock_calculate.side_effect = lambda symbol: {"data": f"data_for_{symbol}"}
        symbols = ("ETF1", "ETF2")

        # --- Call the function ---
        results = get_all_etf_data(symbols)

        # --- Assertions ---
        mock_calculate.assert_has_calls([call("ETF1"), call("ETF2")], any_order=True)
        self.assertEqual(len(results), 2)
        self.assertEqual(results["ETF1"]["data"], "data_for_ETF1")

    @patch('etf_calculator.calculate_etf_data')
    def test_caching_get_all_etf_data(self, mock_calculate):
        """
        Tests that the results from get_all_etf_data are cached.
        """
        # --- Mocking ---
        mock_calculate.return_value = {"mock_data": "some_value"}
        symbols = ("CACHE1", "CACHE2")

        # --- Call the function twice ---
        result1 = get_all_etf_data(symbols)
        result2 = get_all_etf_data(symbols)

        # --- Assertions ---
        # The mock should only be called once for each symbol on the first call
        self.assertEqual(mock_calculate.call_count, len(symbols))
        self.assertEqual(result1, result2)

        # --- Test after clearing cache ---
        cache.clear()
        result3 = get_all_etf_data(symbols)
        # The mock should be called again after clearing the cache
        self.assertEqual(mock_calculate.call_count, len(symbols) * 2)


    @patch('time.monotonic')
    def test_cache_ttl(self, mock_monotonic):
        """
        Tests that the cache expires after the TTL by mocking time.monotonic.
        """
        # --- Setup local cache for isolated test ---
        # We must patch time.monotonic as it's the default timer for TTLCache
        test_cache = TTLCache(maxsize=10, ttl=5, timer=time.monotonic)

        @cached(test_cache)
        def dummy_expensive_call(arg):
            dummy_expensive_call.call_count[0] += 1
            return f"result_for_{arg}"
        dummy_expensive_call.call_count = [0] # Use a list for mutable counter

        # --- Test caching behavior ---
        mock_monotonic.return_value = 0

        # Call 1: Should be a cache miss
        res1 = dummy_expensive_call("A")
        self.assertEqual(res1, "result_for_A")
        self.assertEqual(dummy_expensive_call.call_count[0], 1)

        # Call 2: Should be a cache hit
        res2 = dummy_expensive_call("A")
        self.assertEqual(res2, "result_for_A")
        self.assertEqual(dummy_expensive_call.call_count[0], 1)

        # --- Advance time past TTL ---
        mock_monotonic.return_value = 6 # 6 seconds have passed, TTL is 5

        # Call 3: Should be a cache miss again due to expiration
        res3 = dummy_expensive_call("A")
        self.assertEqual(res3, "result_for_A")
        self.assertEqual(dummy_expensive_call.call_count[0], 2)


if __name__ == '__main__':
    unittest.main()