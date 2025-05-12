"""
File: config.py
Path: D:/YourProject/src/config.py

Description:
------------
Handles centralized configuration for the trading system.
It reads environment variables dynamically (with .env support) to allow test overrides,
and exposes both API credentials and trading parameters as properties.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL")

# Trading Settings
STARTING_CASH = 10000
COMMISSION_RATE = 0.001
SMA_PERIOD = 14
SYMBOL = "TSLA"
TIMEFRAMES = ["5Min", "15Min", "30Min", "1H"]
DATA_LIMIT = 6000


class Config:
    """Centralized configuration handler for the trading system. Reads values dynamically from environment variables."""

    @staticmethod
    def get_env(key: str, default=None, cast_type=None):
        """Helper to retrieve environment variables with optional type conversion."""
        value = os.getenv(key, default)
        return cast_type(value) if cast_type and value is not None else value

    # Alpaca API Credentials
    @property
    def ALPACA_API_KEY(self):
        return self.get_env("ALPACA_API_KEY")

    @property
    def ALPACA_SECRET_KEY(self):
        return self.get_env("ALPACA_SECRET_KEY")

    @property
    def ALPACA_BASE_URL(self):
        return self.get_env("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    # Logging & Debugging
    @property
    def DEBUG_MODE(self):
        return self.get_env("DEBUG_MODE", "false").lower() == "true"

    @property
    def LOG_FILE(self):
        return self.get_env("LOG_FILE", None)

    @property
    def LOG_LEVEL(self):
        return self.get_env("LOG_LEVEL", "INFO")

    # Trading Parameters
    @property
    def SYMBOL(self):
        return self.get_env("SYMBOL", "TSLA")

    @property
    def TIMEFRAME(self):
        return self.get_env("TIMEFRAME", "5Min")

    @property
    def LOOKBACK_DAYS(self):
        return self.get_env("LOOKBACK_DAYS", 10, int)

    @property
    def DATA_LIMIT(self):
        return self.get_env("DATA_LIMIT", 1000, int)

    @property
    def RISK_PERCENT(self):
        return self.get_env("RISK_PERCENT", 0.5, float)

    @property
    def STOP_LOSS_PCT(self):
        return self.get_env("STOP_LOSS_PCT", 0.05, float)

    @property
    def TAKE_PROFIT_PCT(self):
        return self.get_env("TAKE_PROFIT_PCT", 0.1, float)

    @property
    def PROFIT_TARGET(self):
        return self.get_env("PROFIT_TARGET", 15, float)

    # Backtesting Configuration
    @property
    def BACKTEST_START_DATE(self):
        return self.get_env("BACKTEST_START_DATE", "2023-01-01")

    @property
    def BACKTEST_END_DATE(self):
        return self.get_env("BACKTEST_END_DATE", "2023-12-31")

    # Execution Mode
    @property
    def TRADING_MODE(self):
        return self.get_env("TRADING_MODE", "backtest")

    def validate(self):
        """Ensure critical configurations are properly set."""
        required_keys = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"]
        missing_keys = [key for key in required_keys if not getattr(self, key)]
        if missing_keys:
            raise ValueError(f"🚨 Missing required config values: {', '.join(missing_keys)}")


# Singleton instance for consistent configuration usage
config = Config()

# Validate configuration at runtime
config.validate()
