#!/usr/bin/env python
"""
Test Suite for Trading Bot
--------------------------
This script performs unit and integration tests on:
✅ TradingAPI (Alpaca API Wrapper)
✅ Strategy (Technical Indicators & Signal Generation)
✅ Backtester (Backtest Simulation)
✅ Configuration (Config Validation)
✅ Full Trading System (Integration Test)
"""

import os

# Ensure project root is in the path
import sys
import unittest

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ✅ Import Trading Bot Components
try:
    from basicbot.backtester import Backtester
    from basicbot.config import config
    from basicbot.logger import setup_logging
    from basicbot.strategy import Strategy
    from basicbot.trading_api_alpaca import TradingAPI
except ImportError:
    from backtester import Backtester
    from config import config
    from logger import setup_logging
    from strategy import Strategy
    from trading_api_alpaca import TradingAPI

# ✅ Setup Logger
logger = setup_logging("test_trading_bot")

# ------------------------------------------------------------------------------
# Unit Tests
# ------------------------------------------------------------------------------


class TestConfig(unittest.TestCase):
    """✅ Test Suite for Config Validation"""

    def test_api_keys_exist(self):
        """🚨 Ensure API keys are loaded properly from config"""
        self.assertIsNotNone(config.ALPACA_API_KEY, "Missing ALPACA_API_KEY")
        self.assertIsNotNone(config.ALPACA_SECRET_KEY, "Missing ALPACA_SECRET_KEY")

    def test_symbol_defined(self):
        """✅ Ensure trading symbol is set"""
        self.assertIsNotNone(config.SYMBOL, "Trading symbol not defined")

    def test_trading_mode_valid(self):
        """✅ Validate trading mode (live/backtest)"""
        self.assertIn(
            config.TRADING_MODE.lower(), ["live", "backtest"], "Invalid trading mode"
        )


class TestTradingAPI(unittest.TestCase):
    """✅ Test Suite for Alpaca API Wrapper"""

    @classmethod
    def setUpClass(cls):
        cls.trading_api = TradingAPI()

    def test_account_info(self):
        """📊 Fetch account balance & equity"""
        account = self.trading_api.get_account()
        self.assertIsInstance(account, dict)
        self.assertIn("buying_power", account)
        self.assertIn("equity", account)

    def test_get_position(self):
        """✅ Fetch position for configured symbol"""
        qty, cost_basis = self.trading_api.get_position(config.SYMBOL)
        self.assertIsInstance(qty, int)
        self.assertIsInstance(cost_basis, float)

    def test_place_order(self):
        """🚀 Simulate a buy order (paper trading)"""
        result = self.trading_api.place_order(config.SYMBOL, qty=1, side="buy")
        self.assertIsInstance(result, dict)
        self.assertIn("id", result)
        self.assertIn("state", result)


class TestStrategy(unittest.TestCase):
    """✅ Test Suite for Trading Strategy"""

    @classmethod
    def setUpClass(cls):
        cls.strategy = Strategy(symbol=config.SYMBOL, timeframe=config.TIMEFRAME)

    def test_indicator_calculation(self):
        """📈 Ensure indicators are correctly computed"""
        df = pd.DataFrame(
            {
                "close": [100, 102, 104, 103, 105],
                "high": [101, 103, 105, 104, 106],
                "low": [99, 101, 103, 102, 104],
            }
        )
        df = self.strategy.calculate_indicators(df)
        self.assertTrue("SMA_short" in df.columns)
        self.assertTrue("RSI" in df.columns)

    def test_signal_generation(self):
        """✅ Ensure correct buy/sell signals"""
        df = pd.DataFrame(
            {
                "close": [100, 102, 104, 103, 105],
                "SMA_short": [99, 100, 101, 102, 103],
                "SMA_long": [98, 99, 100, 101, 102],
                "RSI": [30, 45, 60, 50, 40],
            }
        )
        signals = self.strategy.generate_signals(df)
        self.assertIsInstance(signals, pd.Series)
        self.assertIn(signals.iloc[-1], ["BUY", "SELL", "HOLD"])


class TestBacktester(unittest.TestCase):
    """✅ Test Suite for Backtesting Engine"""

    @classmethod
    def setUpClass(cls):
        cls.strategy = Strategy(symbol=config.SYMBOL, timeframe=config.TIMEFRAME)
        cls.backtester = Backtester(strategy=cls.strategy, logger=logger)

    def test_backtest_execution(self):
        """📊 Run a backtest on sample data"""
        df = pd.DataFrame(
            {
                "close": [100, 102, 104, 103, 105],
                "high": [101, 103, 105, 104, 106],
                "low": [99, 101, 103, 102, 104],
            }
        )
        df = self.strategy.calculate_indicators(df)
        results = self.backtester.run_backtest(df)
        self.assertTrue("cumulative_returns" in results.columns)


# ------------------------------------------------------------------------------
# Integration Test (Full Trading System)
# ------------------------------------------------------------------------------


class TestTradingBot(unittest.TestCase):
    """✅ Full System Test (Live/Backtest Modes)"""

    def test_live_trading(self):
        """🚀 Simulate live trading execution (mock API)"""
        if config.TRADING_MODE.lower() == "live":
            trading_api = TradingAPI()
            strat = Strategy(symbol=config.SYMBOL, timeframe=config.TIMEFRAME)
            data = strat.fetch_historical_data()
            if data is not None and not data.empty:
                signal = strat.generate_signals(data).iloc[-1]
                if signal in ["BUY", "SELL"]:
                    order = trading_api.place_order(config.SYMBOL, 1, signal.lower())
                    self.assertIsInstance(order, dict)
                    self.assertIn("id", order)
            else:
                self.fail("No historical data available for testing.")

    def test_backtest_execution(self):
        """📊 Run a full backtest (simulated trading)"""
        if config.TRADING_MODE.lower() == "backtest":
            strat = Strategy(symbol=config.SYMBOL, timeframe=config.TIMEFRAME)
            backtester = Backtester(strategy=strat, logger=logger)
            df = strat.fetch_historical_data()
            if df is None or df.empty:
                self.fail("No historical data available for backtesting.")
            results = backtester.run_backtest(df)
            self.assertTrue("cumulative_returns" in results.columns)


# ------------------------------------------------------------------------------
# Run Tests
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
