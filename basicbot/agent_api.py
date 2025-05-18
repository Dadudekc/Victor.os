"""
agent_api.py - Dream.OS Agent Integration Layer

This module exposes BasicBot functionality to Dream.OS agents through a clean API.
It provides standardized inputs and outputs that agents can understand and process.

Key features:
- Run backtests with various strategies and parameters
- Generate trading signals for specified symbols and timeframes
- Access performance metrics in structured format
- Retrieve visualizations for agent consumption
"""

import json
import base64
from io import BytesIO
from pathlib import Path
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple

try:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
except ImportError:
    plt = None
    Figure = None

# Import BasicBot components
from basicbot.strategy import Strategy
from basicbot.backtester import Backtester
from basicbot.logger import setup_logging
from basicbot.config import config

# Setup logger
logger = setup_logging("agent_api")


def run_backtest(
    symbol: str = "TSLA",
    timeframe: str = "1D",
    start_date: str = "2022-01-01",
    end_date: str = None,
    strategy_type: str = "default",
    strategy_params: Dict[str, Any] = None,
    initial_cash: float = 10000,
    include_plot: bool = True,
) -> Dict[str, Any]:
    """
    Run a backtest with specified parameters and return results in agent-friendly format.
    
    Args:
        symbol: Trading symbol (e.g., "TSLA")
        timeframe: Data timeframe (e.g., "1D", "1H", "5Min")
        start_date: Start date for backtest in YYYY-MM-DD format
        end_date: End date for backtest in YYYY-MM-DD format (defaults to current date)
        strategy_type: Type of strategy to use ("default", "macd_rsi", etc.)
        strategy_params: Dictionary of strategy-specific parameters
        initial_cash: Starting capital for backtest
        include_plot: Whether to include visualization in response
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if backtest was successful
        - metrics: Dictionary of performance metrics
        - trades: List of executed trades
        - plot: Base64-encoded PNG image of results (if include_plot=True)
        - error: Error message (if any)
    """
    logger.info(f"Agent requested backtest: {symbol} ({timeframe}) from {start_date} to {end_date}")
    
    try:
        # Initialize default response
        response = {
            "success": False,
            "metrics": {},
            "trades": [],
            "plot": None,
            "error": None
        }
        
        # Set up strategy parameters
        params = strategy_params or {}
        
        # Create strategy based on strategy_type
        if strategy_type == "macd_rsi":
            strategy = Strategy(
                symbol=symbol,
                timeframe=timeframe,
                maShortLength=params.get("ma_short", 12),
                maLongLength=params.get("ma_long", 26),
                rsiLength=params.get("rsi_length", 14),
                rsiOverbought=params.get("rsi_overbought", 70),
                rsiOversold=params.get("rsi_oversold", 30),
                macdFast=params.get("macd_fast", 12),
                macdSlow=params.get("macd_slow", 26),
                macdSignal=params.get("macd_signal", 9),
            )
        else:  # default strategy
            strategy = Strategy(
                symbol=symbol,
                timeframe=timeframe,
            )
        
        # Initialize backtester with temp logger to avoid excessive output
        backtest_logger = setup_logging(
            f"backtest_{symbol}_{timeframe}",
            log_level="INFO",
            console=False,
        )
        
        backtester = Backtester(
            strategy=strategy,
            logger=backtest_logger,
            symbol=symbol,
            timeframe=timeframe,
            initial_cash=initial_cash,
            log_file=f"backtest_{symbol}_{timeframe}.csv"
        )
        
        # Fetch historical data
        import yfinance as yf
        
        # Parse dates and fetch data
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date) if end_date else pd.Timestamp.now()
        
        # Download data from Yahoo Finance
        data = yf.download(symbol, start=start, end=end, interval=timeframe)
        
        if data.empty:
            return {
                "success": False,
                "error": f"No data available for {symbol} from {start_date} to {end_date}"
            }
        
        # Run backtest
        results = backtester.run_backtest(data)
        
        # Extract metrics
        response["metrics"] = {k: float(v) for k, v in backtester.metrics.items()}
        
        # Extract trades
        if hasattr(backtester, "trades"):
            response["trades"] = []
            for trade in backtester.trades:
                clean_trade = {}
                for k, v in trade.items():
                    if isinstance(v, pd.Timestamp):
                        clean_trade[k] = v.isoformat()
                    else:
                        clean_trade[k] = v
                response["trades"].append(clean_trade)
        
        # Generate plot if requested
        if include_plot and plt is not None:
            fig = backtester.plot_results(results)
            if fig:
                buf = BytesIO()
                fig.savefig(buf, format='png')
                buf.seek(0)
                response["plot"] = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)
        
        response["success"] = True
        
    except Exception as e:
        logger.error(f"Error running backtest: {str(e)}", exc_info=True)
        response = {
            "success": False,
            "error": str(e)
        }
    
    return response


