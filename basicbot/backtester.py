"""
backtester.py - Trading Strategy Backtesting Engine

This module implements a Backtester class that evaluates trading strategies using historical data.
It supports single or multi-timeframe data, calculates signals, and computes strategy performance.

Key Features:
- Accepts single or multi-timeframe DataFrames (or a dictionary of DataFrames)
- Calculates trading indicators using the user-provided strategy class
- Generates BUY/SELL/HOLD signals and maps them to numeric positions
- Simulates trading execution to compute returns and cumulative performance
- Logs all major steps using a provided logger
- Saves backtest results to a CSV file for further analysis
"""

import pandas as pd
import numpy as np
import logging
from typing import Any, Dict, Union, Optional, List
import datetime
from pathlib import Path

# Handle both package and standalone imports
try:
    from basicbot.config import config
    from basicbot.logger import setup_logging
    from basicbot.strategy import Strategy
except ImportError:
    from config import config
    from logger import setup_logging
    from strategy import Strategy


class Backtester:
    """
    Implements a backtesting engine for evaluating trading strategies.
    """

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
        log_file: str = "backtest_results.csv",
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
        self.symbol = symbol or getattr(strategy, 'symbol', None) or config.SYMBOL
        self.timeframe = timeframe or getattr(strategy, 'timeframe', None) or config.TIMEFRAME
        self.limit = limit
        self.portfolio = portfolio or {}
        self.log_callback = log_callback
        self.initial_cash = initial_cash
        self.log_file = log_file

        # Performance metrics
        self.metrics = {}
        
        self.logger.info(
            f"Backtester initialized: {self.symbol} @ {self.timeframe}, "
            f"Initial cash: ${self.initial_cash:.2f}"
        )

    def run_backtest(
        self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]
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
            'signal'       : Trading signal ('BUY', 'SELL', or 'HOLD').
            'position'     : Numeric position (1 for BUY, -1 for SELL, 0 for HOLD).
            'returns'      : Daily returns from 'close'.
            'strategy_returns': Returns adjusted by executed position.
            'cumulative_returns': Cumulative performance over the period.
            'balance'      : Simulated portfolio balance over time.
        """
        self.logger.info("Starting backtest.")

        # If multi-timeframe data is provided, select the primary timeframe.
        if isinstance(data, dict):
            df = self._prepare_multitimeframe_data(data)
        else:
            df = data.copy()

        if "close" not in df.columns:
            raise ValueError("Data must contain a 'close' column for backtesting.")

        # Calculate indicators using the strategy.
        df = self._calculate_indicators(df)

        # Generate trading signals.
        df = self._generate_signals(df)

        # Simulate trading execution.
        df = self._simulate_trading(df)

        # Calculate returns and cumulative performance.
        df = self._calculate_returns(df)
        
        # Calculate performance metrics
        self._calculate_performance_metrics(df)

        # Save results to CSV.
        self._save_results(df)
        
        self.logger.info("Backtest completed.")
        return df

    def _prepare_multitimeframe_data(
        self, data_dict: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Prepares multi-timeframe data by selecting the primary timeframe.
        (Optional: Extend this to merge data from multiple timeframes.)
        """
        self.logger.info("Preparing multi-timeframe data.")
        
        # Select primary timeframe based on priority
        timeframe_priority = ["1D", "1H", "15Min", "5Min", "1Min"]
        
        # First try the configured timeframe
        if self.timeframe in data_dict:
            primary_key = self.timeframe
        else:
            # Try to find a timeframe in order of priority
            primary_key = None
            for tf in timeframe_priority:
                if tf in data_dict:
                    primary_key = tf
                    break
            
            # If not found, just use the first one
            if primary_key is None:
                primary_key = list(data_dict.keys())[0]
        
        self.logger.info(f"Selected primary timeframe: {primary_key}")
        return data_dict[primary_key].copy()

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators using the provided strategy.
        """
        self.logger.info("Calculating indicators.")
        
        try:
            return self.strategy.calculate_indicators(df)
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}", exc_info=True)
            raise

    def _generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals using the provided strategy.
        """
        self.logger.info("Generating trade signals.")
        
        try:
            df["signal"] = self.strategy.generate_signals(df)
            df["position"] = df["signal"].map({"BUY": 1, "SELL": -1, "HOLD": 0})
            
            signal_counts = df["signal"].value_counts()
            self.logger.info(f"Signal distribution: {signal_counts.to_dict()}")
            
            return df
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}", exc_info=True)
            raise

    def _simulate_trading(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Simulates trade execution based on signals.
        
        This includes:
        - Position tracking
        - Cash balance updates
        - Transaction costs (optional)
        - Stop-loss and take-profit handling (if enabled)
        """
        self.logger.info("Simulating trading execution.")
        
        # Initialize tracking variables
        current_position = 0
        cash = self.initial_cash
        portfolio_value = []
        equity = []
        transaction_costs = self.portfolio.get("transaction_cost", 0.001)  # 0.1% by default
        
        # Additional tracking for analysis
        trades = []
        current_trade = None
        
        for i in range(len(df)):
            date = df.index[i]
            price = df["close"].iloc[i]
            signal = df["signal"].iloc[i]
            
            # Handle BUY signal
            if signal == "BUY" and current_position == 0:
                # Calculate shares to buy (using all available cash)
                shares_to_buy = cash / (price * (1 + transaction_costs))
                
                # Update position and cash
                current_position = shares_to_buy
                transaction_cost = price * shares_to_buy * transaction_costs
                cash -= (price * shares_to_buy + transaction_cost)
                
                # Record trade
                current_trade = {
                    "entry_date": date,
                    "entry_price": price,
                    "shares": shares_to_buy,
                    "direction": "LONG",
                    "transaction_cost": transaction_cost
                }
                
                self.logger.debug(
                    f"BUY: {shares_to_buy:.2f} shares @ ${price:.2f}, "
                    f"Cost: ${price * shares_to_buy:.2f}, "
                    f"Transaction Fee: ${transaction_cost:.2f}, "
                    f"Remaining Cash: ${cash:.2f}"
                )
                
            # Handle SELL signal
            elif signal == "SELL" and current_position > 0:
                # Calculate sell value and costs
                sell_value = current_position * price
                transaction_cost = sell_value * transaction_costs
                cash += (sell_value - transaction_cost)
                
                # Complete trade record
                if current_trade:
                    current_trade["exit_date"] = date
                    current_trade["exit_price"] = price
                    current_trade["profit_loss"] = (
                        (price - current_trade["entry_price"]) * current_trade["shares"]
                        - current_trade["transaction_cost"]
                        - transaction_cost
                    )
                    current_trade["profit_loss_pct"] = (
                        (price / current_trade["entry_price"]) - 1
                    ) * 100
                    
                    trades.append(current_trade)
                    current_trade = None
                
                self.logger.debug(
                    f"SELL: {current_position:.2f} shares @ ${price:.2f}, "
                    f"Value: ${sell_value:.2f}, "
                    f"Transaction Fee: ${transaction_cost:.2f}, "
                    f"New Cash: ${cash:.2f}"
                )
                
                # Reset position
                current_position = 0
            
            # Calculate portfolio value
            portfolio_value.append(cash + (current_position * price))
            equity.append(current_position * price)
        
        # Add results to DataFrame
        df["cash"] = cash
        df["position_size"] = current_position
        df["equity"] = equity
        df["portfolio_value"] = portfolio_value
        
        # Store trade history
        self.trades = trades
        
        # Log summary
        if trades:
            profit_loss = sum(trade["profit_loss"] for trade in trades)
            win_count = sum(1 for trade in trades if trade["profit_loss"] > 0)
            loss_count = sum(1 for trade in trades if trade["profit_loss"] <= 0)
            
            self.logger.info(
                f"Trading simulation completed: {len(trades)} trades, "
                f"Win: {win_count}, Loss: {loss_count}, "
                f"P/L: ${profit_loss:.2f}"
            )
        else:
            self.logger.info("Trading simulation completed: No trades executed")
        
        return df

    def _calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate returns and performance metrics.
        """
        self.logger.info("Calculating performance metrics.")
        
        # Calculate simple returns (percentage change)
        df["returns"] = df["close"].pct_change()
        
        # Calculate strategy returns (based on position)
        df["strategy_returns"] = df["returns"] * df["position"].shift(1)
        
        # Calculate cumulative returns
        df["cumulative_returns"] = (1 + df["strategy_returns"].fillna(0)).cumprod()
        
        # Calculate drawdown
        df["cumulative_max"] = df["cumulative_returns"].cummax()
        df["drawdown"] = (df["cumulative_returns"] / df["cumulative_max"]) - 1
        
        return df

    def _calculate_performance_metrics(self, df: pd.DataFrame) -> None:
        """
        Calculate and store performance metrics.
        """
        # Filter out any NaN values
        returns = df["strategy_returns"].fillna(0)
        
        # Basic metrics
        total_return = df["cumulative_returns"].iloc[-1] - 1
        annual_return = total_return / (len(df) / 252)  # Assuming 252 trading days
        max_drawdown = df["drawdown"].min()
        
        # Risk metrics
        volatility = returns.std() * np.sqrt(252)  # Annualized volatility
        
        # If volatility is zero, set Sharpe ratio to NaN
        if volatility == 0:
            sharpe_ratio = float("nan")
        else:
            sharpe_ratio = annual_return / volatility
        
        # Win/loss metrics
        if hasattr(self, "trades") and self.trades:
            win_trades = [t for t in self.trades if t["profit_loss"] > 0]
            loss_trades = [t for t in self.trades if t["profit_loss"] <= 0]
            
            win_rate = len(win_trades) / len(self.trades) if self.trades else 0
            
            # Average win/loss
            avg_win = sum(t["profit_loss"] for t in win_trades) / len(win_trades) if win_trades else 0
            avg_loss = sum(t["profit_loss"] for t in loss_trades) / len(loss_trades) if loss_trades else 0
            
            # Profit factor
            gross_profit = sum(t["profit_loss"] for t in win_trades) if win_trades else 0
            gross_loss = sum(t["profit_loss"] for t in loss_trades) if loss_trades else 0
            profit_factor = abs(gross_profit / gross_loss) if gross_loss else float("inf")
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        # Store metrics
        self.metrics = {
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "final_balance": df["portfolio_value"].iloc[-1],
            "trade_count": len(self.trades) if hasattr(self, "trades") else 0,
        }
        
        # Log metrics
        metrics_str = "\n".join([f"{k}: {v:.4f}" for k, v in self.metrics.items()])
        self.logger.info(f"Performance Metrics:\n{metrics_str}")

    def _save_results(self, df: pd.DataFrame) -> None:
        """
        Save backtest results to CSV file.
        """
        try:
            df.to_csv(self.log_file, index=True)
            self.logger.info(f"Backtest results saved to {self.log_file}")
            
            # Save metrics to a separate file
            metrics_file = Path(self.log_file).with_suffix('.metrics.csv')
            pd.DataFrame([self.metrics]).to_csv(metrics_file, index=False)
            self.logger.info(f"Performance metrics saved to {metrics_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving backtest results: {e}", exc_info=True)

    def plot_results(self, df: pd.DataFrame = None, save_path: str = None) -> Any:
        """
        Plot backtest results (if matplotlib is available).
        
        Returns the plot object if successful, None otherwise.
        """
        try:
            import matplotlib.pyplot as plt
            
            if df is None:
                self.logger.error("No DataFrame provided for plotting")
                return None
            
            # Create figure with subplots
            fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
            
            # Plot 1: Price and signals
            ax1 = axes[0]
            ax1.plot(df.index, df["close"], label="Price")
            
            # Plot buy and sell signals
            buys = df[df["signal"] == "BUY"].index
            sells = df[df["signal"] == "SELL"].index
            
            ax1.scatter(buys, df.loc[buys, "close"], marker="^", color="green", s=100, label="Buy")
            ax1.scatter(sells, df.loc[sells, "close"], marker="v", color="red", s=100, label="Sell")
            
            ax1.set_title(f"Backtest Results: {self.symbol} ({self.timeframe})")
            ax1.set_ylabel("Price")
            ax1.legend()
            ax1.grid(True)
            
            # Plot 2: Equity curve
            ax2 = axes[1]
            ax2.plot(df.index, df["portfolio_value"], label="Portfolio Value")
            ax2.set_ylabel("Portfolio Value ($)")
            ax2.legend()
            ax2.grid(True)
            
            # Plot 3: Drawdown
            ax3 = axes[2]
            ax3.fill_between(df.index, df["drawdown"] * 100, 0, color="red", alpha=0.3)
            ax3.set_ylabel("Drawdown (%)")
            ax3.set_xlabel("Date")
            ax3.grid(True)
            
            # Adjust layout
            fig.tight_layout()
            
            # Save figure if path provided
            if save_path:
                plt.savefig(save_path)
                self.logger.info(f"Backtest plot saved to {save_path}")
            
            return fig
        
        except ImportError:
            self.logger.warning("Matplotlib not available for plotting")
            return None
        except Exception as e:
            self.logger.error(f"Error plotting backtest results: {e}", exc_info=True)
            return None


# For testing
if __name__ == "__main__":
    # Setup logger
    logger = setup_logging("backtester_test")
    
    # Create sample data
    dates = pd.date_range(start="2022-01-01", periods=100, freq="D")
    close = np.array([100, 102, 104, 103, 105, 107, 106, 108, 110, 112] * 10)
    high = close + np.random.uniform(0, 2, len(close))
    low = close - np.random.uniform(0, 2, len(close))
    
    df = pd.DataFrame({
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.random.randint(1000, 10000, len(close))
    }, index=dates)
    
    # Initialize strategy
    strategy = Strategy(
        symbol="TSLA",
        timeframe="1D",
        maShortLength=20,
        maLongLength=50,
        rsiLength=14,
        rsiOverbought=70,
        rsiOversold=30
    )
    
    # Initialize backtester
    backtester = Backtester(
        strategy=strategy,
        logger=logger,
        symbol="TSLA",
        timeframe="1D",
        initial_cash=10000,
        log_file="backtest_results.csv"
    )
    
    # Run backtest
    results = backtester.run_backtest(df)
    
    # Plot results
    backtester.plot_results(results, "backtest_plot.png")
    
    print("Backtest completed. Results saved to backtest_results.csv") 