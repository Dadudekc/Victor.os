"""
Test module for backtesting framework.

This module contains comprehensive test cases for all components of the
backtesting framework.
"""

import unittest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
import json

from dreamos.backtesting import (
    BacktestEngine,
    DataManager,
    StrategyBase,
    MovingAverageCrossover,
    MeanReversion,
    PerformanceAnalyzer
)
from dreamos.backtesting.utils import (
    ValidationError,
    BacktestError,
    DataError,
    validate_date_range,
    validate_strategy_parameters,
    save_results,
    load_results,
    format_metrics
)

class TestBacktestEngine(unittest.TestCase):
    """Test cases for BacktestEngine class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.results_dir = Path(self.temp_dir) / "results"
        self.data_dir.mkdir()
        self.results_dir.mkdir()
        
        # Create sample market data
        self.create_sample_data()
        
        # Initialize engine
        self.engine = BacktestEngine(
            data_dir=self.data_dir,
            results_dir=self.results_dir
        )
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        
    def create_sample_data(self):
        """Create sample market data for testing."""
        # Create sample price data
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.normal(150, 10, len(dates)),
            'GOOGL': np.random.normal(2800, 100, len(dates)),
            'MSFT': np.random.normal(300, 15, len(dates))
        }, index=dates)
        
        # Save to CSV
        prices.to_csv(self.data_dir / "market_data.csv")
        
    def test_initialization(self):
        """Test engine initialization."""
        self.assertEqual(self.engine.data_dir, self.data_dir)
        self.assertEqual(self.engine.results_dir, self.results_dir)
        self.assertTrue(self.results_dir.exists())
        
    def test_run_backtest(self):
        """Test running a backtest."""
        # Create strategy
        strategy = MovingAverageCrossover(
            name="MA Crossover",
            parameters={'short_window': 20, 'long_window': 50}
        )
        
        # Run backtest
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        initial_capital = 100000
        
        results = self.engine.run_backtest(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
        
        # Verify results
        self.assertIn('returns', results)
        self.assertIn('portfolio_value', results)
        self.assertIn('trades', results)
        self.assertIn('positions', results)
        
    def test_invalid_date_range(self):
        """Test running backtest with invalid date range."""
        strategy = MovingAverageCrossover(
            name="MA Crossover",
            parameters={'short_window': 20, 'long_window': 50}
        )
        
        with self.assertRaises(ValidationError):
            self.engine.run_backtest(
                strategy=strategy,
                start_date=datetime(2023, 12, 31),
                end_date=datetime(2023, 1, 1),
                initial_capital=100000
            )

class TestDataManager(unittest.TestCase):
    """Test cases for DataManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir()
        
        # Create sample data
        self.create_sample_data()
        
        # Initialize manager
        self.manager = DataManager(data_dir=self.data_dir)
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        
    def create_sample_data(self):
        """Create sample data for testing."""
        # Create market data
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.normal(150, 10, len(dates)),
            'GOOGL': np.random.normal(2800, 100, len(dates)),
            'MSFT': np.random.normal(300, 15, len(dates))
        }, index=dates)
        
        # Create fundamental data
        fundamentals = {
            'AAPL': {
                'pe_ratio': 25.5,
                'market_cap': 2000000000000,
                'dividend_yield': 0.02
            },
            'GOOGL': {
                'pe_ratio': 30.2,
                'market_cap': 1800000000000,
                'dividend_yield': 0.0
            },
            'MSFT': {
                'pe_ratio': 28.7,
                'market_cap': 1900000000000,
                'dividend_yield': 0.01
            }
        }
        
        # Save data
        prices.to_csv(self.data_dir / "market_data.csv")
        with open(self.data_dir / "fundamental_data.json", 'w') as f:
            json.dump(fundamentals, f)
            
    def test_load_market_data(self):
        """Test loading market data."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        symbols = ['AAPL', 'GOOGL']
        
        data = self.manager.load_data(
            start_date=start_date,
            end_date=end_date,
            data_type='market',
            symbols=symbols
        )
        
        self.assertIsInstance(data, pd.DataFrame)
        self.assertEqual(len(data.columns), 2)
        self.assertTrue(all(symbol in data.columns for symbol in symbols))
        
    def test_load_fundamental_data(self):
        """Test loading fundamental data."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        symbols = ['AAPL', 'GOOGL']
        
        data = self.manager.load_data(
            start_date=start_date,
            end_date=end_date,
            data_type='fundamental',
            symbols=symbols
        )
        
        self.assertIsInstance(data, dict)
        self.assertEqual(len(data), 2)
        self.assertTrue(all(symbol in data for symbol in symbols))
        
    def test_preprocess_data(self):
        """Test data preprocessing."""
        # Create sample data
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        prices = pd.DataFrame({
            'AAPL': np.random.normal(150, 10, len(dates)),
            'GOOGL': np.random.normal(2800, 100, len(dates))
        }, index=dates)
        
        # Preprocess data
        processed_data = self.manager.preprocess_data(prices)
        
        self.assertIsInstance(processed_data, pd.DataFrame)
        self.assertIn('returns', processed_data.columns)
        self.assertIn('ma_20', processed_data.columns)
        self.assertIn('ma_50', processed_data.columns)

