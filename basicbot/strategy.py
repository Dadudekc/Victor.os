"""
Trading Strategy Module → strategy.py

Description:
------------
This module implements a Strategy class that:
- Fetches real market data from the Alpaca API.
- Calculates technical indicators (SMA, RSI, ATR) and generates trading signals.
- Computes ATR-based dynamic stop-loss and take-profit levels.
- Provides a position sizing function.
- Includes a placeholder for AI-driven signal optimization.
- Supports configurable parameters (symbol, timeframe, lookback days, etc.).

The design closely mimics the following Pine Script strategy:

    // Inputs:
    //   maShortLength = 50, maLongLength = 200, rsiLength = 14, rsiOverbought = 60, rsiOversold = 40
    //   atrLength = 14, atrMultiplier = 1.5, riskPercent = 0.5, profitTarget = 15, useTrailingStop = true

    // Indicators:
    //   maShort = sma(close, maShortLength)
    //   maLong  = sma(close, maLongLength)
    //   rsi = rsi(close, rsiLength)
    //   atrValue = atr(atrLength)

    // Entry Conditions:
    //   Long: close > maShort and close > maLong and rsi < rsiOverbought
    //   Short: close < maShort and close < maLong and rsi > rsiOversold

    // Exit Levels:
    //   For long: stop = close - (atrValue * atrMultiplier), take profit = close * (1 + profitTarget/100)
    //   For short: stop = close + (atrValue * atrMultiplier), take profit = close * (1 - profitTarget/100)
    //   Optionally use a trailing stop.

Dependencies:
-------------
- pandas, numpy, logging, datetime
- Alpaca trade API
- Basicbot config and AI model integration

Usage:
------
    from strategy import Strategy
    strat = Strategy(symbol="TSLA", timeframe="5Min")
    df = strat.fetch_historical_data()
    if not df.empty:
        df = strat.calculate_indicators(df)
        df["signal"] = strat.generate_signals(df)
        df = strat.compute_exit_levels(df)
        pos_size = strat.calculate_position_size(balance=10000, stop_loss_pct=0.05)
        optimized_df = strat.optimize_signals(df)
        print(optimized_df.tail())
    else:
        print("No market data available.")
"""

import pandas as pd
import numpy as np
import logging
import datetime
import alpaca_trade_api as tradeapi

# Attempt to import as part of the package; fallback to standalone.
try:
    from basicbot.config import config  
    from basicbot.ai_models import ModelManager
except ImportError:
    from config import config  
    from ai_models import ModelManager

