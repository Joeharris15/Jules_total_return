import yfinance as yf
from datetime import datetime, timedelta

def simulate_trading(etf_symbols, initial_investment, weeks):
    """
    Simulates a trading strategy of switching between ETFs based on weekly performance.

    :param etf_symbols: A list of ETF symbols to trade.
    :param initial_investment: The starting amount in USD.
    :param weeks: The number of weeks to simulate the trading.
    :return: The final value of the investment after the simulation.
    """
    end_date = datetime.now()
    # Fetch more data to ensure we have enough data points.
    start_date = end_date - timedelta(weeks=weeks + 10)

    data = yf.download(etf_symbols, start=start_date, end=end_date, interval='1wk')['Close']

    # Take the last weeks + 2 data points
    data = data.tail(weeks + 2)

    # We need weeks + 2 data points to run the simulation for the specified number of weeks.
    if data.empty or len(data) < weeks + 2:
        raise ValueError("Not enough historical data to perform the simulation for the given timeframe.")

    account_value = initial_investment
    data = data.reset_index(drop=True)
    for i in range(1, weeks + 1):
        # Determine the best performer from the previous week
        last_week_start = i - 1
        last_week_end = i

        returns = data.iloc[last_week_end] / data.iloc[last_week_start] - 1
        best_performer = returns.idxmax()

        # Calculate this week's return based on the best performer
        current_week_start = i
        current_week_end = i + 1

        best_performer_return = data[best_performer].iloc[current_week_end] / data[best_performer].iloc[current_week_start] - 1

        # Update account value
        account_value *= (1 + best_performer_return)

    return account_value
