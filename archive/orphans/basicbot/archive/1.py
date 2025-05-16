from basicbot.config import Config
from basicbot.utils import get_historical_data, logger

# API Credentials
api = tradeapi.REST(
    Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, Config.BASE_URL, api_version="v2"
)

# Fetch historical data
data = get_historical_data(Config.SYMBOL, Config.TIMEFRAME, Config.LOOKBACK_DAYS)
logger.info(f"📊 Fetched {Config.LOOKBACK_DAYS} days of data for {Config.SYMBOL}")

from basicbot.utils import get_historical_data, logger, retry_api_call

# Example usage
data = get_historical_data("TSLA")
logger.info("📊 Historical Data Retrieved for TSLA")

# Example API call with retry
order = retry_api_call(api.submit_order, symbol="TSLA", qty=1, side="buy")
