"""
strategy.py - Trading Strategy Implementation

This module implements the Strategy class for technical analysis and signal generation.
It provides a flexible framework for creating and testing trading strategies.

Key features:
- Technical indicator calculation (MA, RSI, MACD, etc.)
- Signal generation (BUY/SELL/HOLD)
- Historical data fetching
- Configurable parameters
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Union, List, Any
import datetime

# Handle both package and standalone imports
try:
    from basicbot.config import config
    from basicbot.logger import setup_logging
except ImportError:
    from config import config
    from logger import setup_logging


class Strategy:
    """
    Base class for implementing trading strategies.
    
    This class provides the framework for calculating technical indicators
    and generating trading signals based on configurable parameters.
    """
    
    def __init__(
        self,
        symbol: str = None,
        timeframe: str = None,
        maShortLength: int = 50,
        maLongLength: int = 200,
        rsiLength: int = 14,
        rsiOverbought: int = 70,
        rsiOversold: int = 30,
        macdFast: int = 12,
        macdSlow: int = 26,
        macdSignal: int = 9,
        atrLength: int = 14,
        atrMultiplier: float = 2.0,
        riskPercent: float = 1.0,
        profitTarget: float = 10.0,
        useTrailingStop: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize a trading strategy with configurable parameters.
        
        Args:
            symbol (str): Trading symbol (e.g., "TSLA")
            timeframe (str): Data timeframe (e.g., "1D", "1H", "5Min")
            maShortLength (int): Short moving average period
            maLongLength (int): Long moving average period
            rsiLength (int): RSI calculation period
            rsiOverbought (int): RSI overbought threshold
            rsiOversold (int): RSI oversold threshold
            macdFast (int): MACD fast line period
            macdSlow (int): MACD slow line period
            macdSignal (int): MACD signal line period
            atrLength (int): ATR calculation period
            atrMultiplier (float): ATR multiplier for stops
            riskPercent (float): Percentage of capital to risk per trade
            profitTarget (float): Target profit percentage
            useTrailingStop (bool): Whether to use trailing stops
            logger (Logger): Logger for debug/info messages
        """
        # Setup logger
        self.logger = logger or setup_logging("strategy")

        # Store initialization parameters
        self.symbol = symbol or config.SYMBOL
        self.timeframe = timeframe or config.TIMEFRAME
        
        # Moving Average parameters
        self.maShortLength = maShortLength
        self.maLongLength = maLongLength
        
        # RSI parameters
        self.rsiLength = rsiLength
        self.rsiOverbought = rsiOverbought
        self.rsiOversold = rsiOversold
        
        # MACD parameters
        self.macdFast = macdFast
        self.macdSlow = macdSlow
        self.macdSignal = macdSignal
        
        # Risk management parameters
        self.atrLength = atrLength
        self.atrMultiplier = atrMultiplier
        self.riskPercent = riskPercent
        self.profitTarget = profitTarget
        self.useTrailingStop = useTrailingStop
        
        self.logger.info(
            f"Strategy initialized: {self.symbol} @ {self.timeframe}"
        )
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators on a DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame with OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with added indicator columns
        """
        self.logger.debug("Calculating technical indicators...")
        
        # Ensure DataFrame is sorted by date
        if 'date' in df.columns:
            df = df.sort_values('date')
        
        # Make a copy to avoid SettingWithCopyWarning
        df = df.copy()
        
        # Calculate Simple Moving Averages
        df['SMA_short'] = self._calculate_sma(df['close'], self.maShortLength)
        df['SMA_long'] = self._calculate_sma(df['close'], self.maLongLength)
        
        # Calculate RSI
        df['RSI'] = self._calculate_rsi(df['close'], self.rsiLength)
        
        # Calculate MACD
        macd_df = self._calculate_macd(
            df['close'], 
            self.macdFast, 
            self.macdSlow, 
            self.macdSignal
        )
        df = pd.concat([df, macd_df], axis=1)
        
        # Calculate ATR for stop loss
        if 'high' in df.columns and 'low' in df.columns:
            df['ATR'] = self._calculate_atr(
                df['high'], 
                df['low'], 
                df['close'], 
                self.atrLength
            )
            
            # Calculate stop loss levels
            df['stop_loss'] = df['close'] - (df['ATR'] * self.atrMultiplier)
            df['take_profit'] = df['close'] + (df['ATR'] * self.atrMultiplier * 
                                             (self.profitTarget / 100))
        
        self.logger.debug("Technical indicators calculated")
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on technical indicators.
        
        Args:
            df (pd.DataFrame): DataFrame with price data and indicators
            
        Returns:
            pd.Series: Series with 'BUY', 'SELL', or 'HOLD' signals
        """
        self.logger.debug("Generating trading signals...")
        
        # Initialize signals series with 'HOLD'
        signals = pd.Series(['HOLD'] * len(df), index=df.index)
        
        # Check required columns exist
        required_columns = ['close', 'SMA_short', 'SMA_long', 'RSI', 'MACD', 'MACD_signal']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            self.logger.error(f"Missing required columns: {missing}")
            return signals
        
        # Example strategy: Moving Average Crossover with RSI filter
        # BUY when short MA crosses above long MA and RSI < 70
        # SELL when short MA crosses below long MA or RSI > 70
        
        for i in range(1, len(df)):
            # Moving Average Crossover
            ma_cross_up = (df['SMA_short'].iloc[i-1] <= df['SMA_long'].iloc[i-1] and 
                          df['SMA_short'].iloc[i] > df['SMA_long'].iloc[i])
            
            ma_cross_down = (df['SMA_short'].iloc[i-1] >= df['SMA_long'].iloc[i-1] and 
                            df['SMA_short'].iloc[i] < df['SMA_long'].iloc[i])
            
            # MACD Crossover
            macd_cross_up = (df['MACD'].iloc[i-1] <= df['MACD_signal'].iloc[i-1] and 
                            df['MACD'].iloc[i] > df['MACD_signal'].iloc[i])
            
            macd_cross_down = (df['MACD'].iloc[i-1] >= df['MACD_signal'].iloc[i-1] and 
                              df['MACD'].iloc[i] < df['MACD_signal'].iloc[i])
            
            # RSI Conditions
            rsi_oversold = df['RSI'].iloc[i] < self.rsiOversold
            rsi_overbought = df['RSI'].iloc[i] > self.rsiOverbought
            
            # Combined Signals
            # BUY: MA crossover up OR MACD crossover up, with RSI not overbought
            if (ma_cross_up or macd_cross_up) and not rsi_overbought:
                signals.iloc[i] = 'BUY'
            
            # SELL: MA crossover down OR MACD crossover down OR RSI overbought
            elif ma_cross_down or macd_cross_down or rsi_overbought:
                signals.iloc[i] = 'SELL'
        
        # Count signals
        buy_count = (signals == 'BUY').sum()
        sell_count = (signals == 'SELL').sum()
        self.logger.info(f"Generated signals: BUY={buy_count}, SELL={sell_count}")
        
        return signals
    
    def fetch_historical_data(self) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for the symbol and timeframe.
        
        Returns:
            pd.DataFrame: DataFrame with OHLCV data or None if failed
        """
        self.logger.info(f"Fetching historical data: {self.symbol} @ {self.timeframe}")
        
        try:
            # This method should be implemented based on the data source
            # For now, we'll use a placeholder and return None
            
            # In a real implementation, use an API client to fetch data
            # Example:
            # from alpaca_trade_api import REST
            # api = REST()
            # bars = api.get_bars(self.symbol, self.timeframe).df
            # return bars
            
            self.logger.warning("Historical data fetching not implemented")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data: {e}", exc_info=True)
            return None
    
    def _calculate_sma(self, price_series: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return price_series.rolling(window=period).mean()
    
    def _calculate_rsi(self, price_series: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index"""
        # Calculate price changes
        delta = price_series.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS
        rs = avg_gain / avg_loss
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(
        self, 
        price_series: pd.Series, 
        fast_period: int, 
        slow_period: int, 
        signal_period: int
    ) -> pd.DataFrame:
        """Calculate MACD, MACD Signal, and MACD Histogram"""
        # Calculate EMAs
        ema_fast = price_series.ewm(span=fast_period).mean()
        ema_slow = price_series.ewm(span=slow_period).mean()
        
        # Calculate MACD line
        macd = ema_fast - ema_slow
        
        # Calculate MACD signal line
        macd_signal = macd.ewm(span=signal_period).mean()
        
        # Calculate MACD histogram
        macd_hist = macd - macd_signal
        
        # Return as DataFrame
        return pd.DataFrame({
            'MACD': macd,
            'MACD_signal': macd_signal,
            'MACD_hist': macd_hist
        }, index=price_series.index)
    
    def _calculate_atr(
        self, 
        high: pd.Series, 
        low: pd.Series, 
        close: pd.Series, 
        period: int
    ) -> pd.Series:
        """Calculate Average True Range"""
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        # True Range is the maximum of the three
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate ATR as moving average of True Range
        atr = tr.rolling(window=period).mean()
        return atr


# For testing
if __name__ == "__main__":
    # Create sample data
    dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
    data = np.random.normal(0, 1, 100).cumsum() + 100
    high = data + np.random.uniform(0, 3, 100)
    low = data - np.random.uniform(0, 3, 100)
    
    df = pd.DataFrame({
        'date': dates,
        'open': data,
        'high': high,
        'low': low,
        'close': data,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Initialize strategy
    strategy = Strategy(symbol="TSLA", timeframe="1D")
    
    # Calculate indicators
    df_with_indicators = strategy.calculate_indicators(df)
    
    # Generate signals
    signals = strategy.generate_signals(df_with_indicators)
    
    # Print sample results
    print(df_with_indicators.tail().round(2))
    print("\nSignals:")
    print(signals.value_counts()) 