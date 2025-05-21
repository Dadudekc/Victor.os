"""
Utility module for backtesting framework.

This module provides error handling classes and common helper functions used
throughout the backtesting framework.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

class BacktestError(Exception):
    """Raised when a backtest operation fails."""
    pass

class DataError(Exception):
    """Raised when there are issues with data loading or processing."""
    pass

def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """
    Validate that the date range is valid.
    
    Args:
        start_date: Start date of the backtest period
        end_date: End date of the backtest period
        
    Raises:
        ValidationError: If the date range is invalid
    """
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        raise ValidationError("Start and end dates must be datetime objects")
        
    if start_date >= end_date:
        raise ValidationError("Start date must be before end date")
        
    if end_date > datetime.now():
        raise ValidationError("End date cannot be in the future")

def validate_strategy_parameters(parameters: Dict[str, Any]) -> None:
    """
    Validate strategy parameters.
    
    Args:
        parameters: Dictionary of strategy parameters
        
    Raises:
        ValidationError: If parameters are invalid
    """
    if not isinstance(parameters, dict):
        raise ValidationError("Parameters must be a dictionary")
        
    for key, value in parameters.items():
        if not isinstance(key, str):
            raise ValidationError("Parameter keys must be strings")
            
        if not isinstance(value, (int, float, str, bool)):
            raise ValidationError(f"Invalid parameter value type for {key}")

def save_results(results: Dict[str, Any], filepath: Path) -> None:
    """
    Save backtest results to a JSON file.
    
    Args:
        results: Dictionary containing backtest results
        filepath: Path to save the results file
        
    Raises:
        BacktestError: If saving results fails
    """
    try:
        # Convert datetime objects to strings
        serializable_results = _make_serializable(results)
        
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=4)
            
    except Exception as e:
        logger.error(f"Failed to save results: {str(e)}")
        raise BacktestError(f"Failed to save results: {str(e)}")

def load_results(filepath: Path) -> Dict[str, Any]:
    """
    Load backtest results from a JSON file.
    
    Args:
        filepath: Path to the results file
        
    Returns:
        Dictionary containing backtest results
        
    Raises:
        BacktestError: If loading results fails
    """
    try:
        with open(filepath, 'r') as f:
            results = json.load(f)
            
        # Convert string timestamps back to datetime objects
        return _convert_timestamps(results)
        
    except Exception as e:
        logger.error(f"Failed to load results: {str(e)}")
        raise BacktestError(f"Failed to load results: {str(e)}")

def _make_serializable(obj: Any) -> Any:
    """
    Convert objects to JSON-serializable format.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON-serializable object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _make_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)

def _convert_timestamps(obj: Any) -> Any:
    """
    Convert ISO format timestamps back to datetime objects.
    
    Args:
        obj: Object to convert
        
    Returns:
        Object with timestamps converted to datetime
    """
    if isinstance(obj, dict):
        return {key: _convert_timestamps(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_timestamps(item) for item in obj]
    elif isinstance(obj, str):
        try:
            return datetime.fromisoformat(obj)
        except ValueError:
            return obj
    else:
        return obj

def format_metrics(metrics: Dict[str, Any]) -> str:
    """
    Format performance metrics for display.
    
    Args:
        metrics: Dictionary of performance metrics
        
    Returns:
        Formatted string of metrics
    """
    try:
        lines = []
        lines.append("Performance Metrics:")
        lines.append("-" * 50)
        
        # Format main metrics
        main_metrics = {
            'Total Return': f"{metrics['total_return']:.2%}",
            'Annualized Return': f"{metrics['annualized_return']:.2%}",
            'Sharpe Ratio': f"{metrics['sharpe_ratio']:.2f}",
            'Sortino Ratio': f"{metrics['sortino_ratio']:.2f}",
            'Max Drawdown': f"{metrics['max_drawdown']:.2%}",
            'Volatility': f"{metrics['volatility']:.2%}",
            'Win Rate': f"{metrics['win_rate']:.2%}",
            'Profit Factor': f"{metrics['profit_factor']:.2f}",
            'Average Trade': f"${metrics['average_trade']:.2f}"
        }
        
        for key, value in main_metrics.items():
            lines.append(f"{key:<20}: {value}")
            
        # Format trade statistics
        stats = metrics['trade_statistics']
        lines.append("\nTrade Statistics:")
        lines.append("-" * 50)
        
        trade_stats = {
            'Total Trades': stats['total_trades'],
            'Winning Trades': stats['winning_trades'],
            'Losing Trades': stats['losing_trades'],
            'Average Win': f"${stats['avg_win']:.2f}",
            'Average Loss': f"${stats['avg_loss']:.2f}",
            'Largest Win': f"${stats['largest_win']:.2f}",
            'Largest Loss': f"${stats['largest_loss']:.2f}",
            'Avg Trade Duration': f"{stats['avg_trade_duration']:.1f} hours"
        }
        
        for key, value in trade_stats.items():
            lines.append(f"{key:<20}: {value}")
            
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to format metrics: {str(e)}")
        raise BacktestError(f"Failed to format metrics: {str(e)}") 