class Strategy:
    def __init__(self,
                 symbol: str = "TSLA",
                 timeframe: str = "5Min",
                 lookback_days: int = 30,
                 maShortLength: int = 50,
                 maLongLength: int = 200,
                 rsiLength: int = 14,
                 rsiOverbought: int = 60,
                 rsiOversold: int = 40,
                 atrLength: int = 14,
                 atrMultiplier: float = 1.5,
                 riskPercent: float = 0.5,
                 profitTarget: float = 15,
                 useTrailingStop: bool = True):
        """
        Initialize strategy parameters and API connection.
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback_days = lookback_days
        self.maShortLength = maShortLength
        self.maLongLength = maLongLength
        self.rsiLength = rsiLength
        self.rsiOverbought = rsiOverbought
        self.rsiOversold = rsiOversold
        self.atrLength = atrLength
        self.atrMultiplier = atrMultiplier
        self.riskPercent = riskPercent
        self.profitTarget = profitTarget
        self.useTrailingStop = useTrailingStop

        # Initialize Alpaca API connection.
        self.api = tradeapi.REST(
            config.ALPACA_API_KEY, 
            config.ALPACA_SECRET_KEY, 
            config.ALPACA_BASE_URL, 
            api_version="v2"
        )

        # Setup logger.
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        # Initialize model manager for future AI optimizations.
        self.model_manager = ModelManager()

    def fetch_historical_data(self) -> pd.DataFrame:
        """
        Fetch real historical market data from Alpaca API.
        :return: DataFrame with 'open', 'high', 'low', 'close', 'volume'
        """
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=self.lookback_days)
        try:
            bars = self.api.get_bars(
                self.symbol,
                self.timeframe,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                limit=10000,
                feed="iex"  # Use free IEX data instead of SIP.
            ).df
        except tradeapi.rest.APIError as e:
            self.logger.error(f"🚨 Alpaca API Error: {e}")
            return pd.DataFrame()
        if bars.empty:
            self.logger.warning(f"⚠️ No data returned for {self.symbol} {self.timeframe}.")
            return pd.DataFrame()
        bars.index = bars.index.tz_convert("America/New_York")
        return bars

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators:
          - SMA_short: Short-term moving average.
          - SMA_long: Long-term moving average.
          - RSI: Relative Strength Index.
          - ATR: Average True Range.
        :param df: DataFrame with at least 'close', 'high', and 'low' columns.
        :return: DataFrame with added columns: 'SMA_short', 'SMA_long', 'RSI', 'ATR'
        """
        if df.empty:
            raise ValueError("❌ DataFrame is empty! Cannot calculate indicators.")
        df = df.copy()
        df["SMA_short"] = df["close"].rolling(window=self.maShortLength, min_periods=1).mean()
        df["SMA_long"] = df["close"].rolling(window=self.maLongLength, min_periods=1).mean()
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=self.rsiLength, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.rsiLength, min_periods=1).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df["RSI"] = 100 - (100 / (1 + rs))
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["ATR"] = true_range.rolling(window=self.atrLength, min_periods=1).mean()
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on indicator conditions.
        Uses a buffer of 5 for the RSI thresholds to avoid borderline cases.
        For long conditions:
            - BUY if RSI < (rsiOverbought - buffer), else HOLD.
        For short conditions:
            - SELL if RSI > (rsiOversold + buffer), else HOLD.
        :param df: DataFrame with 'close', 'SMA_short', 'SMA_long', 'RSI'
        :return: Pandas Series with signals ("BUY", "SELL", "HOLD")
        """
        buffer = 5
        for col in ["SMA_short", "SMA_long", "RSI"]:
            if col not in df.columns:
                raise ValueError(f"DataFrame must contain '{col}' column.")
        signals = []
        for i in range(len(df)):
            if i == 0:
                signals.append("HOLD")
            else:
                price = df["close"].iloc[i]
                sma_short = df["SMA_short"].iloc[i]
                sma_long = df["SMA_long"].iloc[i]
                rsi = df["RSI"].iloc[i]
                # Long scenario: if price is above both SMAs.
                if price > sma_short and price > sma_long:
                    if rsi < (self.rsiOverbought - buffer):
                        signals.append("BUY")
                    else:
                        signals.append("HOLD")
                # Short scenario: if price is below both SMAs.
                elif price < sma_short and price < sma_long:
                    if rsi > (self.rsiOversold + buffer):
                        signals.append("SELL")
                    else:
                        signals.append("HOLD")
                else:
                    signals.append("HOLD")
        return pd.Series(signals, index=df.index)

    def compute_exit_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute dynamic stop-loss and take-profit levels based on ATR.
        For Long:
          - stopLevel = close - (ATR * atrMultiplier)
          - takeProfit = close * (1 + profitTarget/100)
        For Short:
          - stopLevel = close + (ATR * atrMultiplier)
          - takeProfit = close * (1 - profitTarget/100)
        :param df: DataFrame with 'close' and 'ATR' columns.
        :return: DataFrame with additional columns: 'stopLong', 'takeProfitLong', 'stopShort', 'takeProfitShort'
        """
        for col in ["close", "ATR"]:
            if col not in df.columns:
                raise ValueError(f"DataFrame must contain '{col}' column.")
        df = df.copy()
        df["stopLong"] = df["close"] - (df["ATR"] * self.atrMultiplier)
        df["takeProfitLong"] = df["close"] * (1 + self.profitTarget / 100)
        df["stopShort"] = df["close"] + (df["ATR"] * self.atrMultiplier)
        df["takeProfitShort"] = df["close"] * (1 - self.profitTarget / 100)
        return df

    def calculate_position_size(self, balance: float, stop_loss_pct: float) -> float:
        """
        Calculate the position size based on the account balance and risk parameters.
        :param balance: Total account balance.
        :param stop_loss_pct: Stop-loss percentage (as a decimal) representing risk per share.
        :return: Calculated position size.
        """
        if stop_loss_pct <= 0:
            raise ValueError("Stop loss percentage must be greater than 0.")
        risk_amount = balance * (self.riskPercent / 100)
        return risk_amount / stop_loss_pct

    def optimize_signals(self, df: pd.DataFrame, model_name: str = "randomforest") -> pd.DataFrame:
        """
        Use the selected ML model to optimize or adjust trading signals.
        :param df: DataFrame with initial signals and indicators.
        :param model_name: The name of the model to use (default: randomforest).
        :return: DataFrame with an additional 'optimized_signal' column.
        """
        predictions = self.model_manager.predict(model_name, df)
        df = df.copy()
        df["optimized_signal"] = predictions
        return df

    def backtest(self):
        """
        Fetch real data, calculate indicators, generate signals, compute exit levels,
        and display the final backtest results.
        """
        df = self.fetch_historical_data()
        if df.empty:
            print("❌ No data fetched.")
            return
        df = self.calculate_indicators(df)
        df["signal"] = self.generate_signals(df)
        df = self.compute_exit_levels(df)
        print("✅ Backtest Results:")
        print(df[["close", "SMA_short", "SMA_long", "RSI", "ATR", "signal",
                  "stopLong", "takeProfitLong", "stopShort", "takeProfitShort"]].tail(10))

# Run backtest if executed as a script.
if __name__ == "__main__":
    strat = Strategy(symbol="TSLA", timeframe="5Min")
    strat.backtest()
