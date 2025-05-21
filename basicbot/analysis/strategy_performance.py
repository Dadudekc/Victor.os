"""
strategy_performance.py - Strategy Performance Analysis

This module provides tools for analyzing trading strategy performance:
- Backtest results analysis
- Performance metrics calculation
- Risk-adjusted return analysis
- Drawdown analysis
- Trade statistics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

from basicbot.strategies.adaptive_momentum import AdaptiveMomentumStrategy
from basicbot.logger import setup_logging

class StrategyPerformance:
    """
    Analyze and visualize trading strategy performance.
    """
    
    def __init__(
        self,
        strategy: AdaptiveMomentumStrategy,
        initial_capital: float = 10000.0,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize performance analyzer.
        
        Args:
            strategy: Trading strategy instance
            initial_capital: Initial capital for backtesting
            logger: Logger instance
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.logger = logger or setup_logging("strategy_performance")
        
        # Performance metrics
        self.metrics = {}
        self.trades = []
        self.equity_curve = None
    
    def analyze_backtest(
        self,
        df: pd.DataFrame,
        commission: float = 0.001,
        slippage: float = 0.001
    ) -> Dict[str, float]:
        """
        Analyze backtest results and calculate performance metrics.
        
        Args:
            df: DataFrame with price data and signals
            commission: Commission per trade (percentage)
            slippage: Slippage per trade (percentage)
            
        Returns:
            Dictionary of performance metrics
        """
        self.logger.info("Analyzing backtest results...")
        
        # Calculate indicators and signals
        df = self.strategy.calculate_indicators(df)
        signals = self.strategy.generate_signals(df)
        
        # Initialize tracking variables
        position = 0
        entry_price = 0
        entry_date = None
        equity = self.initial_capital
        equity_curve = [equity]
        trades = []
        
        # Process each bar
        for i in range(1, len(df)):
            current = df.iloc[i]
            signal = signals.iloc[i]
            
            # Calculate trade costs
            trade_cost = current['close'] * (commission + slippage)
            
            # Process signals
            if signal == 'BUY' and position <= 0:
                # Close short position if exists
                if position < 0:
                    pnl = (entry_price - current['close']) * abs(position) - trade_cost
                    equity += pnl
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': current.name,
                        'entry_price': entry_price,
                        'exit_price': current['close'],
                        'position': position,
                        'pnl': pnl,
                        'return': pnl / (entry_price * abs(position))
                    })
                
                # Open long position
                position = 1
                entry_price = current['close'] + trade_cost
                entry_date = current.name
                
            elif signal == 'SELL' and position >= 0:
                # Close long position if exists
                if position > 0:
                    pnl = (current['close'] - entry_price) * position - trade_cost
                    equity += pnl
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': current.name,
                        'entry_price': entry_price,
                        'exit_price': current['close'],
                        'position': position,
                        'pnl': pnl,
                        'return': pnl / (entry_price * position)
                    })
                
                # Open short position
                position = -1
                entry_price = current['close'] - trade_cost
                entry_date = current.name
            
            # Update equity curve
            if position != 0:
                current_pnl = (current['close'] - entry_price) * position
                equity_curve.append(equity + current_pnl)
            else:
                equity_curve.append(equity)
        
        # Store results
        self.trades = pd.DataFrame(trades)
        self.equity_curve = pd.Series(equity_curve, index=df.index)
        
        # Calculate performance metrics
        self.metrics = self._calculate_metrics()
        
        return self.metrics
    
    def _calculate_metrics(self) -> Dict[str, float]:
        """
        Calculate performance metrics from backtest results.
        
        Returns:
            Dictionary of performance metrics
        """
        if self.trades.empty or self.equity_curve is None:
            return {}
        
        # Calculate returns
        returns = self.equity_curve.pct_change().dropna()
        
        # Basic metrics
        total_return = (self.equity_curve.iloc[-1] / self.initial_capital) - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        daily_volatility = returns.std()
        annual_volatility = daily_volatility * np.sqrt(252)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility != 0 else 0
        
        # Drawdown analysis
        rolling_max = self.equity_curve.expanding().max()
        drawdowns = (self.equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        # Trade statistics
        win_rate = (self.trades['pnl'] > 0).mean()
        avg_win = self.trades[self.trades['pnl'] > 0]['pnl'].mean()
        avg_loss = self.trades[self.trades['pnl'] < 0]['pnl'].mean()
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # Risk metrics
        var_95 = returns.quantile(0.05)
        cvar_95 = returns[returns <= var_95].mean()
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'total_trades': len(self.trades),
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }
    
    def plot_performance(self, save_path: Optional[str] = None) -> None:
        """
        Plot performance charts.
        
        Args:
            save_path: Path to save plots (if None, display instead)
        """
        if self.equity_curve is None or self.trades.empty:
            self.logger.error("No performance data to plot")
            return
        
        # Create figure with subplots
        fig, axes = plt.subplots(3, 1, figsize=(12, 15))
        
        # Plot equity curve
        self.equity_curve.plot(ax=axes[0], title='Equity Curve')
        axes[0].set_ylabel('Equity')
        axes[0].grid(True)
        
        # Plot drawdowns
        rolling_max = self.equity_curve.expanding().max()
        drawdowns = (self.equity_curve - rolling_max) / rolling_max
        drawdowns.plot(ax=axes[1], title='Drawdowns')
        axes[1].set_ylabel('Drawdown')
        axes[1].grid(True)
        
        # Plot trade returns
        self.trades['return'].hist(ax=axes[2], bins=50, title='Trade Returns Distribution')
        axes[2].set_xlabel('Return')
        axes[2].set_ylabel('Frequency')
        axes[2].grid(True)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save or show plot
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
    
    def generate_report(self) -> str:
        """
        Generate performance report.
        
        Returns:
            Formatted performance report
        """
        if not self.metrics:
            return "No performance data available"
        
        # Format metrics
        report = [
            "Strategy Performance Report",
            "========================",
            f"Total Return: {self.metrics['total_return']:.2%}",
            f"Annual Return: {self.metrics['annual_return']:.2%}",
            f"Annual Volatility: {self.metrics['annual_volatility']:.2%}",
            f"Sharpe Ratio: {self.metrics['sharpe_ratio']:.2f}",
            f"Max Drawdown: {self.metrics['max_drawdown']:.2%}",
            f"Win Rate: {self.metrics['win_rate']:.2%}",
            f"Profit Factor: {self.metrics['profit_factor']:.2f}",
            f"Value at Risk (95%): {self.metrics['var_95']:.2%}",
            f"Conditional VaR (95%): {self.metrics['cvar_95']:.2%}",
            f"Total Trades: {self.metrics['total_trades']}",
            f"Average Win: ${self.metrics['avg_win']:.2f}",
            f"Average Loss: ${self.metrics['avg_loss']:.2f}"
        ]
        
        return "\n".join(report) 