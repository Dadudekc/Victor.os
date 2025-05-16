import logging
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp  # Ensure aiohttp is imported for async tests
import pandas as pd
import pytest

from basicbot.data_fetcher import DataFetcher


# Fixture: Create a dummy logger for testing.
@pytest.fixture
def dummy_logger():
    logger = logging.getLogger("test_data_fetcher")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # Clear existing handlers.
    return logger


# Fixture: Create a DataFetcher instance with overridden API and NEWS_API_KEY.
@pytest.fixture
def data_fetcher(dummy_logger):
    df = DataFetcher(logger=dummy_logger)
    # Override the alpaca_api with a MagicMock so that tests can define its behavior.
    df.alpaca_api = MagicMock()
    # Set a dummy NewsAPI key so that news fetching is enabled in tests.
    df.news_api_key = "dummy_api_key"
    return df


### --------------------------
# Test: Historical Data Retrieval
### --------------------------
def test_get_historical_data(data_fetcher):
    """Ensure historical stock data is fetched correctly."""
    # Create a dummy DataFrame with a DatetimeIndex.
    dates = pd.date_range(start="2024-01-01", periods=5, freq="D", tz="UTC")
    dummy_df = pd.DataFrame(
        {
            "open": [100, 102, 103, 105, 107],
            "high": [105, 107, 108, 110, 112],
            "low": [99, 101, 102, 104, 106],
            "close": [104, 106, 107, 109, 111],
            "volume": [1000, 1100, 1050, 1200, 1150],
        },
        index=dates,
    )
    data_fetcher.alpaca_api.get_bars.return_value.df = dummy_df

    data = data_fetcher.get_historical_data("TSLA", "5Min")
    # Expect a non-None DataFrame with the dummy data and with index converted to America/New_York.
    assert data is not None, "Expected non-None DataFrame"
    assert isinstance(data, pd.DataFrame)
    assert "open" in data.columns
    # Verify index timezone conversion:
    assert data.index.tz is not None
    assert data.index.tz.zone == "America/New_York"


### --------------------------
# Test: Latest Quote Retrieval (normal)
### --------------------------
def test_get_latest_quote(data_fetcher):
    """Ensure latest quote is fetched correctly."""
    # Simulate get_last_quote with askprice present.
    mock_quote = MagicMock(bidprice=150.5, askprice=151.0)
    data_fetcher.alpaca_api.get_last_quote.return_value = mock_quote

    quote = data_fetcher.get_latest_quote("TSLA")
    assert quote is not None, "Expected a valid quote dictionary"
    assert isinstance(quote, dict)
    assert quote["bid"] == 150.5
    assert quote["ask"] == 151.0
    # Ask price takes priority.
    assert quote["last_price"] == 151.0


### --------------------------
# Test: Latest Quote Retrieval (no ask price)
### --------------------------
def test_get_latest_quote_no_ask(data_fetcher):
    """Ensure latest quote falls back to bid price when ask price is missing."""
    mock_quote = MagicMock(bidprice=150.5, askprice=None)
    data_fetcher.alpaca_api.get_last_quote.return_value = mock_quote

    quote = data_fetcher.get_latest_quote("TSLA")
    assert (
        quote is not None
    ), "Expected a valid quote dictionary even if askprice is missing"
    assert quote["last_price"] == 150.5  # Should use bid price


### --------------------------
# Test: Fetch Financial News Data (Async, success)
### --------------------------
@pytest.mark.asyncio
@patch("basicbot.data_fetcher.aiohttp.ClientSession.get")
async def test_fetch_news_data(mock_get, data_fetcher):
    """Ensure news data is fetched correctly."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "articles": [
            {
                "title": "Tesla stock surges",
                "source": {"name": "CNBC"},
                "publishedAt": "2024-02-25",
                "url": "http://example.com/tesla1",
            },
            {
                "title": "Tesla announces new model",
                "source": {"name": "Reuters"},
                "publishedAt": "2024-02-24",
                "url": "http://example.com/tesla2",
            },
        ]
    }
    mock_get.return_value.__aenter__.return_value = mock_response

    async with aiohttp.ClientSession() as session:
        news_df = await data_fetcher.fetch_news_data("TSLA", session, page_size=2)

    assert not news_df.empty, "Expected non-empty DataFrame for news data"
    assert "headline" in news_df.columns
    assert len(news_df) == 2


### --------------------------
# Test: Fetch Multiple News (Async)
### --------------------------
@pytest.mark.asyncio
@patch("basicbot.data_fetcher.DataFetcher.fetch_news_data", new_callable=AsyncMock)
async def test_fetch_multiple_news(mock_fetch_news, data_fetcher):
    """Ensure multiple news fetch works correctly."""

    def side_effect(ticker, session, page_size):
        return pd.DataFrame(
            [
                {
                    "symbol": ticker,
                    "headline": f"News for {ticker}",
                    "source": "Reuters",
                    "published_at": "2024-02-25",
                    "url": f"http://example.com/{ticker}",
                }
            ]
        )

    mock_fetch_news.side_effect = side_effect

    results = await data_fetcher.fetch_multiple_news(["TSLA", "AAPL"], page_size=1)
    for ticker in ["TSLA", "AAPL"]:
        assert ticker in results
        df = results[ticker]
        assert not df.empty, f"Expected non-empty DataFrame for {ticker}"
        assert df.iloc[0]["symbol"] == ticker


### --------------------------
# Test: Fetch News API Failure (Async)
### --------------------------
@pytest.mark.asyncio
@patch("basicbot.data_fetcher.aiohttp.ClientSession.get")
async def test_fetch_news_api_failure(mock_get, data_fetcher):
    """Ensure failure handling when NewsAPI fails."""
    mock_response = AsyncMock()
    mock_response.status = 500  # Simulate API failure
    mock_get.return_value.__aenter__.return_value = mock_response

    async with aiohttp.ClientSession() as session:
        news_df = await data_fetcher.fetch_news_data("TSLA", session)
    assert news_df.empty, "Expected empty DataFrame when NewsAPI fails"


### --------------------------
# Test: Fetch News Rate Limit (Async)
### --------------------------
@pytest.mark.asyncio
@patch("basicbot.data_fetcher.aiohttp.ClientSession.get")
async def test_fetch_news_rate_limit(mock_get, data_fetcher):
    """Ensure rate limit handling in NewsAPI."""
    mock_response = AsyncMock()
    mock_response.status = 429  # Too Many Requests
    mock_get.return_value.__aenter__.return_value = mock_response

    async with aiohttp.ClientSession() as session:
        news_df = await data_fetcher.fetch_news_data("TSLA", session)
    assert news_df.empty, "Expected empty DataFrame when rate limited"
