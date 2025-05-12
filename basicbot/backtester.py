"""
D:\TradingRobotPlug\basicbot\backtester.py

Description:
------------
Implements a **Backtester** class that evaluates trading strategies using
historical data. Supports single or multi-timeframe data, calculates signals,
and computes strategy performance. Integrates seamlessly with a user-defined
strategy that provides indicator calculations and signal logic.

Key Features:
-------------
- Accepts single or multi-timeframe DataFrames (dictionary of DataFrames).
- Calculates trading indicators using the user-provided strategy class.
- Generates BUY/SELL/HOLD signals and maps them to positions.
- Simulates trading execution to compute returns and cumulative performance.
- Logs all major steps using a provided `logger`.
- Saves backtest results to a CSV file for further analysis.

Usage:
------
1. Provide a `strategy` object implementing:
   - `calculate_indicators(df)` → returns a DataFrame with indicator columns.
   - `generate_signals(df)` → returns a Series of 'BUY', 'SELL', or 'HOLD' signals.
   - (Optional) A `fetch_historical_data()` method if using real data.
2. Initialize `Backtester` with the strategy, logger, and optional parameters.
3. Call `run_backtest(...)` with either a single DataFrame or a dict of DataFrames.
4. Receive a DataFrame with signals, positions, returns, and cumulative performance.

Dependencies:
-------------
- pandas
- logging
- typing
- A user-defined `strategy` object
"""

import pandas as pd
import logging
from typing import Any, Dict, Union
import datetime

