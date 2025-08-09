from flask import Flask, jsonify, render_template
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import sys

app = Flask(__name__)

ETFS = ["COYY", "TSYY", "NVYY", "COII", "COIW", "ULTY", "MSII", "XBTY", "MST", "USOY", "HOOW", "YETH", "NVDW", "TSLW", "PLTW", "LFGY"]
ETFS = sorted(list(set(ETFS)))

def log_message(message):
    """Prints a message to stderr."""
    print(message, file=sys.stderr)
    sys.stderr.flush()

def calculate_etf_data(symbol):
    """
    Fetches and calculates data for a given ETF symbol using yfinance.
    """
    try:
        log_message(f"--- Processing {symbol} ---")
        ticker = yf.Ticker(symbol)

        # Get current price
        hist = ticker.history(period="5d")
        if hist.empty:
            log_message(f"ERROR: Could not get current price for {symbol}")
            return {"error": "Could not get current price."}
        # Use .iloc for position-based access to avoid FutureWarning
        current_price = hist['Close'].iloc[-1]
        log_message(f"Current price for {symbol}: {current_price}")

        # Get historical data
        two_months_ago = datetime.now() - timedelta(days=60)
        one_month_ago = datetime.now() - timedelta(days=30)

        start_date_2m = two_months_ago.strftime('%Y-%m-%d')
        start_date_1m = one_month_ago.strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        hist_2m = yf.download(symbol, start=start_date_2m, end=end_date, progress=False, auto_adjust=True)
        if hist_2m.empty:
            log_message(f"ERROR: Could not get 2-month historical data for {symbol}")
            return {"error": "Could not get 2-month historical data."}

        price_2m_ago = hist_2m['Close'].iloc[0]
        log_message(f"Price 2 months ago for {symbol}: {price_2m_ago}")

        hist_1m = hist_2m.loc[hist_2m.index >= start_date_1m]
        if hist_1m.empty:
            log_message(f"ERROR: Could not get 1-month historical data for {symbol}")
            return {"error": "Could not get 1-month historical data."}
        price_1m_ago = hist_1m['Close'].iloc[0]
        log_message(f"Price 1 month ago for {symbol}: {price_1m_ago}")

        # Get dividends
        dividends = ticker.dividends
        if dividends is not None and not dividends.empty:
            dividends_1m = dividends.loc[start_date_1m:end_date].sum()
            dividends_2m = dividends.loc[start_date_2m:end_date].sum()
        else:
            dividends_1m = 0
            dividends_2m = 0
        log_message(f"Dividends for {symbol}: 1m={dividends_1m}, 2m={dividends_2m}")

        # Calculate total return
        one_month_return = ((current_price - price_1m_ago + dividends_1m) / price_1m_ago) * 100
        two_month_return = ((current_price - price_2m_ago + dividends_2m) / price_2m_ago) * 100

        log_message(f"Successfully processed {symbol}")
        return {
            "current_price": current_price,
            "one_month_return": one_month_return,
            "two_month_return": two_month_return,
        }
    except Exception as e:
        log_message(f"ERROR: An exception occurred while fetching data for {symbol}: {e}")
        return {"error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/etfs")
def etf_data():
    log_message("Request received for /api/etfs")
    all_etf_data = {}
    for symbol in ETFS:
        data = calculate_etf_data(symbol)
        all_etf_data[symbol] = data
    log_message("Finished processing all ETFs")
    return jsonify(all_etf_data)

if __name__ == "__main__":
    log_message("Starting Flask server")
    app.run(host="0.0.0.0", port=5001)
