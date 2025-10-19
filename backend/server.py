
import genkit
import yfinance as yf
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
from cachetools import cached, TTLCache
import concurrent.futures
import threading

# Initialize Flask app
app = Flask(__name__)

# Define the list of ETF tickers
ETF_TICKERS = [
    "AAPW", "AZYY", "BCCC", "BRKW", "CHAT", "GMEY", "HIMY", "HIYY", "HUMN", "JEDI", "MEME", "MRNY",
    "MSDD", "MSTP", "NOWL", "PLYY", "QQQI", "TDAQ", "TSYY", "ULTY", "VSTL", "WILD", "YBTC", "AMDW",
    "PLTW", "CHPY", "QQQY", "EGGY", "WDTE", "JEPQ", "CVNY", "NFLW", "IWMY", "YMAG", "SCHD", "ICOI",
    "AMDU", "AMDY", "IMRA", "COIW", "SMCC", "CONY", "COYY", "HOOW", "IMST", "NVYY", "WNTR", "AVGW",
    "HOOY", "MARO", "LFGY", "PLTY", "MSTY", "MSTW", "BLOX", "XBTY", "NVDW", "NVDY", "COII", "SNOY",
    "TSLW", "MST", "CEPI", "FIAT", "YETH", "BETE", "CRSH", "YMAX", "IGME", "GPTY", "GOOW", "AMYY",
    "NVII", "USOY", "RDTY", "MSFW", "AMZW", "RDTE", "TQQY", "YBIT", "DIPS", "BTCI", "YSPY", "HOOI",
    "METW", "MAGY", "SOXY", "QDTE", "TSII", "QDTY", "XDTE", "WPAY", "XPAY", "MSII", "SDTY", "SVOL",
    "SPYT", "SPYI", "BIGY", "MSFY", "TSPY", "JEPI", "WEEK", "SLTY", "RNTY", "PLT", "VTI", "VOO",
    "SSK", "MTYY", "RDYY"
]

# Configure caching with a 15-minute TTL
cache = TTLCache(maxsize=100, ttl=900)
lock = threading.Lock()

def get_total_return(ticker, start_date, end_date):
    """
    Calculates the total return of a ticker between two dates.
    """
    stock = yf.Ticker(ticker)
    hist = stock.history(start=start_date, end=end_date)

    if hist.empty:
        return 0, 0, 0, 0  # Return zeros if no data

    start_price = hist['Close'].iloc[0]
    end_price = hist['Close'].iloc[-1]

    dividends = stock.dividends[start_date:end_date].sum()

    total_return = ((end_price + dividends) - start_price) / start_price

    return start_price, end_price, dividends, total_return

@cached(cache, lock=lock)
def get_etf_data(ticker):
    """
    Fetches and calculates the 1, 2, and 3-month total returns for a given ETF ticker.
    """
    today = datetime.now()
    one_month_ago = today - timedelta(days=30)
    two_months_ago = today - timedelta(days=60)
    three_months_ago = today - timedelta(days=90)

    _, _, _, one_month_return = get_total_return(ticker, one_month_ago, today)
    _, _, _, two_month_return = get_total_return(ticker, two_months_ago, today)
    _, _, _, three_month_return = get_total_return(ticker, three_months_ago, today)

    return {
        'ticker': ticker,
        'one_month_return': round(one_month_return * 100, 2),
        'two_month_return': round(two_month_return * 100, 2),
        'three_month_return': round(three_month_return * 100, 2),
    }

def fetch_all_etfs(tickers):
    """
    Fetches data for all ETFs concurrently.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(get_etf_data, tickers))
    return results

@app.route('/api/etfs', methods=['GET'])
def get_etfs():
    """
    API endpoint to get ETF data, sorted by 3-month total return.
    """
    etf_data = fetch_all_etfs(ETF_TICKERS)

    # Filter out ETFs with no data
    etf_data = [data for data in etf_data if data['three_month_return'] != 0]

    # Sort by 3-month total return in descending order
    sorted_data = sorted(etf_data, key=lambda x: x['three_month_return'], reverse=True)

    return jsonify(sorted_data)

@app.route('/api/etf_details', methods=['GET'])
def get_etf_details():
    """
    API endpoint for detailed ETF information.
    """
    ticker = request.args.get('ticker')
    period = request.args.get('period')

    if not ticker or not period:
        return jsonify({'error': 'Ticker and period are required'}), 400

    today = datetime.now()
    if period == '1m':
        start_date = today - timedelta(days=30)
    elif period == '2m':
        start_date = today - timedelta(days=60)
    elif period == '3m':
        start_date = today - timedelta(days=90)
    else:
        return jsonify({'error': 'Invalid period specified'}), 400

    start_price, end_price, dividends, total_return = get_total_return(ticker, start_date, today)

    return jsonify({
        'ticker': ticker,
        'start_price': round(start_price, 2),
        'end_price': round(end_price, 2),
        'total_distributions': round(dividends, 2),
        'total_return_dollars': round((end_price + dividends) - start_price, 2)
    })

if __name__ == '__main__':
    genkit.init()
    app.run(debug=True, port=5001)
