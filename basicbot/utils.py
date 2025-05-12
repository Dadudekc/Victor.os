import time
import datetime
import pandas as pd
import alpaca_trade_api as tradeapi
import functools
from basicbot.logger import setup_logging  # ✅ Import logger
from basicbot.config import config  # ✅ Import the singleton instance

# ✅ Initialize logger with script name
logger = setup_logging("utils")

# ✅ Ensure API is initialized once
api = tradeapi.REST(
    config.ALPACA_API_KEY,
    config.ALPACA_SECRET_KEY,
    config.ALPACA_BASE_URL,
    api_version="v2"
)

# ✅ Ensure API credentials are available
if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
    logger.error("🚨 Missing Alpaca API credentials! Check your .env file.")
    raise ValueError("Alpaca API credentials not found!")


def get_timestamp():
    """Returns the current timestamp for logging/trading."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_historical_data(symbol=config.SYMBOL, timeframe=config.TIMEFRAME, days=config.LOOKBACK_DAYS):
    """
    Fetches historical stock data from Alpaca.

    :param symbol: Ticker symbol (default: from config)
    :param timeframe: Timeframe for historical data
    :param days: Number of days to look back
    :return: Pandas DataFrame with price data or None if API call fails
    """

    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days)

    try:
        bars = api.get_bars(
            symbol, timeframe, 
            start=start_date.strftime('%Y-%m-%d'), 
            end=end_date.strftime('%Y-%m-%d'), 
            feed="iex"
        ).df
        if bars.empty:
            logger.warning(f"⚠️ No data for {symbol}. Check API keys or symbol.")
            return None
        return bars
    except Exception as e:  # ✅ Catch all exceptions
        logger.error(f"🚨 Alpaca API Error: {e}")
        return None  # ✅ Ensure it returns None on failure



def retry_api_call(func, max_retries=3, delay=2, *args, **kwargs):
    """
    Retries API calls on failure to handle transient errors.

    :param func: Function to retry
    :param max_retries: Maximum number of retry attempts
    :param delay: Delay in seconds between retries
    :return: Result of function call or None if failed
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"⚠️ API call failed (Attempt {attempt}/{max_retries}): {e}")
            time.sleep(delay)
    logger.error("❌ Max retries reached. API call failed.")
    return None


def calculate_position_size(balance, risk_percent=config.RISK_PERCENT, stop_loss_pct=config.STOP_LOSS_PCT):
    """
    Calculates the position size based on account balance and risk.

    :param balance: Account balance
    :param risk_percent: Percentage of balance to risk
    :param stop_loss_pct: Stop-loss percentage
    :return: Position size
    """
    if stop_loss_pct == 0:
        logger.error("❌ Stop-loss percentage cannot be zero.")
        return 0

    risk_amount = balance * (risk_percent / 100)
    return risk_amount / stop_loss_pct


def retry_request(max_retries=3, delay=2):
    """
    Decorator to retry API requests in case of transient failures.

    :param max_retries: Number of retry attempts
    :param delay: Delay in seconds between retries
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"⚠️ API call failed (Attempt {attempt}/{max_retries}): {e}")
                    time.sleep(delay)
            logger.error("❌ Max retries reached. API call failed.")
            return None
        return wrapper
    return decorator