def generate_trading_signals(
    symbol: str = "TSLA",
    timeframe: str = "1D",
    days: int = 30,
    strategy_type: str = "default",
    strategy_params: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Generate trading signals for the specified symbol.
    
    Args:
        symbol: Trading symbol (e.g., "TSLA")
        timeframe: Data timeframe (e.g., "1D", "1H", "5Min")
        days: Number of days of historical data to analyze
        strategy_type: Type of strategy to use ("default", "macd_rsi", etc.)
        strategy_params: Dictionary of strategy-specific parameters
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if signal generation was successful
        - current_signal: The most recent signal ("BUY", "SELL", or "HOLD")
        - signals: Dictionary with counts of each signal type
        - indicators: Dictionary with current indicator values
        - error: Error message (if any)
    """
    logger.info(f"Agent requested trading signals: {symbol} ({timeframe}, {days} days)")
    
    try:
        # Initialize default response
        response = {
            "success": False,
            "current_signal": None,
            "signals": {},
            "indicators": {},
            "error": None
        }
        
        # Set up strategy parameters
        params = strategy_params or {}
        
        # Create strategy based on strategy_type
        if strategy_type == "macd_rsi":
            strategy = Strategy(
                symbol=symbol,
                timeframe=timeframe,
                maShortLength=params.get("ma_short", 12),
                maLongLength=params.get("ma_long", 26),
                rsiLength=params.get("rsi_length", 14),
                rsiOverbought=params.get("rsi_overbought", 70),
                rsiOversold=params.get("rsi_oversold", 30),
                macdFast=params.get("macd_fast", 12),
                macdSlow=params.get("macd_slow", 26),
                macdSignal=params.get("macd_signal", 9),
            )
        else:  # default strategy
            strategy = Strategy(
                symbol=symbol,
                timeframe=timeframe,
            )
        
        # Fetch historical data
        import yfinance as yf
        
        end = pd.Timestamp.now()
        start = end - pd.Timedelta(days=days, unit='D')
        
        # Download data from Yahoo Finance
        data = yf.download(symbol, start=start, end=end, interval=timeframe)
        
        if data.empty:
            return {
                "success": False,
                "error": f"No data available for {symbol} for the last {days} days"
            }
        
        # Calculate indicators
        data = strategy.calculate_indicators(data)
        
        # Generate signals
        signals = strategy.generate_signals(data)
        
        # Extract current signal
        current_signal = signals.iloc[-1] if not signals.empty else "HOLD"
        
        # Count signal types
        signal_counts = signals.value_counts().to_dict()
        
        # Extract current indicator values
        indicators = {}
        for col in ['SMA_short', 'SMA_long', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist']:
            if col in data.columns:
                indicators[col] = float(data[col].iloc[-1])
        
        # Add price info
        indicators["current_price"] = float(data["close"].iloc[-1])
        
        # Prepare response
        response["success"] = True
        response["current_signal"] = current_signal
        response["signals"] = signal_counts
        response["indicators"] = indicators
        
    except Exception as e:
        logger.error(f"Error generating signals: {str(e)}", exc_info=True)
        response = {
            "success": False,
            "error": str(e)
        }
    
    return response


def get_strategy_info() -> Dict[str, Any]:
    """
    Get information about available strategies and parameters.
    
    Returns:
        Dictionary containing available strategies and their parameters
    """
    return {
        "available_strategies": {
            "default": {
                "description": "Standard technical analysis strategy with MA crossover and RSI",
                "parameters": {
                    "maShortLength": "Short moving average period (default: 50)",
                    "maLongLength": "Long moving average period (default: 200)",
                    "rsiLength": "RSI calculation period (default: 14)",
                    "rsiOverbought": "RSI overbought threshold (default: 70)",
                    "rsiOversold": "RSI oversold threshold (default: 30)",
                }
            },
            "macd_rsi": {
                "description": "MACD and RSI combined strategy",
                "parameters": {
                    "maShortLength": "Short moving average period (default: 50)",
                    "maLongLength": "Long moving average period (default: 200)",
                    "rsiLength": "RSI calculation period (default: 14)",
                    "rsiOverbought": "RSI overbought threshold (default: 70)",
                    "rsiOversold": "RSI oversold threshold (default: 30)",
                    "macdFast": "MACD fast line period (default: 12)",
                    "macdSlow": "MACD slow line period (default: 26)",
                    "macdSignal": "MACD signal line period (default: 9)",
                }
            }
        },
        "supported_timeframes": [
            "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"
        ]
    }


# Example function for Dream.OS agent integration
def agent_query(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a query from a Dream.OS agent.
    
    Args:
        request: Dictionary containing the agent's query with:
            - action: String indicating the requested action
            - parameters: Dictionary of parameters for the action
            
    Returns:
        Dictionary with the response for the agent
    """
    logger.info(f"Received agent query: {request.get('action')}")
    
    action = request.get("action", "").lower()
    params = request.get("parameters", {})
    
    if action == "backtest":
        return run_backtest(**params)
    
    elif action == "generate_signals":
        return generate_trading_signals(**params)
    
    elif action == "get_strategy_info":
        return get_strategy_info()
    
    else:
        return {
            "success": False,
            "error": f"Unknown action: {action}. Supported actions: backtest, generate_signals, get_strategy_info"
        }


# For testing
if __name__ == "__main__":
    # Test backtest
    backtest_request = {
        "action": "backtest",
        "parameters": {
            "symbol": "TSLA",
            "timeframe": "1d",
            "start_date": "2023-01-01",
            "end_date": "2023-06-30",
            "strategy_type": "macd_rsi",
            "strategy_params": {
                "ma_short": 20,
                "ma_long": 50,
                "rsi_length": 14
            },
            "initial_cash": 10000,
            "include_plot": True
        }
    }
    
    result = agent_query(backtest_request)
    
    if result["success"]:
        print("Backtest successful")
        print(f"Metrics: {json.dumps(result['metrics'], indent=2)}")
        print(f"Trades: {len(result['trades'])}")
        
        # Save plot if available
        if result.get("plot"):
            plot_data = base64.b64decode(result["plot"])
            with open("agent_backtest_plot.png", "wb") as f:
                f.write(plot_data)
            print("Plot saved to agent_backtest_plot.png")
    else:
        print(f"Backtest failed: {result.get('error')}")

    # Test signal generation
    signals_request = {
        "action": "generate_signals",
        "parameters": {
            "symbol": "TSLA",
            "timeframe": "1d",
            "days": 60,
            "strategy_type": "default"
        }
    }
    
    signals_result = agent_query(signals_request)
    
    if signals_result["success"]:
        print("\nSignal generation successful")
        print(f"Current signal: {signals_result['current_signal']}")
        print(f"Indicators: {json.dumps(signals_result['indicators'], indent=2)}")
    else:
        print(f"Signal generation failed: {signals_result.get('error')}") 