"""
Performance analysis module for backtesting framework.

This module provides the PerformanceAnalyzer class for calculating and analyzing
backtest results, including various performance metrics and risk measures.
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from scipy import stats

from .utils import ValidationError, BacktestError

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Analyzes backtest results and calculates performance metrics."""
    
    def analyze(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze backtest results and calculate performance metrics.
        
        Args:
            results: Dictionary containing backtest results
            
        Returns:
            Dictionary containing performance metrics
        """
        try:
            # Extract data
            returns = pd.Series(results['returns'])
            portfolio_value = pd.Series(results['portfolio_value'])
            trades = results['trades']
            
            # Calculate metrics
            metrics = {
                'total_return': self._calculate_total_return(portfolio_value),
                'annualized_return': self._calculate_annualized_return(returns),
                'sharpe_ratio': self._calculate_sharpe_ratio(returns),
                'sortino_ratio': self._calculate_sortino_ratio(returns),
                'max_drawdown': self._calculate_max_drawdown(portfolio_value),
                'volatility': self._calculate_volatility(returns),
                'win_rate': self._calculate_win_rate(trades),
                'profit_factor': self._calculate_profit_factor(trades),
                'average_trade': self._calculate_average_trade(trades),
                'trade_statistics': self._calculate_trade_statistics(trades)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to analyze results: {str(e)}")
            raise BacktestError(f"Failed to analyze results: {str(e)}")
            
    def _calculate_total_return(self, portfolio_value: pd.Series) -> float:
        """
        Calculate total return.
        
        Args:
            portfolio_value: Series of portfolio values
            
        Returns:
            Total return as a decimal
        """
        try:
            return (portfolio_value.iloc[-1] / portfolio_value.iloc[0]) - 1
        except Exception as e:
            logger.error(f"Failed to calculate total return: {str(e)}")
            raise BacktestError(f"Failed to calculate total return: {str(e)}")
            
    def _calculate_annualized_return(self, returns: pd.Series) -> float:
        """
        Calculate annualized return.
        
        Args:
            returns: Series of returns
            
        Returns:
            Annualized return as a decimal
        """
        try:
            total_return = (1 + returns).prod() - 1
            years = len(returns) / 252  # Assuming 252 trading days per year
            return (1 + total_return) ** (1 / years) - 1
        except Exception as e:
            logger.error(f"Failed to calculate annualized return: {str(e)}")
            raise BacktestError(f"Failed to calculate annualized return: {str(e)}")
            
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            returns: Series of returns
            
        Returns:
            Sharpe ratio
        """
        try:
            excess_returns = returns - 0.02/252  # Assuming 2% risk-free rate
            return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        except Exception as e:
            logger.error(f"Failed to calculate Sharpe ratio: {str(e)}")
            raise BacktestError(f"Failed to calculate Sharpe ratio: {str(e)}")
            
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """
        Calculate Sortino ratio.
        
        Args:
            returns: Series of returns
            
        Returns:
            Sortino ratio
        """
        try:
            excess_returns = returns - 0.02/252  # Assuming 2% risk-free rate
            downside_returns = excess_returns[excess_returns < 0]
            downside_std = np.sqrt(np.mean(downside_returns ** 2))
            return np.sqrt(252) * excess_returns.mean() / downside_std
        except Exception as e:
            logger.error(f"Failed to calculate Sortino ratio: {str(e)}")
            raise BacktestError(f"Failed to calculate Sortino ratio: {str(e)}")
            
    def _calculate_max_drawdown(self, portfolio_value: pd.Series) -> float:
        """
        Calculate maximum drawdown.
        
        Args:
            portfolio_value: Series of portfolio values
            
        Returns:
            Maximum drawdown as a decimal
        """
        try:
            rolling_max = portfolio_value.expanding().max()
            drawdowns = portfolio_value / rolling_max - 1
            return abs(drawdowns.min())
        except Exception as e:
            logger.error(f"Failed to calculate max drawdown: {str(e)}")
            raise BacktestError(f"Failed to calculate max drawdown: {str(e)}")
            
    def _calculate_volatility(self, returns: pd.Series) -> float:
        """
        Calculate annualized volatility.
        
        Args:
            returns: Series of returns
            
        Returns:
            Annualized volatility as a decimal
        """
        try:
            return returns.std() * np.sqrt(252)
        except Exception as e:
            logger.error(f"Failed to calculate volatility: {str(e)}")
            raise BacktestError(f"Failed to calculate volatility: {str(e)}")
            
    def _calculate_win_rate(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate win rate.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Win rate as a decimal
        """
        try:
            if not trades:
                return 0.0
                
            profitable_trades = sum(1 for trade in trades if trade['action'] == 'sell' and
                                  trade['quantity'] * trade['price'] > 0)
            return profitable_trades / len(trades)
        except Exception as e:
            logger.error(f"Failed to calculate win rate: {str(e)}")
            raise BacktestError(f"Failed to calculate win rate: {str(e)}")
            
    def _calculate_profit_factor(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate profit factor.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Profit factor
        """
        try:
            if not trades:
                return 0.0
                
            gross_profit = sum(trade['quantity'] * trade['price']
                             for trade in trades if trade['action'] == 'sell' and
                             trade['quantity'] * trade['price'] > 0)
            gross_loss = abs(sum(trade['quantity'] * trade['price']
                               for trade in trades if trade['action'] == 'sell' and
                               trade['quantity'] * trade['price'] < 0))
                               
            return gross_profit / gross_loss if gross_loss != 0 else float('inf')
        except Exception as e:
            logger.error(f"Failed to calculate profit factor: {str(e)}")
            raise BacktestError(f"Failed to calculate profit factor: {str(e)}")
            
    def _calculate_average_trade(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate average trade profit/loss.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Average trade profit/loss
        """
        try:
            if not trades:
                return 0.0
                
            trade_pnls = [trade['quantity'] * trade['price']
                         for trade in trades if trade['action'] == 'sell']
            return np.mean(trade_pnls)
        except Exception as e:
            logger.error(f"Failed to calculate average trade: {str(e)}")
            raise BacktestError(f"Failed to calculate average trade: {str(e)}")
            
    def _calculate_trade_statistics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate detailed trade statistics.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Dictionary containing trade statistics
        """
        try:
            if not trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'largest_win': 0.0,
                    'largest_loss': 0.0,
                    'avg_trade_duration': 0.0
                }
                
            # Calculate basic statistics
            trade_pnls = [trade['quantity'] * trade['price']
                         for trade in trades if trade['action'] == 'sell']
            winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
            losing_trades = [pnl for pnl in trade_pnls if pnl < 0]
            
            # Calculate trade durations
            trade_durations = []
            for i in range(0, len(trades)-1, 2):
                if trades[i]['action'] == 'buy' and trades[i+1]['action'] == 'sell':
                    duration = (pd.to_datetime(trades[i+1]['timestamp']) -
                              pd.to_datetime(trades[i]['timestamp'])).total_seconds() / 3600
                    trade_durations.append(duration)
                    
            return {
                'total_trades': len(trade_pnls),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'avg_win': np.mean(winning_trades) if winning_trades else 0.0,
                'avg_loss': np.mean(losing_trades) if losing_trades else 0.0,
                'largest_win': max(winning_trades) if winning_trades else 0.0,
                'largest_loss': min(losing_trades) if losing_trades else 0.0,
                'avg_trade_duration': np.mean(trade_durations) if trade_durations else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate trade statistics: {str(e)}")
            raise BacktestError(f"Failed to calculate trade statistics: {str(e)}") 