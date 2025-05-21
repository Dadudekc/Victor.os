"""
Tests for BasicBot strategy implementations.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .strategies import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    RiskAwareStrategy
)

class TestBasicBotStrategies(unittest.TestCase):
    """Test cases for BasicBot strategies."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample market data
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=100),
            end=datetime.now(),
            freq='D'
        )
        
        # Generate random price data
        np.random.seed(42)
        prices = np.random.normal(100, 2, len(dates))
        volumes = np.random.normal(1000000, 200000, len(dates))
        
        # Create DataFrame
        self.data = pd.DataFrame({
            'symbol': ['AAPL'] * len(dates),
            'price': prices,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': volumes
        }, index=dates)
        
    def test_trend_following_strategy(self):
        """Test trend following strategy."""
        strategy = TrendFollowingStrategy()
        signals = strategy.generate_signals(self.data)
        
        # Verify signal generation
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn('AAPL_signal', signals.columns)
        self.assertIn('AAPL_price', signals.columns)
        
        # Verify signal values
        self.assertTrue(all(signals['AAPL_signal'].isin([-1.0, 0.0, 1.0])))
        
    def test_mean_reversion_strategy(self):
        """Test mean reversion strategy."""
        strategy = MeanReversionStrategy()
        signals = strategy.generate_signals(self.data)
        
        # Verify signal generation
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn('AAPL_signal', signals.columns)
        self.assertIn('AAPL_price', signals.columns)
        
        # Verify signal values
        self.assertTrue(all(signals['AAPL_signal'].isin([-1.0, 0.0, 1.0])))
        
    def test_momentum_strategy(self):
        """Test momentum strategy."""
        strategy = MomentumStrategy()
        signals = strategy.generate_signals(self.data)
        
        # Verify signal generation
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn('AAPL_signal', signals.columns)
        self.assertIn('AAPL_price', signals.columns)
        
        # Verify signal values
        self.assertTrue(all(signals['AAPL_signal'].isin([-1.0, 0.0, 1.0])))
        
    def test_risk_aware_strategy(self):
        """Test risk-aware strategy."""
        strategy = RiskAwareStrategy()
        signals = strategy.generate_signals(self.data)
        
        # Verify signal generation
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn('AAPL_signal', signals.columns)
        self.assertIn('AAPL_price', signals.columns)
        self.assertIn('AAPL_stop_loss', signals.columns)
        
        # Verify signal values
        self.assertTrue(all(signals['AAPL_signal'].isin([-1.0, 0.0, 1.0])))
        
        # Verify stop loss levels
        self.assertTrue(all(signals['AAPL_stop_loss'] < signals['AAPL_price']))
        
    def test_strategy_initialization(self):
        """Test strategy initialization with custom parameters."""
        # Test trend following strategy
        trend_strategy = TrendFollowingStrategy(
            short_window=10,
            medium_window=30,
            long_window=100,
            atr_period=10,
            risk_per_trade=0.01
        )
        self.assertEqual(trend_strategy.parameters['short_window'], 10)
        self.assertEqual(trend_strategy.parameters['risk_per_trade'], 0.01)
        
        # Test mean reversion strategy
        mean_strategy = MeanReversionStrategy(
            window=30,
            std_dev=2.5,
            min_holding_period=10,
            max_holding_period=30
        )
        self.assertEqual(mean_strategy.parameters['window'], 30)
        self.assertEqual(mean_strategy.parameters['std_dev'], 2.5)
        
        # Test momentum strategy
        momentum_strategy = MomentumStrategy(
            lookback_period=30,
            volume_threshold=2.0,
            max_positions=3
        )
        self.assertEqual(momentum_strategy.parameters['lookback_period'], 30)
        self.assertEqual(momentum_strategy.parameters['max_positions'], 3)
        
        # Test risk-aware strategy
        risk_strategy = RiskAwareStrategy(
            volatility_window=30,
            max_risk_per_trade=0.01,
            stop_loss_atr=3.0,
            trailing_stop=False
        )
        self.assertEqual(risk_strategy.parameters['volatility_window'], 30)
        self.assertEqual(risk_strategy.parameters['trailing_stop'], False)
        
if __name__ == '__main__':
    unittest.main() 