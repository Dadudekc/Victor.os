import asyncio
import datetime
import logging
import os
import time
from functools import wraps

import aiohttp
import alpaca_trade_api as tradeapi
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ✅ Define Retry Decorator for API Requests
def retry_request(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        delay = 2  # seconds
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except tradeapi.rest.APIError as e:
                logging.error(
                    f"🚨 Alpaca API Error (Attempt {attempt+1}/{max_retries}): {e}"
                )
            except Exception as e:
                logging.error(f"❌ Unexpected error: {e}")
            time.sleep(delay)
        logging.error(f"❌ Failed after {max_retries} attempts: {func.__name__}")
        return None

    return wrapper


class DataFetcher:
    """Handles fetching historical stock data & news from multiple sources."""

    def __init__(self, api=None, logger=None):
        """
        Initialize DataFetcher with market & news data sources.

        - Alpaca for stock market data.
        - NewsAPI for financial news.
        """
        self.logger = logger or logging.getLogger(__name__)

        # ✅ Alpaca API Initialization
        self.alpaca_api = api or tradeapi.REST(
            os.getenv("ALPACA_API_KEY"),
            os.getenv("ALPACA_SECRET_KEY"),
            os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
            api_version="v2",
        )

        # ✅ NewsAPI Initialization
        self.news_api_key = os.getenv("NEWS_API_KEY")
        if not self.news_api_key:
            self.logger.warning(
                "⚠️ NewsAPI key is missing. News features will be disabled."
            )

        self.logger.info("✅ DataFetcher initialized.")

    @retry_request
    def get_historical_data(self, symbol="TSLA", timeframe="5Min", limit=1000):
        """
        Fetches historical stock data from Alpaca.

        :param symbol: Ticker symbol (default: TSLA)
        :param timeframe: Timeframe (default: 5Min)
        :param limit: Number of bars to retrieve (default: 1000)
        :return: DataFrame with historical price data
        """
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=10)

        try:
            bars = self.alpaca_api.get_bars(
                symbol,
                timeframe,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                feed="iex",  # ✅ SWITCHED TO "iex" (Free)
            ).df
        except tradeapi.rest.APIError as e:
            self.logger.error(f"🚨 Alpaca API Error: {e}")
            return None

        if bars.empty:
            self.logger.warning("⚠️ No data returned. Check API keys or symbol.")
            return None

        # ✅ Ensure timestamps are formatted properly
        bars.index = bars.index.tz_convert("America/New_York")
        return bars

    @retry_request
    def get_latest_quote(self, symbol="TSLA"):
        """
        Fetches the latest price quote for a given symbol.

        :param symbol: Ticker symbol (default: TSLA)
        :return: Latest price data or None if API fails
        """
        try:
            quote = self.alpaca_api.get_last_quote(symbol)
            last_price = quote.askprice if quote.askprice else quote.bidprice
            return {
                "symbol": symbol,
                "bid": quote.bidprice,
                "ask": quote.askprice,
                "last_price": last_price,
            }
        except tradeapi.rest.APIError as e:
            self.logger.error(f"🚨 Failed to fetch latest quote: {e}")
            return None

    async def fetch_news_data(
        self, ticker: str, session: aiohttp.ClientSession, page_size: int = 5
    ):
        """
        Fetches financial news related to the given ticker from NewsAPI.

        :param ticker: Stock ticker symbol (e.g., TSLA)
        :param session: aiohttp ClientSession
        :param page_size: Number of news articles to fetch
        :return: DataFrame containing news headlines & sentiment scores
        """
        if not self.news_api_key:
            self.logger.warning("⚠️ NewsAPI is not configured. Skipping news fetch.")
            return pd.DataFrame()

        url = f"https://newsapi.org/v2/everything?q={ticker}&language=en&pageSize={page_size}&apiKey={self.news_api_key}"
        retries = 3
        for attempt in range(retries):
            try:
                async with session.get(url) as response:
                    if response.status == 429:  # Too Many Requests
                        self.logger.warning(
                            "⚠️ NewsAPI Rate Limit Hit. Retrying in 5 sec..."
                        )
                        await asyncio.sleep(5)
                        continue
                    if response.status != 200:
                        self.logger.error(f"❌ NewsAPI error: {response.status}")
                        return pd.DataFrame()

                    news_json = await response.json()
                    articles = news_json.get("articles", [])
                    if not articles:
                        self.logger.warning(f"⚠️ No news found for {ticker}.")
                        return pd.DataFrame()

                    return pd.DataFrame(
                        [
                            {
                                "symbol": ticker,
                                "headline": article["title"],
                                "source": article["source"]["name"],
                                "published_at": article["publishedAt"],
                                "url": article["url"],
                            }
                            for article in articles
                        ]
                    )
            except Exception as e:
                self.logger.error(f"🚨 Error fetching news for {ticker}: {e}")

        return pd.DataFrame()

    async def fetch_multiple_news(self, tickers: list, page_size: int = 5):
        """
        Fetches news for multiple stocks concurrently.

        :param tickers: List of stock ticker symbols
        :param page_size: Number of articles per stock
        :return: Dictionary of DataFrames containing news per ticker
        """
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.fetch_news_data(ticker, session, page_size) for ticker in tickers
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return {tickers[i]: results[i] for i in range(len(tickers))}