class TestStrategies(unittest.TestCase):
    """Test cases for strategy classes."""
    
    def setUp(self):
        """Set up test environment."""
        # Create sample data
        self.dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        self.prices = pd.DataFrame({
            'AAPL': np.random.normal(150, 10, len(self.dates)),
            'GOOGL': np.random.normal(2800, 100, len(self.dates))
        }, index=self.dates)
        
    def test_moving_average_crossover(self):
        """Test MovingAverageCrossover strategy."""
        strategy = MovingAverageCrossover(
            name="MA Crossover",
            parameters={'short_window': 20, 'long_window': 50}
        )
        
        # Run strategy
        results = strategy.run(self.prices)
        
        self.assertIn('signals', results)
        self.assertIn('positions', results)
        self.assertIn('trades', results)
        
    def test_mean_reversion(self):
        """Test MeanReversion strategy."""
        strategy = MeanReversion(
            name="Mean Reversion",
            parameters={'window': 20, 'std_dev': 2.0}
        )
        
        # Run strategy
        results = strategy.run(self.prices)
        
        self.assertIn('signals', results)
        self.assertIn('positions', results)
        self.assertIn('trades', results)

class TestPerformanceAnalyzer(unittest.TestCase):
    """Test cases for PerformanceAnalyzer class."""
    
    def setUp(self):
        """Set up test environment."""
        self.analyzer = PerformanceAnalyzer()
        
        # Create sample results
        self.results = {
            'returns': pd.Series(np.random.normal(0.001, 0.02, 252)),
            'portfolio_value': pd.Series(np.random.normal(100000, 5000, 252)),
            'trades': [
                {
                    'action': 'buy',
                    'symbol': 'AAPL',
                    'quantity': 100,
                    'price': 150.0,
                    'timestamp': '2023-01-01T10:00:00'
                },
                {
                    'action': 'sell',
                    'symbol': 'AAPL',
                    'quantity': 100,
                    'price': 155.0,
                    'timestamp': '2023-01-02T10:00:00'
                }
            ]
        }
        
    def test_analyze(self):
        """Test performance analysis."""
        metrics = self.analyzer.analyze(self.results)
        
        self.assertIn('total_return', metrics)
        self.assertIn('annualized_return', metrics)
        self.assertIn('sharpe_ratio', metrics)
        self.assertIn('sortino_ratio', metrics)
        self.assertIn('max_drawdown', metrics)
        self.assertIn('volatility', metrics)
        self.assertIn('win_rate', metrics)
        self.assertIn('profit_factor', metrics)
        self.assertIn('average_trade', metrics)
        self.assertIn('trade_statistics', metrics)
        
    def test_calculate_metrics(self):
        """Test individual metric calculations."""
        # Test total return
        total_return = self.analyzer._calculate_total_return(
            self.results['portfolio_value']
        )
        self.assertIsInstance(total_return, float)
        
        # Test Sharpe ratio
        sharpe = self.analyzer._calculate_sharpe_ratio(
            self.results['returns']
        )
        self.assertIsInstance(sharpe, float)
        
        # Test win rate
        win_rate = self.analyzer._calculate_win_rate(
            self.results['trades']
        )
        self.assertIsInstance(win_rate, float)
        self.assertTrue(0 <= win_rate <= 1)

class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""
    
    def test_validate_date_range(self):
        """Test date range validation."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        # Valid date range
        validate_date_range(start_date, end_date)
        
        # Invalid date range
        with self.assertRaises(ValidationError):
            validate_date_range(end_date, start_date)
            
    def test_validate_strategy_parameters(self):
        """Test strategy parameter validation."""
        # Valid parameters
        valid_params = {
            'short_window': 20,
            'long_window': 50,
            'threshold': 0.02
        }
        validate_strategy_parameters(valid_params)
        
        # Invalid parameters
        invalid_params = {
            123: 'invalid',
            'window': object()
        }
        with self.assertRaises(ValidationError):
            validate_strategy_parameters(invalid_params)
            
    def test_save_load_results(self):
        """Test saving and loading results."""
        # Create sample results
        results = {
            'returns': [0.01, -0.02, 0.03],
            'portfolio_value': [100000, 98000, 100940],
            'trades': [
                {
                    'action': 'buy',
                    'symbol': 'AAPL',
                    'quantity': 100,
                    'price': 150.0,
                    'timestamp': '2023-01-01T10:00:00'
                }
            ]
        }
        
        # Save results
        with tempfile.NamedTemporaryFile(suffix='.json') as f:
            save_results(results, Path(f.name))
            
            # Load results
            loaded_results = load_results(Path(f.name))
            
            # Verify loaded results
            self.assertEqual(loaded_results['returns'], results['returns'])
            self.assertEqual(loaded_results['portfolio_value'], results['portfolio_value'])
            self.assertEqual(len(loaded_results['trades']), len(results['trades']))
            
    def test_format_metrics(self):
        """Test metrics formatting."""
        metrics = {
            'total_return': 0.15,
            'annualized_return': 0.12,
            'sharpe_ratio': 1.5,
            'sortino_ratio': 2.0,
            'max_drawdown': 0.1,
            'volatility': 0.2,
            'win_rate': 0.6,
            'profit_factor': 1.8,
            'average_trade': 100.0,
            'trade_statistics': {
                'total_trades': 100,
                'winning_trades': 60,
                'losing_trades': 40,
                'avg_win': 150.0,
                'avg_loss': -100.0,
                'largest_win': 500.0,
                'largest_loss': -300.0,
                'avg_trade_duration': 24.0
            }
        }
        
        formatted = format_metrics(metrics)
        
        self.assertIsInstance(formatted, str)
        self.assertIn('Performance Metrics:', formatted)
        self.assertIn('Trade Statistics:', formatted)
        self.assertIn('15.00%', formatted)  # Total Return
        self.assertIn('1.50', formatted)    # Sharpe Ratio
        self.assertIn('60.00%', formatted)  # Win Rate

if __name__ == '__main__':
    unittest.main() 