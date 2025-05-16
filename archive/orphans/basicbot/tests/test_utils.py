"""
-- D:\\TradingRobotPlug\\basicbot\\tests\\test_utils.py --

Description:
------------
This script tests utility functions from `trading_utils.py`. It includes:
- ✅ Timestamp validation
- ✅ Historical data fetching tests (mocked API calls)
- ✅ API retry logic validation
- ✅ Position sizing calculations
- ✅ Retry decorator testing

Dependencies:
-------------
- `pytest` for testing framework.
- `unittest.mock` for API mocking.
- `pandas` for data handling.
"""

from unittest.mock import MagicMock, patch

import pandas as pd

from basicbot.utils import (
    calculate_position_size,
    get_historical_data,
    get_timestamp,
    retry_api_call,
    retry_request,
)


# ✅ TEST: Timestamp Function
def test_get_timestamp():
    """Ensure timestamp format is correct."""
    timestamp = get_timestamp()
    assert isinstance(timestamp, str)
    assert len(timestamp) == 19  # Format: YYYY-MM-DD HH:MM:SS


# ✅ TEST: Historical Data Retrieval
@patch("basicbot.utils.api.get_bars")
def test_get_historical_data(mock_get_bars):
    """Test fetching historical stock data with valid API response."""
    mock_df = pd.DataFrame({"open": [100], "close": [110], "high": [115], "low": [95]})
    mock_get_bars.return_value.df = mock_df

    result = get_historical_data("TSLA", "5Min", 10)
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert "open" in result.columns


@patch("basicbot.utils.api.get_bars")
def test_get_historical_data_empty(mock_get_bars):
    """Test case where API returns empty data."""
    mock_get_bars.return_value.df = pd.DataFrame()

    result = get_historical_data("INVALID", "5Min", 10)
    assert result is None  # Should return None for no data


@patch("basicbot.utils.api.get_bars")
def test_get_historical_data_api_error(mock_get_bars):
    """Test handling of API errors when Alpaca API fails."""
    mock_get_bars.side_effect = Exception("API error")  # Force an API error

    result = get_historical_data("TSLA", "5Min", 10)

    assert result is None  # Should return None when API fails


# ✅ TEST: Retry Logic
@patch("time.sleep", return_value=None)
def test_retry_api_call(mock_sleep):
    """Test API retry logic when the function eventually succeeds."""
    mock_func = MagicMock(
        side_effect=[Exception("Fail 1"), Exception("Fail 2"), 42]
    )  # Succeed on 3rd try

    result = retry_api_call(mock_func, max_retries=3)
    assert result == 42  # Final call should succeed

    assert mock_func.call_count == 3  # Should retry 3 times
    assert mock_sleep.call_count == 2  # Should sleep twice before success


@patch("time.sleep", return_value=None)
def test_retry_api_call_fail(mock_sleep):
    """Test retry logic when all attempts fail."""
    mock_func = MagicMock(side_effect=Exception("Permanent Failure"))

    result = retry_api_call(mock_func, max_retries=3)
    assert result is None  # Should return None after max retries
    assert mock_func.call_count == 3  # Should retry 3 times


# ✅ TEST: Position Sizing
def test_calculate_position_size():
    """Test position size calculation."""
    balance = 10000
    risk_percent = 2  # 2% risk
    stop_loss_pct = 0.05  # 5% stop-loss

    position_size = calculate_position_size(balance, risk_percent, stop_loss_pct)
    assert position_size == 4000  # (10000 * 0.02) / 0.05


def test_calculate_position_size_zero_stop_loss():
    """Test position size when stop loss is zero."""
    balance = 10000
    risk_percent = 2
    stop_loss_pct = 0

    position_size = calculate_position_size(balance, risk_percent, stop_loss_pct)
    assert position_size == 0  # Should return zero


# ✅ TEST: Retry Decorator
@patch("time.sleep", return_value=None)
def test_retry_request(mock_sleep):
    """Test retry decorator works correctly."""

    @retry_request(max_retries=3)
    def flaky_function():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise Exception("Temporary failure")
        return "Success"

    attempt = 0
    result = flaky_function()
    assert result == "Success"
    assert attempt == 3  # Should succeed on the 3rd attempt
