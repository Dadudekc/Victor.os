"""
Core backtesting engine implementation.

This module provides the main BacktestEngine class that orchestrates the backtesting process,
managing data loading, strategy execution, and result analysis.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .data import DataManager
from .strategies import StrategyBase
from .analysis import PerformanceAnalyzer
from .utils import ValidationError, BacktestError

logger = logging.getLogger(__name__)

class BacktestEngine:
    """Main backtesting engine for strategy optimization."""
    
    def __init__(self, data_dir: Union[str, Path], results_dir: Union[str, Path]):
        """
        Initialize the backtesting engine.
        
        Args:
            data_dir: Directory containing historical data
            results_dir: Directory for storing backtest results
        """
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.data_manager = DataManager(self.data_dir)
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Create results directory if it doesn't exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def run_backtest(
        self,
        strategy: StrategyBase,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000.0,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a backtest for the given strategy.
        
        Args:
            strategy: Strategy to backtest
            start_date: Start date for backtest period
            end_date: End date for backtest period
            initial_capital: Initial capital for the strategy
            parameters: Optional strategy parameters
            
        Returns:
            Dictionary containing backtest results
        """
        try:
            # Validate dates
            if start_date >= end_date:
                raise ValidationError("Start date must be before end date")
                
            # Load historical data
            data = self.data_manager.load_data(start_date, end_date)
            if data.empty:
                raise BacktestError("No data available for the specified period")
                
            # Initialize strategy
            strategy.initialize(parameters or {})
            
            # Run simulation
            results = strategy.run(data, initial_capital)
            
            # Analyze performance
            performance = self.performance_analyzer.analyze(results)
            
            # Save results
            self._save_results(strategy, performance, parameters)
            
            return {
                'strategy_name': strategy.name,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'initial_capital': initial_capital,
                'parameters': parameters,
                'performance': performance,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            raise BacktestError(f"Backtest failed: {str(e)}")
            
    def _save_results(
        self,
        strategy: StrategyBase,
        performance: Dict[str, Any],
        parameters: Optional[Dict[str, Any]]
    ) -> None:
        """
        Save backtest results to disk.
        
        Args:
            strategy: Strategy that was tested
            performance: Performance metrics
            parameters: Strategy parameters used
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{strategy.name}_{timestamp}.json"
        filepath = self.results_dir / filename
        
        results = {
            'strategy_name': strategy.name,
            'timestamp': timestamp,
            'parameters': parameters,
            'performance': performance
        }
        
        try:
            import json
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved backtest results to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")
            raise BacktestError(f"Failed to save results: {str(e)}")
            
    def load_results(self, strategy_name: str) -> List[Dict[str, Any]]:
        """
        Load previous backtest results for a strategy.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            List of previous backtest results
        """
        results = []
        try:
            import json
            for filepath in self.results_dir.glob(f"{strategy_name}_*.json"):
                with open(filepath, 'r') as f:
                    results.append(json.load(f))
            return results
        except Exception as e:
            logger.error(f"Failed to load results: {str(e)}")
            raise BacktestError(f"Failed to load results: {str(e)}") 