class Backtester:
    def __init__(
        self,
        strategy: Any,
        logger: logging.Logger,
        api: Any = None,
        symbol: str = None,
        timeframe: str = None,
        limit: int = None,
        portfolio: Dict[str, Any] = None,
        log_callback: Any = None,
        initial_cash: float = 10000,
        log_file: str = "backtest_results.csv"
    ):
        """
        Initializes the Backtester with flexible parameters.

        Parameters:
        -----------
        - strategy (object): Trading strategy instance. Must implement:
            • calculate_indicators(df) → DataFrame with indicators.
            • generate_signals(df) → Series of 'BUY', 'SELL', or 'HOLD' signals.
            • (Optional) fetch_historical_data() for real data.
        - logger (logging.Logger): Logger for debug/info messages.
        - api (optional): API object for fetching real-time data.
        - symbol (optional): Ticker symbol for the asset.
        - timeframe (optional): Timeframe for backtesting (e.g., "5Min", "1D").
        - limit (optional): Number of historical bars to consider.
        - portfolio (optional): Dictionary for portfolio configuration.
        - log_callback (optional): External logging callback.
        - initial_cash: Initial account balance.
        - log_file: Filename to save the backtest results.
        """
        self.strategy = strategy
        self.logger = logger
        self.api = api
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.portfolio = portfolio
        self.log_callback = log_callback
        self.initial_cash = initial_cash
        self.log_file = log_file

    def run_backtest(self, 
                     data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]
                    ) -> pd.DataFrame:
        """
        Executes the backtest and returns a DataFrame with computed signals,
        simulated trading performance, and cumulative returns.

        Parameters:
        -----------
        - data: A single DataFrame or a dict of DataFrames for multi-timeframe testing.

        Returns:
        --------
        - DataFrame with added columns:
            'signal'       : Trading signal ('BUY', 'SELL', 'HOLD').
            'position'     : Numeric position (1 for BUY, -1 for SELL, 0 for HOLD).
            'returns'      : Daily returns from 'close'.
            'strategy_returns': Returns adjusted by executed position.
            'cumulative_returns': Cumulative performance over the period.
            'balance'      : Simulated portfolio balance over time.
        """
        self.logger.info("Starting backtest.")

        # If multi-timeframe data is provided, pick primary timeframe (e.g., '5Min')
        if isinstance(data, dict):
            df = self._prepare_multitimeframe_data(data)
        else:
            df = data.copy()

        if "close" not in df.columns:
            raise ValueError("Data must contain a 'close' column for backtesting.")

        # Calculate indicators using the strategy
        df = self._calculate_indicators(df)

        # Generate trading signals
        df = self._generate_signals(df)

        # Simulate trading execution
        df = self._simulate_trading(df)

        # Calculate returns and cumulative performance
        df = self._calculate_returns(df)

        # Save results to CSV
        df.to_csv(self.log_file)
        self.logger.info(f"Backtest results saved to {self.log_file}")
        self.logger.info("Backtest completed.")
        return df

    def _prepare_multitimeframe_data(self, 
                                      data_dict: Dict[str, pd.DataFrame]
                                     ) -> pd.DataFrame:
        """
        Prepares multi-timeframe data by selecting the primary timeframe.
        (Optional: Extend this to merge data from multiple timeframes.)
        """
        self.logger.info("Preparing multi-timeframe data.")
        primary_key = "5Min" if "5Min" in data_dict else list(data_dict.keys())[0]
        return data_dict[primary_key].copy()

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Calculating indicators.")
        return self.strategy.calculate_indicators(df)

    def _generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Generating trade signals.")
        df["signal"] = self.strategy.generate_signals(df)
        df["position"] = df["signal"].map({"BUY": 1, "SELL": -1, "HOLD": 0})
        self.logger.debug(f"Signal distribution:\n{df['signal'].value_counts()}")
        return df

    def _simulate_trading(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Simulates trade execution based on signals. This simple simulation:
         - Enters a BUY when signal is BUY (using all available cash).
         - Exits (SELL) when signal is SELL.
         - Tracks portfolio balance over time.
        """
        position = 0
        entry_price = 0
        cash = self.initial_cash
        balance_history = []

        for i in range(len(df)):
            signal = df["signal"].iloc[i]
            price = df["close"].iloc[i]

            if signal == "BUY" and position == 0:
                position = cash / price
                entry_price = price
                cash = 0
                self.logger.info(f"BUY at {price:.2f}")
            elif signal == "SELL" and position > 0:
                cash = position * price
                position = 0
                self.logger.info(f"SELL at {price:.2f} | P/L: {(cash - self.initial_cash):.2f}")
            balance_history.append(cash + (position * price))
        
        df["balance"] = balance_history
        return df

    def _calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Calculating performance metrics.")
        df["returns"] = df["close"].pct_change()
        df["strategy_returns"] = df["returns"] * df["position"].shift(1)
        df["cumulative_returns"] = (1 + df["strategy_returns"]).cumprod()
        return df

# ------------------------------------------------------------------------------
# Example Usage (for testing via command line)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # For real data, the strategy should have a fetch_historical_data() method.
    # Here we simulate with sample data.
    data = pd.DataFrame({
        "close": [100, 102, 104, 103, 105, 107, 106, 108, 110, 112],
        "high":  [101, 103, 105, 104, 106, 108, 107, 109, 111, 113],
        "low":   [99, 101, 103, 102, 104, 106, 105, 107, 109, 111]
    })
    
    # Instantiate the strategy (real strategy should be implemented in strategy.py)
    strat = Strategy(
        maShortLength=50,
        maLongLength=200,
        rsiLength=14,
        rsiOverbought=60,
        rsiOversold=40,
        atrLength=14,
        atrMultiplier=1.5,
        riskPercent=0.5,
        profitTarget=15,
        useTrailingStop=True
    )
    
    # For testing, add a dummy fetch method to simulate real data (if needed)
    if not hasattr(strat, "fetch_historical_data"):
        strat.fetch_historical_data = lambda: data.copy()
    
    # Initialize Backtester with the strategy and logger
    backtester = Backtester(strategy=strat, logger=logging.getLogger("Backtester"))
    
    # Run backtest
    results = backtester.run_backtest(data)
    print("Backtest Completed. Results:")
    print(results)
