import datetime
import time
from functools import wraps

import alpaca_trade_api as tradeapi
import backtrader as bt
import matplotlib
from config import config  # ✅ Your centralized configuration
from logger import setup_logging  # ✅ Your logging setup

matplotlib.use("Agg")  # ✅ Non-GUI backend to avoid Tkinter errors
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------------
# Setup Logging
# ------------------------------------------------------------------------------
logger = setup_logging("backtest")

# ------------------------------------------------------------------------------
# Initialize Alpaca API
# ------------------------------------------------------------------------------
alpaca_api = tradeapi.REST(
    config.ALPACA_API_KEY,
    config.ALPACA_SECRET_KEY,
    config.ALPACA_BASE_URL,
    api_version="v2",
)


# ------------------------------------------------------------------------------
# Retry Decorator for API Requests
# ------------------------------------------------------------------------------
def retry_request(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except tradeapi.rest.APIError as e:
                logger.error(
                    f"🚨 Alpaca API Error (Attempt {attempt+1}/{max_retries}): {e}"
                )
                if "403" in str(e):
                    logger.error(
                        "🚨 Forbidden (403) error! Check API keys & subscription level."
                    )
                    return None
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
            time.sleep(delay)

        logger.error(f"❌ Failed after {max_retries} attempts: {func.__name__}")
        return None

    return wrapper


# ------------------------------------------------------------------------------
# Fetch & Resample Data
# ------------------------------------------------------------------------------
@retry_request
def get_historical_data(symbol="TSLA", timeframe="5Min", limit=6000):
    """Fetch historical stock data from Alpaca (30-day lookback)."""
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)

    try:
        bars = alpaca_api.get_bars(
            symbol,
            timeframe,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            feed="iex",
        ).df
    except tradeapi.rest.APIError as e:
        logger.error(f"🚨 Alpaca API Error: {e}")
        return None

    if bars is None or bars.empty:
        logger.warning(
            f"⚠️ No data returned for {symbol} {timeframe}. Check API keys or symbol."
        )
        return None

    # Convert timezone
    bars.index = bars.index.tz_convert("America/New_York")
    return bars


def resample_data(df, timeframe):
    """Resample data to a higher timeframe (15T, 30T, 1H, etc.)."""
    if df is None:
        logger.warning(f"⚠️ No data to resample for {timeframe}. Skipping...")
        return None
    return (
        df.resample(timeframe)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
    )


# ------------------------------------------------------------------------------
# Hardcoded Timeframes
# ------------------------------------------------------------------------------
TIMEFRAMES = ["5Min", "15Min", "30Min", "1H"]

logger.info("📡 Fetching TSLA data from Alpaca...")
data_feeds = {}

# ------------------------------------------------------------------------------
# Fetch Data for Each Timeframe
# ------------------------------------------------------------------------------
for tf in TIMEFRAMES:
    logger.info(f"Fetching data for {tf}...")
    data_feeds[tf] = get_historical_data("TSLA", tf)

# Ensure we have 5Min data for resampling
if data_feeds.get("5Min") is None:
    raise ValueError(
        "❌ Critical Error: No 5-minute data retrieved. Check API keys and permissions."
    )

# Resample 15Min & 30Min from 5Min
data_feeds["15Min"] = resample_data(data_feeds["5Min"], "15T")
data_feeds["30Min"] = resample_data(data_feeds["5Min"], "30T")

# ------------------------------------------------------------------------------
# Log Data Summary
# ------------------------------------------------------------------------------
for tf, df in data_feeds.items():
    logger.info(f"✅ {tf} Data: {len(df) if df is not None else '⚠️ Skipped'} bars")


# ------------------------------------------------------------------------------
# Backtrader Strategy
# ------------------------------------------------------------------------------
class MultiTFStrategy(bt.Strategy):
    def __init__(self):
        # SimpleMovingAverage on the primary (5Min) data feed
        self.sma = bt.indicators.SimpleMovingAverage(self.datas[0], period=14)

    def next(self):
        dt = self.datas[0].datetime.datetime(0)
        price = self.datas[0].close[0]
        logger.info(f"{dt} - Close Price: {price}")


# ------------------------------------------------------------------------------
# Setup Backtrader Engine
# ------------------------------------------------------------------------------
cerebro = bt.Cerebro()
cerebro.addstrategy(MultiTFStrategy)

# Add 5Min data feed for plotting
if data_feeds["5Min"] is not None:
    cerebro.adddata(bt.feeds.PandasData(dataname=data_feeds["5Min"]))
# Add other timeframes (no plot)
for tf in ["15Min", "30Min", "1H"]:
    if data_feeds[tf] is not None:
        cerebro.adddata(bt.feeds.PandasData(dataname=data_feeds[tf], plot=False))

logger.info("🚀 Starting Backtest...")
cerebro.run()
logger.info("✅ Backtest Completed.")

# ------------------------------------------------------------------------------
# Plot & Save Figure as PNG
# ------------------------------------------------------------------------------
plt.close("all")
figs = cerebro.plot(
    style="candle",
    volume=False,  # ❌ Remove volume subplot
    trade=False,  # ❌ Hide buy/sell markers
    broker=False,  # ❌ Hide broker/cash lines
)

if figs:
    for i, fig_list in enumerate(figs):
        if isinstance(fig_list, list):
            for j, fig in enumerate(fig_list):
                fig.set_size_inches(16, 10)
                fig.subplots_adjust(hspace=0.3)
                filename = f"backtest_plot_{i}_{j}.png"
                fig.savefig(filename, dpi=300)
                logger.info(f"📊 Saved: {filename}")
        else:
            fig_list.set_size_inches(16, 10)
            fig_list.subplots_adjust(hspace=0.3)
            filename = f"backtest_plot_{i}.png"
            fig_list.savefig(filename, dpi=300)
            logger.info(f"📊 Saved: {filename}")
else:
    logger.warning("⚠️ No figures generated. Check if the strategy executed properly.")

logger.info("✅ Backtest plots saved! Check your directory.")
