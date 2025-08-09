import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

# This is a bit of a hack to import app and calculate_etf_data
# from app.py. If this were a real package, we would have a better
# structure.
import sys
sys.path.append('.')
from app import app, calculate_etf_data

class TestEtfCalculator(unittest.TestCase):

    def setUp(self):
        # The Flask app context is needed for the logger to work
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('yfinance.Ticker')
    @patch('yfinance.download')
    def test_calculate_etf_data_success(self, mock_download, mock_ticker):
        # --- Mocking yfinance ---

        # 1. Mock yf.Ticker
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance

        # Mock ticker.history()
        hist_data = {'Close': [100.0, 105.0]}
        hist_df = pd.DataFrame(hist_data)
        mock_ticker_instance.history.return_value = hist_df

        # Mock ticker.dividends
        # Create a DatetimeIndex for the dividends
        one_month_ago_dt = datetime.now() - timedelta(days=30)
        start_date_1m_str = one_month_ago_dt.strftime('%Y-%m-%d')
        dividends_index = pd.to_datetime([start_date_1m_str])
        dividends_data = [1.0]
        dividends_series = pd.Series(dividends_data, index=dividends_index)
        mock_ticker_instance.dividends = dividends_series

        # 2. Mock yf.download
        # Create a DatetimeIndex for the downloaded data
        two_months_ago_dt = datetime.now() - timedelta(days=60)
        one_month_ago_dt = datetime.now() - timedelta(days=30)
        index_2m = pd.to_datetime([two_months_ago_dt.strftime('%Y-%m-%d')])
        index_1m = pd.to_datetime([one_month_ago_dt.strftime('%Y-%m-%d')])

        # Create separate dataframes for 2m and 1m history to be safe
        download_data_2m = {'Close': [90.0]}
        download_df_2m = pd.DataFrame(download_data_2m, index=index_2m)

        # yf.download is called once, but we need to simulate the slicing
        # that happens inside the function. So we'll make the mock smart.
        # The function slices the 2-month data to get the 1-month data.
        # Let's create a combined dataframe for the mock to return.
        combined_index = index_2m.union(index_1m)
        combined_data = {'Close': [90.0, 95.0]}
        combined_df = pd.DataFrame(combined_data, index=combined_index)
        mock_download.return_value = combined_df

        # --- Call the function ---
        symbol = "TEST"
        result = calculate_etf_data(symbol)

        # --- Assertions ---
        self.assertNotIn("error", result)

        # current_price is the last from history()
        self.assertAlmostEqual(result["current_price"], 105.0)

        # price_1m_ago is the first from the sliced 1-month data
        # price_2m_ago is the first from the 2-month data
        price_1m_ago = 95.0
        price_2m_ago = 90.0
        dividends_1m = 1.0
        dividends_2m = 1.0 # Since it's within the last 2 months
        current_price = 105.0

        expected_1m_return = ((current_price - price_1m_ago + dividends_1m) / price_1m_ago) * 100
        # ((105 - 95 + 1) / 95) * 100 = (11 / 95) * 100 = 11.5789...
        self.assertAlmostEqual(result["one_month_return"], expected_1m_return)

        expected_2m_return = ((current_price - price_2m_ago + dividends_2m) / price_2m_ago) * 100
        # ((105 - 90 + 1) / 90) * 100 = (16 / 90) * 100 = 17.7777...
        self.assertAlmostEqual(result["two_month_return"], expected_2m_return)

if __name__ == '__main__':
    unittest.main()
