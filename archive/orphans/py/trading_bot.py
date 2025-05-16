#!/usr/bin/env python
"""
tradingbot.py

Description:
------------
This script ties together the TradingAPI, Strategy, and Backtester modules to
create an end‑to‑end trading bot. It supports both live trading and backtesting
modes, as configured in the centralized config.

Dependencies:
-------------
- basicbot.config (for configuration)
- basicbot.logger (for logging)
- basicbot.strategy (for trading strategy logic)
- basicbot.trading_api_alpaca (for Alpaca API integration)
- basicbot.backtester (for backtesting simulation)
- pandas, backtrader, ta, alpaca_trade_api, logging, time, datetime

Usage:
------
Run the script to start trading in the mode specified by config.TRADING_MODE:
- For live trading: orders will be placed via Alpaca.
- For backtesting: historical data is used to simulate the strategy.
"""

import datetime
import sys
import time

import pandas as pd

# Ensure the project root is on sys.path (adjust the path as needed)
sys.path.append(r"D:\TradingRobotPlug")

# Dynamic Import Handling for Config and Logger
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

# ------------------------------------------------------------------------------
# Setup Logger
# ------------------------------------------------------------------------------
logger = setup_logging("tradingbot")


# ------------------------------------------------------------------------------
# Live Trading Function
# ------------------------------------------------------------------------------
def run_live_trading():
    """
    Runs live trading using the TradingAPI and the Strategy.
    Periodically fetches recent historical data, calculates indicators,
    evaluates signals, and places orders accordingly.
    """
    logger.info("🚀 Starting Live Trading Mode...")

    # Initialize Trading API and Strategy
    trading_api = TradingAPI()
    strat = Strategy(symbol=config.SYMBOL, timeframe=config.TIMEFRAME)

    while True:
        try:
            # Fetch recent market data (using a 60-minute lookback window)
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(minutes=60)
            data = trading_api.api.get_bars(
                config.SYMBOL,
                config.TIMEFRAME,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                limit=1000,
                feed="iex",
            ).df

            if data is not None and not data.empty:
                # Calculate indicators and generate latest signal
                data = strat.calculate_indicators(data)
                latest_signal = strat.generate_signals(data).iloc[-1]
                logger.info(f"Latest Signal: {latest_signal}")

                if latest_signal == "BUY":
                    trading_api.place_order(config.SYMBOL, qty=1, side="buy")
                elif latest_signal == "SELL":
                    trading_api.place_order(config.SYMBOL, qty=1, side="sell")
            else:
                logger.warning("⚠️ No market data available.")

            account_info = trading_api.get_account()
            logger.info(f"💰 Account Info: {account_info}")
            time.sleep(60)  # Wait 1 minute between checks
        except KeyboardInterrupt:
            logger.info("🛑 Live trading stopped by user.")
            break
        except Exception as e:
            logger.error(f"❌ Error during live trading: {e}")
            time.sleep(60)

    trading_api.logout()


# ------------------------------------------------------------------------------
# Backtesting Function
# ------------------------------------------------------------------------------
def run_backtest():
    """
    Runs a backtest using historical market data.
    Uses the Backtester class and Backtrader framework.
    """
    logger.info("📊 Starting Backtest Mode...")

    # Initialize Strategy (for backtesting)
    strat = Strategy(symbol=config.SYMBOL, timeframe=config.TIMEFRAME)

    # Use fetch_historical_data() if available; otherwise load sample data from CSV
    if hasattr(strat, "fetch_historical_data"):
        df = strat.fetch_historical_data()
    else:
        logger.warning("No fetch_historical_data method found; using sample CSV data.")
        df = pd.read_csv(
            "historical_data.csv", parse_dates=["timestamp"], index_col="timestamp"
        )

    if df.empty:
        logger.error("❌ Historical data is empty. Aborting backtest.")
        return

    # Initialize Backtester with the strategy and logger
    backtester = Backtester(
        strategy=strat, logger=logger, initial_cash=config.STARTING_CASH
    )
    results = backtester.run_backtest(df)

    logger.info("✅ Backtest Completed.")
    print("\nBacktest Results (tail):")
    print(results.tail())

    # Plot cumulative returns
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12, 6))
        plt.plot(
            results.index,
            results["cumulative_returns"],
            label="Cumulative Returns",
            color="purple",
            linestyle="--",
        )
        plt.xlabel("Date")
        plt.ylabel("Cumulative Return")
        plt.title("Backtest Cumulative Returns")
        plt.legend()
        plt.grid(True)
        plt.show()
    except Exception as e:
        logger.error(f"❌ Plotting failed: {e}")


# ------------------------------------------------------------------------------
# Main Execution: Choose Mode Based on Config
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    mode = (
        config.TRADING_MODE.lower() if hasattr(config, "TRADING_MODE") else "backtest"
    )
    if mode == "live":
        run_live_trading()
    else:
        run_backtest()
