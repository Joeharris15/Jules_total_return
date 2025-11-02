from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import logging
import mstarpy as ms

# It's better to use a configured logger than the Flask app's logger directly
logger = logging.getLogger(__name__)

from concurrent.futures import ThreadPoolExecutor, as_completed
from cachetools import TTLCache, cached

# Cache with a TTL of 15 minutes (900 seconds)
# The maxsize parameter is also important for production apps
cache = TTLCache(maxsize=100, ttl=900)

@cached(cache)
def get_all_etf_data(symbols):
    """
    Fetches data for all ETF symbols concurrently using a thread pool.
    """
    all_data = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(calculate_etf_data, symbol): symbol for symbol in symbols}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                all_data[symbol] = data
            except Exception as exc:
                logger.error(f'{symbol} generated an exception: {exc}')
                all_data[symbol] = {"error": str(exc)}
    return all_data

def calculate_etf_data(symbol):
    """
    Fetches and calculates data for a given ETF symbol using yfinance.
    """
    try:
        logger.info(f"--- Processing {symbol} ---")
        ticker = yf.Ticker(symbol)

        # Get current price
        hist = ticker.history(period="5d")
        if hist.empty:
            logger.error(f"Could not get current price for {symbol}")
            return {"error": "Could not get current price."}
        # Use .iloc for position-based access to avoid FutureWarning
        current_price = hist['Close'].iloc[-1].item()
        logger.info(f"Current price for {symbol}: {current_price}")

        # Get historical data
        two_months_ago = datetime.now() - timedelta(days=60)
        one_month_ago = datetime.now() - timedelta(days=30)

        start_date_2m = two_months_ago.strftime('%Y-%m-%d')
        start_date_1m = one_month_ago.strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        hist_2m = yf.download(symbol, start=start_date_2m, end=end_date, progress=False, auto_adjust=True)
        if hist_2m.empty:
            logger.error(f"Could not get 2-month historical data for {symbol}")
            return {"error": "Could not get 2-month historical data."}

        price_2m_ago = hist_2m['Close'].iloc[0].item()
        logger.info(f"Price 2 months ago for {symbol}: {price_2m_ago}")

        hist_1m = hist_2m.loc[hist_2m.index >= start_date_1m]
        if hist_1m.empty:
            logger.error(f"Could not get 1-month historical data for {symbol}")
            return {"error": "Could not get 1-month historical data."}
        price_1m_ago = hist_1m['Close'].iloc[0].item()
        logger.info(f"Price 1 month ago for {symbol}: {price_1m_ago}")

        # Get dividends
        dividends = ticker.dividends
        if dividends is not None and not dividends.empty:
            dividends_1m = float(dividends.loc[start_date_1m:end_date].sum())
            dividends_2m = float(dividends.loc[start_date_2m:end_date].sum())
        else:
            dividends_1m = 0.0
            dividends_2m = 0.0
        logger.info(f"Dividends for {symbol}: 1m={dividends_1m}, 2m={dividends_2m}")

        # Calculate total return
        one_month_return = ((current_price - price_1m_ago + dividends_1m) / price_1m_ago) * 100
        two_month_return = ((current_price - price_2m_ago + dividends_2m) / price_2m_ago) * 100

        logger.info(f"Successfully processed {symbol}")
        return {
            "current_price": current_price,
            "one_month_return": one_month_return,
            "two_month_return": two_month_return,
        }
    except Exception as e:
        logger.error(f"An exception occurred while fetching data for {symbol}: {e}", exc_info=True)
        return {"error": str(e)}

def get_etf_data_with_harris_factor(symbols, period_months):
    """
    Fetches and calculates data for a list of ETF symbols, including the Harris Factor.
    """
    all_data = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(calculate_single_etf_data, symbol, period_months): symbol for symbol in symbols}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                all_data[symbol] = data
            except Exception as exc:
                logger.error(f'{symbol} generated an exception: {exc}')
                all_data[symbol] = {"error": str(exc)}
    return all_data

def calculate_single_etf_data(symbol, period_months):
    """
    Calculates various metrics for a single ETF, including the Harris Factor.
    """
    try:
        logger.info(f"--- Processing {symbol} for a {period_months}-month period ---")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30 * period_months)

        # yfinance ticker
        ticker = yf.Ticker(symbol)

        # mstarpy funds
        funds = ms.Funds(symbol)

        # NAV Return
        nav_history = funds.nav(start_date, end_date)
        if not nav_history or len(nav_history) < 2:
            raise ValueError("Could not get sufficient NAV history.")

        start_nav = nav_history[0]['nav']
        end_nav = nav_history[-1]['nav']
        nav_return = ((end_nav - start_nav) / start_nav) * 100 if start_nav != 0 else 0

        # Distribution Return
        dividends = ticker.dividends
        dividends_in_period = dividends.loc[start_date.strftime('%Y-%m-%d'):end_date.strftime('%Y-%m-%d')].sum()

        hist = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        if hist.empty:
            raise ValueError("Could not get price history.")

        start_price = hist['Close'].iloc[0]
        distribution_return = (dividends_in_period / start_price) * 100 if start_price != 0 else 0

        # Underlying Return
        # This is an approximation based on the top 10 holdings.
        holdings = funds.holdings()
        if holdings.empty:
            raise ValueError("Could not get holdings data.")

        underlying_return = 0
        total_weight = 0

        # Limit to top 10 holdings to avoid excessive API calls
        for _, row in holdings.head(10).iterrows():
            holding_symbol = row['ticker']
            weight = row['weighting']

            try:
                holding_hist = yf.Ticker(holding_symbol).history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
                if not holding_hist.empty and len(holding_hist['Close']) > 1:
                    holding_start_price = holding_hist['Close'].iloc[0]
                    holding_end_price = holding_hist['Close'].iloc[-1]
                    holding_return = ((holding_end_price - holding_start_price) / holding_start_price)
                    underlying_return += holding_return * weight
                    total_weight += weight
            except Exception as e:
                logger.warning(f"Could not process holding {holding_symbol} for {symbol}: {e}")

        if total_weight > 0:
            underlying_return = (underlying_return / total_weight) * 100
        else:
            underlying_return = 0

        # Total Return
        end_price = hist['Close'].iloc[-1]
        total_return = ((end_price - start_price + dividends_in_period) / start_price) * 100 if start_price != 0 else 0

        # Harris Factor
        # Harris Factor is nav return divided by underlying return times distribution return, times 1 minus the return of capital percentage. Multiply results by 100
        # ROC is unavailable, so it will be omitted.
        if underlying_return != 0:
            harris_factor = (nav_return / underlying_return) * distribution_return * 100
        else:
            harris_factor = 0

        return {
            "ticker": symbol,
            "nav_return": nav_return,
            "underlying_return": underlying_return,
            "distribution_return": distribution_return,
            "total_return": total_return,
            "harris_factor": harris_factor,
            "return_of_capital_percentage": "N/A"
        }
    except Exception as e:
        logger.error(f"An exception occurred while calculating data for {symbol}: {e}", exc_info=True)
        return {"error": str(e)}