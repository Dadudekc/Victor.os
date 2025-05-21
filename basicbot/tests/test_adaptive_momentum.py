"""
test_adaptive_momentum.py - Tests for Adaptive Momentum Strategy

This module contains tests for the AdaptiveMomentumStrategy class:
- Technical indicator calculations
- Signal generation
- Risk parameter adjustments
- Performance metrics
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

from basicbot.strategies.adaptive_momentum import AdaptiveMomentumStrategy
from basicbot.logger import setup_logging

class TestAdaptiveMomentumStrategy(unittest.TestCase):
    """Test cases for AdaptiveMomentumStrategy."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.logger = setup_logging("test_adaptive_momentum")
        cls.strategy = AdaptiveMomentumStrategy(
            symbol="TEST",
            timeframe="1D",
            logger=cls.logger
        )
        
        # Generate test data
        cls.test_data = cls._generate_test_data()
    
    @classmethod
    def _generate_test_data(cls) -> pd.DataFrame:
        """Generate test price data with known patterns."""
        # Create date range
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=100),
            end=datetime.now(),
            freq='D'
        )
        
        # Generate price data
        np.random.seed(42)  # For reproducibility
        n = len(dates)
        
        # Generate base price series with trend
        base_price = np.linspace(100, 150, n) + np.random.normal(0, 2, n)
        
        # Create DataFrame
        df = pd.DataFrame({
            'date': dates,
            'open': base_price,
            'high': base_price + np.random.uniform(1, 3, n),
            'low': base_price - np.random.uniform(1, 3, n),
            'close': base_price + np.random.normal(0, 1, n),
            'volume': np.random.uniform(1000, 5000, n)
        })
        
        # Add some known patterns
        # Uptrend
        df.loc[20:40, 'close'] = df.loc[20:40, 'close'] * 1.1
        # Downtrend
        df.loc[60:80, 'close'] = df.loc[60:80, 'close'] * 0.9
        
        return df
    
    def test_calculate_indicators(self):
        """Test technical indicator calculations."""
        # Calculate indicators
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Check required columns
        required_columns = [
            'SMA_short', 'SMA_long', 'RSI', 'MACD', 'MACD_signal',
            'ATR', 'VWAP', 'volatility', 'trend_strength', 'momentum',
            'volume_ma', 'volume_ratio', 'price_distance', 'rsi_ma',
            'macd_hist', 'macd_hist_ma'
        ]
        for col in required_columns:
            self.assertIn(col, df.columns)
        
        # Check indicator values
        self.assertTrue(df['RSI'].between(0, 100).all())
        self.assertTrue(df['volatility'].notna().all())
        self.assertTrue(df['trend_strength'].notna().all())
        self.assertTrue(df['momentum'].notna().all())
        self.assertTrue(df['volume_ratio'].notna().all())
        self.assertTrue(df['price_distance'].notna().all())
        self.assertTrue(df['rsi_ma'].notna().all())
        self.assertTrue(df['macd_hist'].notna().all())
        self.assertTrue(df['macd_hist_ma'].notna().all())
    
    def test_generate_signals(self):
        """Test signal generation."""
        # Calculate indicators
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Generate signals
        signals = self.strategy.generate_signals(df)
        
        # Check signal values
        valid_signals = ['BUY', 'SELL', 'HOLD']
        self.assertTrue(signals.isin(valid_signals).all())
        
        # Check signal distribution
        signal_counts = signals.value_counts()
        self.assertGreater(signal_counts['HOLD'], 0)
    
    def test_signal_strength(self):
        """Test signal strength calculation."""
        # Calculate indicators
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Test signal strength for each row
        for i in range(len(df)):
            current = df.iloc[i]
            strength = self.strategy._calculate_signal_strength(current)
            
            # Check strength is between 0 and 1
            self.assertTrue(0 <= strength <= 1)
    
    def test_buy_signal_conditions(self):
        """Test buy signal conditions."""
        # Calculate indicators
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Test buy signals
        for i in range(1, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            strength = self.strategy._calculate_signal_strength(current)
            
            is_buy = self.strategy._is_buy_signal(current, previous, strength)
            
            # If it's a buy signal, verify conditions
            if is_buy:
                self.assertTrue(current['close'] > current['VWAP'])
                self.assertTrue(
                    (current['MACD'] > current['MACD_signal'] and
                     previous['MACD'] <= previous['MACD_signal']) or
                    (current['RSI'] < self.strategy.rsiOversold and
                     current['RSI'] > current['rsi_ma'])
                )
                self.assertTrue(current['macd_hist'] > current['macd_hist_ma'])
                self.assertTrue(current['volume_ratio'] > 1.2)
                self.assertTrue(current['momentum'] > 0)
                self.assertTrue(current['volatility'] < self.strategy.volatility_threshold)
                self.assertTrue(strength > 0.6)
    
    def test_sell_signal_conditions(self):
        """Test sell signal conditions."""
        # Calculate indicators
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Test sell signals
        for i in range(1, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            strength = self.strategy._calculate_signal_strength(current)
            
            is_sell = self.strategy._is_sell_signal(current, previous, strength)
            
            # If it's a sell signal, verify conditions
            if is_sell:
                self.assertTrue(current['close'] < current['VWAP'])
                self.assertTrue(
                    (current['MACD'] < current['MACD_signal'] and
                     previous['MACD'] >= previous['MACD_signal']) or
                    (current['RSI'] > self.strategy.rsiOverbought and
                     current['RSI'] < current['rsi_ma'])
                )
                self.assertTrue(current['macd_hist'] < current['macd_hist_ma'])
                self.assertTrue(current['volume_ratio'] > 1.2)
                self.assertTrue(current['momentum'] < 0)
                self.assertTrue(
                    current['volatility'] > self.strategy.volatility_threshold or
                    strength > 0.7
                )
    
    def test_risk_parameter_adjustment(self):
        """Test risk parameter adjustments."""
        # Calculate indicators
        df = self.strategy.calculate_indicators(self.test_data)
        
        # Store initial risk percentage
        initial_risk = self.strategy.risk_manager.max_risk_pct
        
        # Adjust risk parameters
        self.strategy.adjust_risk_parameters(df)
        
        # Check risk percentage is within bounds
        self.assertTrue(
            self.strategy.min_risk_pct <=
            self.strategy.risk_manager.max_risk_pct <=
            self.strategy.max_risk_pct
        )
        
        # Verify risk adjustment based on volatility
        current = df.iloc[-1]
        if current['volatility'] > self.strategy.volatility_threshold:
            self.assertLess(
                self.strategy.risk_manager.max_risk_pct,
                initial_risk
            )
        elif current['volatility'] < self.strategy.volatility_threshold * 0.5:
            self.assertGreater(
                self.strategy.risk_manager.max_risk_pct,
                initial_risk
            )
        
        # Verify risk adjustment based on volume
        if current['volume_ratio'] > 1.5:
            self.assertGreater(
                self.strategy.risk_manager.max_risk_pct,
                initial_risk
            )
        elif current['volume_ratio'] < 0.8:
            self.assertLess(
                self.strategy.risk_manager.max_risk_pct,
                initial_risk
            )

if __name__ == '__main__':
    unittest.main() 