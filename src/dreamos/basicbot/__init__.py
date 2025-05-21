"""
BasicBot module for implementing and testing trading strategies.

This module provides strategy implementations for BasicBot instances, focusing on
algorithmic design, risk management, and performance optimization.
"""

from .strategies import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    RiskAwareStrategy
)

__version__ = "0.1.0"
__all__ = [
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
    'MomentumStrategy',
    'RiskAwareStrategy'
] 