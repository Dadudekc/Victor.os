"""
Strategy implementation module for backtesting framework.

This module provides the base class for implementing backtesting strategies and includes
some common strategy implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .utils import ValidationError, BacktestError

logger = logging.getLogger(__name__)

class StrategyBase(ABC):
    """Base class for implementing backtesting strategies."""
    
    def __init__(self, name: str):
        """
        Initialize the strategy.
        
        Args:
            name: Name of the strategy
        """
        self.name = name
        self.parameters: Dict[str, Any] = {}
        self.positions: Dict[str, float] = {}
        self.cash: float = 0.0
        self.trades: list = []
        
    def initialize(self, parameters: Dict[str, Any]) -> None:
        """
        Initialize the strategy with parameters.
        
        Args:
            parameters: Strategy parameters
        """
        self.parameters = parameters
        self.positions = {}
        self.cash = 0.0
        self.trades = []
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from the data.
        
        Args:
            data: Market data
            
        Returns:
            DataFrame with trading signals
        """
        pass
        
    def run(self, data: pd.DataFrame, initial_capital: float) -> Dict[str, Any]:
        """
        Run the strategy on the provided data.
        
        Args:
            data: Market data
            initial_capital: Initial capital for the strategy
            
        Returns:
            Dictionary containing strategy results
        """
        try:
            # Initialize
            self.cash = initial_capital
            self.positions = {}
            self.trades = []
            
            # Generate signals
            signals = self.generate_signals(data)
            
            # Execute trades
            portfolio_value = []
            for timestamp, row in signals.iterrows():
                # Update positions based on signals
                self._update_positions(row)
                
                # Calculate portfolio value
                portfolio_value.append(self._calculate_portfolio_value(row))
                
            # Calculate performance metrics
            returns = pd.Series(portfolio_value).pct_change()
            
            return {
                'portfolio_value': portfolio_value,
                'returns': returns,
                'positions': self.positions,
                'trades': self.trades,
                'cash': self.cash
            }
            
        except Exception as e:
            logger.error(f"Strategy execution failed: {str(e)}")
            raise BacktestError(f"Strategy execution failed: {str(e)}")
            
    def _update_positions(self, signal: pd.Series) -> None:
        """
        Update positions based on trading signals.
        
        Args:
            signal: Trading signal for current timestamp
        """
        try:
            for symbol, position in self.positions.items():
                if symbol in signal and signal[symbol] != 0:
                    # Close existing position
                    price = signal[f"{symbol}_price"]
                    self.cash += position * price
                    self.trades.append({
                        'timestamp': signal.name,
                        'symbol': symbol,
                        'action': 'sell',
                        'quantity': position,
                        'price': price
                    })
                    self.positions[symbol] = 0
                    
            # Open new positions
            for symbol in signal.index:
                if symbol.endswith('_signal') and signal[symbol] != 0:
                    base_symbol = symbol.replace('_signal', '')
                    price = signal[f"{base_symbol}_price"]
                    quantity = (self.cash * abs(signal[symbol])) / price
                    
                    if quantity > 0:
                        self.positions[base_symbol] = quantity
                        self.cash -= quantity * price
                        self.trades.append({
                            'timestamp': signal.name,
                            'symbol': base_symbol,
                            'action': 'buy',
                            'quantity': quantity,
                            'price': price
                        })
                        
        except Exception as e:
            logger.error(f"Failed to update positions: {str(e)}")
            raise BacktestError(f"Failed to update positions: {str(e)}")
            
    def _calculate_portfolio_value(self, data: pd.Series) -> float:
        """
        Calculate current portfolio value.
        
        Args:
            data: Current market data
            
        Returns:
            Total portfolio value
        """
        try:
            value = self.cash
            for symbol, position in self.positions.items():
                if position != 0:
                    price = data[f"{symbol}_price"]
                    value += position * price
            return value
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio value: {str(e)}")
            raise BacktestError(f"Failed to calculate portfolio value: {str(e)}")
            
class MovingAverageCrossover(StrategyBase):
    """Moving average crossover strategy implementation."""
    
    def __init__(self, short_window: int = 20, long_window: int = 50):
        """
        Initialize the moving average crossover strategy.
        
        Args:
            short_window: Short moving average window
            long_window: Long moving average window
        """
        super().__init__("MovingAverageCrossover")
        self.parameters = {
            'short_window': short_window,
            'long_window': long_window
        }
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on moving average crossovers.
        
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
                long_ma = symbol_data['price'].rolling(
                    window=self.parameters['long_window']
                ).mean()
                
                # Generate signals
                signals[f"{symbol}_signal"] = np.where(
                    short_ma > long_ma, 1.0, -1.0
                )
                signals[f"{symbol}_price"] = symbol_data['price']
                
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate signals: {str(e)}")
            raise BacktestError(f"Failed to generate signals: {str(e)}")
            
class MeanReversion(StrategyBase):
    """Mean reversion strategy implementation."""
    
    def __init__(self, window: int = 20, std_dev: float = 2.0):
        """
        Initialize the mean reversion strategy.
        
        Args:
            window: Window for calculating mean and standard deviation
            std_dev: Number of standard deviations for signal generation
        """
        super().__init__("MeanReversion")
        self.parameters = {
            'window': window,
            'std_dev': std_dev
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
                
                # Generate signals
                upper_band = mean + (self.parameters['std_dev'] * std)
                lower_band = mean - (self.parameters['std_dev'] * std)
                
                signals[f"{symbol}_signal"] = np.where(
                    symbol_data['price'] > upper_band, -1.0,
                    np.where(symbol_data['price'] < lower_band, 1.0, 0.0)
                )
                signals[f"{symbol}_price"] = symbol_data['price']
                
            return signals
            
        except Exception as e:
            logger.error(f"Failed to generate signals: {str(e)}")
            raise BacktestError(f"Failed to generate signals: {str(e)}") 