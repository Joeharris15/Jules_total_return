
import unittest
from unittest.mock import patch, MagicMock
from backend.server import app
import pandas as pd
from datetime import datetime, timedelta

class TestEtfApi(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('backend.server.fetch_all_etfs')
    def test_get_etfs_endpoint(self, mock_fetch_all_etfs):
        # Mock the data returned by fetch_all_etfs
        mock_data = [
            {'ticker': 'AAA', 'one_month_return': 1.0, 'two_month_return': 2.0, 'three_month_return': 3.0},
            {'ticker': 'BBB', 'one_month_return': 4.0, 'two_month_return': 5.0, 'three_month_return': 6.0},
            {'ticker': 'CCC', 'one_month_return': 7.0, 'two_month_return': 8.0, 'three_month_return': 9.0},
        ]
        mock_fetch_all_etfs.return_value = mock_data

        # Make a request to the /api/etfs endpoint
        response = self.app.get('/api/etfs')
        self.assertEqual(response.status_code, 200)

        # Check if the data is sorted correctly
        data = response.get_json()
        self.assertEqual(data[0]['ticker'], 'CCC')
        self.assertEqual(data[1]['ticker'], 'BBB')
        self.assertEqual(data[2]['ticker'], 'AAA')

    @patch('backend.server.get_total_return')
    def test_get_etf_details_endpoint(self, mock_get_total_return):
        # Mock the data returned by get_total_return
        mock_get_total_return.return_value = (100.0, 110.0, 5.0, 0.15)

        # Make a request to the /api/etf_details endpoint
        response = self.app.get('/api/etf_details?ticker=TEST&period=1m')
        self.assertEqual(response.status_code, 200)

        # Check the returned data
        data = response.get_json()
        self.assertEqual(data['ticker'], 'TEST')
        self.assertEqual(data['start_price'], 100.0)
        self.assertEqual(data['end_price'], 110.0)
        self.assertEqual(data['total_distributions'], 5.0)
        self.assertEqual(data['total_return_dollars'], 15.0)

    @patch('yfinance.Ticker')
    def test_get_total_return_calculation(self, mock_ticker):
        # Mock the yfinance Ticker object
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        mock_hist = pd.DataFrame({'Close': [100, 110]}, index=[start_date, end_date])
        mock_dividends = pd.Series([5.0], index=[start_date + timedelta(days=15)])

        # Create a mock instance of the Ticker object
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = mock_hist
        mock_ticker_instance.dividends = mock_dividends
        mock_ticker.return_value = mock_ticker_instance

        from backend.server import get_total_return

        start_price, end_price, dividends, total_return = get_total_return('TEST', start_date, end_date)

        self.assertEqual(start_price, 100)
        self.assertEqual(end_price, 110)
        self.assertEqual(dividends, 5.0)
        self.assertAlmostEqual(total_return, 0.15)

if __name__ == '__main__':
    unittest.main()
