"""
-- D:\\TradingRobotPlug\\basicbot\\tests\\test_config.py --

Description:
------------
Unit tests for the `config.py` module.
Ensures that dynamic environment variable overrides work correctly in tests.

"""

import os
from unittest.mock import patch

import pytest

from basicbot.config import Config


@pytest.fixture
def dynamic_config():
    """Fixture to reload the Config instance dynamically for each test."""
    return Config()


### ✅ TEST: Required Configuration Values ###
def test_config_validation(dynamic_config):
    """Ensure required API credentials are present in the configuration."""
    with patch.dict(
        os.environ, {"ALPACA_API_KEY": "test_key", "ALPACA_SECRET_KEY": "test_secret"}
    ):
        dynamic_config.validate()  # Should not raise errors


def test_config_validation_missing_keys(dynamic_config):
    """Ensure missing API credentials trigger a ValueError."""
    with patch.dict(os.environ, {"ALPACA_API_KEY": "", "ALPACA_SECRET_KEY": ""}):
        with pytest.raises(
            ValueError,
            match="Missing required config values: ALPACA_API_KEY, ALPACA_SECRET_KEY",
        ):
            dynamic_config.validate()


### ✅ TEST: Logging Configuration ###
def test_logging_config(dynamic_config):
    """Ensure logging configurations are correctly set from environment variables."""
    with patch.dict(
        os.environ,
        {"LOG_LEVEL": "DEBUG", "DEBUG_MODE": "true", "LOG_FILE": "/tmp/test.log"},
    ):
        assert dynamic_config.LOG_LEVEL == "DEBUG"
        assert dynamic_config.DEBUG_MODE is True
        assert dynamic_config.LOG_FILE == "/tmp/test.log"


### ✅ TEST: Trading Parameters ###
def test_trading_parameters(dynamic_config):
    """Ensure trading parameters are loaded with correct defaults."""
    with patch.dict(
        os.environ,
        {
            "SYMBOL": "AAPL",
            "TIMEFRAME": "1Hour",
            "LOOKBACK_DAYS": "20",
            "DATA_LIMIT": "500",
            "RISK_PERCENT": "1.0",
            "STOP_LOSS_PCT": "0.02",
            "TAKE_PROFIT_PCT": "0.05",
            "PROFIT_TARGET": "25",
        },
    ):
        assert dynamic_config.SYMBOL == "AAPL"
        assert dynamic_config.TIMEFRAME == "1Hour"
        assert dynamic_config.LOOKBACK_DAYS == 20
        assert dynamic_config.DATA_LIMIT == 500
        assert dynamic_config.RISK_PERCENT == 1.0
        assert dynamic_config.STOP_LOSS_PCT == 0.02
        assert dynamic_config.TAKE_PROFIT_PCT == 0.05
        assert dynamic_config.PROFIT_TARGET == 25


### ✅ TEST: Backtesting Configuration ###
def test_backtesting_config(dynamic_config):
    """Ensure backtesting date range is loaded correctly."""
    with patch.dict(
        os.environ,
        {"BACKTEST_START_DATE": "2022-01-01", "BACKTEST_END_DATE": "2022-12-31"},
    ):
        assert dynamic_config.BACKTEST_START_DATE == "2022-01-01"
        assert dynamic_config.BACKTEST_END_DATE == "2022-12-31"


### ✅ TEST: Execution Mode ###
def test_execution_mode(dynamic_config):
    """Ensure trading mode is correctly read from the environment."""
    with patch.dict(os.environ, {"TRADING_MODE": "backtest"}):
        assert dynamic_config.TRADING_MODE == "backtest"

    with patch.dict(os.environ, {"TRADING_MODE": "live"}):
        assert dynamic_config.TRADING_MODE == "live"
