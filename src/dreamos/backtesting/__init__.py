"""
Dream.OS Backtesting Framework

This module provides a comprehensive backtesting framework for strategy optimization,
enabling agents to test and validate their strategies against historical data.
"""

__version__ = "0.1.0"

from .core import BacktestEngine
from .data import DataManager
from .strategies import StrategyBase, MovingAverageCrossover, MeanReversion
from .analysis import PerformanceAnalyzer
from .utils import ValidationError, BacktestError

__all__ = [
    'BacktestEngine',
    'DataManager',
    'StrategyBase',
    'MovingAverageCrossover',
    'MeanReversion',
    'PerformanceAnalyzer',
    'ValidationError',
    'BacktestError'
] 