"""
BasicBot strategy implementations.

This module provides various trading strategies for BasicBot instances, each with
different approaches to market analysis and risk management.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from ..backtesting.strategies import StrategyBase

logger = logging.getLogger(__name__)

class TrendFollowingStrategy(StrategyBase):
    """Trend following strategy using multiple timeframes and indicators."""
    
    def __init__(
        self,
        short_window: int = 20,
        medium_window: int = 50,
        long_window: int = 200,
        atr_period: int = 14,
        risk_per_trade: float = 0.02
    ):
        """
        Initialize the trend following strategy.
        
        Args:
            short_window: Short-term moving average window
            medium_window: Medium-term moving average window
            long_window: Long-term moving average window
            atr_period: ATR calculation period
            risk_per_trade: Maximum risk per trade as fraction of capital
        """
        super().__init__("TrendFollowing")
        self.parameters = {
            'short_window': short_window,
            'medium_window': medium_window,
            'long_window': long_window,
            'atr_period': atr_period,
            'risk_per_trade': risk_per_trade
        }
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on trend following indicators.
        
        Args:
            data: Market data
            
        Returns:
            DataFrame with trading signals
        """
        try:
            signals = pd.DataFrame(index=data.index)
            
            for symbol in data['symbol'].unique():
                symbol_data = data[data['symbol'] == symbol]
                
                # Calculate moving averages
                short_ma = symbol_data['price'].rolling(
                    window=self.parameters['short_window']
                ).mean()
                medium_ma = symbol_data['price'].rolling(
                    window=self.parameters['medium_window']
                ).mean()
                long_ma = symbol_data['price'].rolling(
                    window=self.parameters['long_window']
                ).mean()
                
                # Calculate ATR
                high_low = symbol_data['high'] - symbol_data['low']
                high_close = np.abs(symbol_data['high'] - symbol_data['close'].shift())
                low_close = np.abs(symbol_data['low'] - symbol_data['close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = np.max(ranges, axis=1)
                atr = true_range.rolling(window=self.parameters['atr_period']).mean()
                
                # Generate signals
                trend_signal = np.where(
                    (short_ma > medium_ma) & (medium_ma > long_ma),
                    1.0,
                    np.where(
                        (short_ma < medium_ma) & (medium_ma < long_ma),
                        -1.0,
                        0.0
                    )
                )
                
                # Apply risk management
                position_size = self.parameters['risk_per_trade'] * self.cash / atr
                signals[f"{symbol}_signal"] = trend_signal * position_size
                signals[f"{symbol}_price"] = symbol_data['price']
                
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate signals: {str(e)}")
            raise BacktestError(f"Failed to generate signals: {str(e)}")

class MeanReversionStrategy(StrategyBase):
    """Mean reversion strategy with dynamic volatility bands."""
    
    def __init__(
        self,
        window: int = 20,
        std_dev: float = 2.0,
        min_holding_period: int = 5,
        max_holding_period: int = 20
    ):
        """
        Initialize the mean reversion strategy.
        
        Args:
            window: Window for calculating mean and standard deviation
            std_dev: Number of standard deviations for signal generation
            min_holding_period: Minimum holding period for positions
            max_holding_period: Maximum holding period for positions
        """
        super().__init__("MeanReversion")
        self.parameters = {
            'window': window,
            'std_dev': std_dev,
            'min_holding_period': min_holding_period,
            'max_holding_period': max_holding_period
        }
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on mean reversion.
        
        Args:
            data: Market data
            
        Returns:
            DataFrame with trading signals
        """
        try:
            signals = pd.DataFrame(index=data.index)
            
            for symbol in data['symbol'].unique():
                symbol_data = data[data['symbol'] == symbol]
                
                # Calculate mean and standard deviation
                mean = symbol_data['price'].rolling(
                    window=self.parameters['window']
                ).mean()
                std = symbol_data['price'].rolling(
                    window=self.parameters['window']
                ).std()
                
                # Calculate z-score
                z_score = (symbol_data['price'] - mean) / std
                
                # Generate signals
                signal = np.where(
                    z_score > self.parameters['std_dev'],
                    -1.0,
                    np.where(
                        z_score < -self.parameters['std_dev'],
                        1.0,
                        0.0
                    )
                )
                
                # Apply holding period constraints
                holding_period = np.random.randint(
                    self.parameters['min_holding_period'],
                    self.parameters['max_holding_period'] + 1
                )
                signal = pd.Series(signal).rolling(window=holding_period).mean()
                
                signals[f"{symbol}_signal"] = signal
                signals[f"{symbol}_price"] = symbol_data['price']
                
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate signals: {str(e)}")
            raise BacktestError(f"Failed to generate signals: {str(e)}")

class MomentumStrategy(StrategyBase):
    """Momentum strategy with relative strength and volume analysis."""
    
    def __init__(
        self,
        lookback_period: int = 20,
        volume_threshold: float = 1.5,
        max_positions: int = 5
    ):
        """
        Initialize the momentum strategy.
        
        Args:
            lookback_period: Period for calculating momentum
            volume_threshold: Volume threshold for signal confirmation
            max_positions: Maximum number of concurrent positions
        """
        super().__init__("Momentum")
        self.parameters = {
            'lookback_period': lookback_period,
            'volume_threshold': volume_threshold,
            'max_positions': max_positions
        }
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on momentum and volume.
        
        Args:
            data: Market data
            
        Returns:
            DataFrame with trading signals
        """
        try:
            signals = pd.DataFrame(index=data.index)
            
            for symbol in data['symbol'].unique():
                symbol_data = data[data['symbol'] == symbol]
                
                # Calculate momentum
                returns = symbol_data['price'].pct_change(
                    periods=self.parameters['lookback_period']
                )
                
                # Calculate volume ratio
                volume_ma = symbol_data['volume'].rolling(
                    window=self.parameters['lookback_period']
                ).mean()
                volume_ratio = symbol_data['volume'] / volume_ma
                
                # Generate signals
                momentum_signal = np.where(
                    returns > 0,
                    1.0,
                    np.where(
                        returns < 0,
                        -1.0,
                        0.0
                    )
                )
                
                # Apply volume filter
                volume_filter = volume_ratio > self.parameters['volume_threshold']
                signal = momentum_signal * volume_filter
                
                # Limit number of positions
                if len(self.positions) >= self.parameters['max_positions']:
                    signal = 0.0
                
                signals[f"{symbol}_signal"] = signal
                signals[f"{symbol}_price"] = symbol_data['price']
                
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate signals: {str(e)}")
            raise BacktestError(f"Failed to generate signals: {str(e)}")

class RiskAwareStrategy(StrategyBase):
    """Risk-aware strategy with dynamic position sizing and stop losses."""
    
    def __init__(
        self,
        volatility_window: int = 20,
        max_risk_per_trade: float = 0.02,
        stop_loss_atr: float = 2.0,
        trailing_stop: bool = True
    ):
        """
        Initialize the risk-aware strategy.
        
        Args:
            volatility_window: Window for calculating volatility
            max_risk_per_trade: Maximum risk per trade as fraction of capital
            stop_loss_atr: Stop loss distance in ATR units
            trailing_stop: Whether to use trailing stops
        """
        super().__init__("RiskAware")
        self.parameters = {
            'volatility_window': volatility_window,
            'max_risk_per_trade': max_risk_per_trade,
            'stop_loss_atr': stop_loss_atr,
            'trailing_stop': trailing_stop
        }
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals with risk management.
        
        Args:
            data: Market data
            
        Returns:
            DataFrame with trading signals
        """
        try:
            signals = pd.DataFrame(index=data.index)
            
            for symbol in data['symbol'].unique():
                symbol_data = data[data['symbol'] == symbol]
                
                # Calculate volatility
                returns = symbol_data['price'].pct_change()
                volatility = returns.rolling(
                    window=self.parameters['volatility_window']
                ).std()
                
                # Calculate ATR
                high_low = symbol_data['high'] - symbol_data['low']
                high_close = np.abs(symbol_data['high'] - symbol_data['close'].shift())
                low_close = np.abs(symbol_data['low'] - symbol_data['close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = np.max(ranges, axis=1)
                atr = true_range.rolling(window=self.parameters['volatility_window']).mean()
                
                # Calculate position size based on risk
                position_size = self.parameters['max_risk_per_trade'] * self.cash / (atr * self.parameters['stop_loss_atr'])
                
                # Generate base signals
                trend = symbol_data['price'].rolling(
                    window=self.parameters['volatility_window']
                ).mean()
                signal = np.where(
                    symbol_data['price'] > trend,
                    1.0,
                    np.where(
                        symbol_data['price'] < trend,
                        -1.0,
                        0.0
                    )
                )
                
                # Apply position sizing
                signal = signal * position_size
                
                # Calculate stop loss levels
                if self.parameters['trailing_stop']:
                    stop_loss = symbol_data['price'] - (atr * self.parameters['stop_loss_atr'])
                else:
                    stop_loss = symbol_data['price'] * (1 - self.parameters['max_risk_per_trade'])
                
                signals[f"{symbol}_signal"] = signal
                signals[f"{symbol}_price"] = symbol_data['price']
                signals[f"{symbol}_stop_loss"] = stop_loss
                
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate signals: {str(e)}")
            raise BacktestError(f"Failed to generate signals: {str(e)}") 