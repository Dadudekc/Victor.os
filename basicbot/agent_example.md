# Dream.OS Agent Integration Guide

This guide demonstrates how Dream.OS agents can interact with the BasicBot trading system.

## Overview

The `agent_api.py` module provides a structured interface that allows Dream.OS agents to:

1. Run backtests with various strategies and parameters
2. Generate trading signals for symbols and timeframes
3. Access performance metrics in a structured format
4. Retrieve visualizations for analysis

## Agent Query Format

Agents should use the following JSON structure when querying the BasicBot system:

```json
{
  "action": "backtest|generate_signals|get_strategy_info",
  "parameters": {
    // Action-specific parameters
  }
}
```

## Example Agent Interactions

### 1. Running a Backtest

**Agent Request:**
```python
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
```

**System Response:**
```python
{
    "success": True,
    "metrics": {
        "total_return": 0.1243,
        "annual_return": 0.2568,
        "max_drawdown": -0.0821,
        "volatility": 0.1853,
        "sharpe_ratio": 1.3856,
        "win_rate": 0.6250,
        "avg_win": 425.75,
        "avg_loss": -215.30,
        "profit_factor": 1.9775,
        "final_balance": 11243.00,
        "trade_count": 8
    },
    "trades": [
        {
            "entry_date": "2023-01-15T00:00:00",
            "entry_price": 123.45,
            "shares": 81.00,
            "direction": "LONG",
            "transaction_cost": 9.99,
            "exit_date": "2023-02-10T00:00:00",
            "exit_price": 135.67,
            "profit_loss": 987.89,
            "profit_loss_pct": 9.90
        },
        // Additional trades...
    ],
    "plot": "base64_encoded_image_data"  // Only if include_plot=True
}
```

### 2. Generating Trading Signals

**Agent Request:**
```python
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
```

**System Response:**
```python
{
    "success": True,
    "current_signal": "BUY",  # or "SELL" or "HOLD"
    "signals": {
        "BUY": 10,
        "SELL": 8,
        "HOLD": 42
    },
    "indicators": {
        "SMA_short": 245.67,
        "SMA_long": 230.45,
        "RSI": 63.21,
        "MACD": 2.45,
        "MACD_signal": 1.89,
        "MACD_hist": 0.56,
        "current_price": 252.78
    }
}
```

### 3. Getting Strategy Information

**Agent Request:**
```python
info_request = {
    "action": "get_strategy_info",
    "parameters": {}
}

info_result = agent_query(info_request)
```

**System Response:**
```python
{
    "available_strategies": {
        "default": {
            "description": "Standard technical analysis strategy with MA crossover and RSI",
            "parameters": {
                "maShortLength": "Short moving average period (default: 50)",
                "maLongLength": "Long moving average period (default: 200)",
                "rsiLength": "RSI calculation period (default: 14)",
                "rsiOverbought": "RSI overbought threshold (default: 70)",
                "rsiOversold": "RSI oversold threshold (default: 30)"
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
                "macdSignal": "MACD signal line period (default: 9)"
            }
        }
    },
    "supported_timeframes": [
        "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"
    ]
}
```

## Example Agent Prompt Templates

Here are some template prompts that can be used when interacting with BasicBot:

### Backtesting Template

```
Run a backtest on TSLA using the MACD-RSI strategy from [START_DATE] to [END_DATE]. 
Use a [FAST] period fast EMA, [SLOW] period slow EMA, and RSI period of [RSI_PERIOD]. 
Set overbought threshold at [OVERBOUGHT] and oversold at [OVERSOLD].
Start with [INITIAL_CASH] initial cash.
```

### Signal Generation Template

```
Generate trading signals for [SYMBOL] using the default strategy.
Analyze the last [DAYS] days of data with [TIMEFRAME] timeframe.
Tell me the current signal and key indicator values.
```

## Advanced Agent Workflows

Agents can build more advanced workflows by chaining these operations:

1. **Strategy Development**:
   - Get strategy information
   - Run multiple backtests with different parameters
   - Compare performance metrics to optimize

2. **Real-time Trading**:
   - Generate signals for current market conditions
   - Make trading recommendations based on signals and indicators
   - Set alerts for specific market conditions

3. **Portfolio Analysis**:
   - Run backtests on multiple symbols
   - Analyze correlations and diversification benefits
   - Recommend portfolio allocations based on performance metrics 