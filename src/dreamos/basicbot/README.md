# BasicBot Trading Strategies

This module provides a collection of trading strategies for BasicBot instances, focusing on algorithmic design, risk management, and performance optimization.

## Overview

The BasicBot strategies module includes four main strategy implementations:

1. **Trend Following Strategy**
   - Uses multiple timeframes and moving averages
   - Implements ATR-based position sizing
   - Suitable for trending markets

2. **Mean Reversion Strategy**
   - Based on statistical mean reversion principles
   - Uses dynamic volatility bands
   - Includes holding period constraints

3. **Momentum Strategy**
   - Combines price momentum with volume analysis
   - Implements position limits
   - Suitable for volatile markets

4. **Risk-Aware Strategy**
   - Focuses on risk management and position sizing
   - Implements dynamic stop losses
   - Includes trailing stop functionality

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from dreamos.basicbot import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    RiskAwareStrategy
)

# Initialize a strategy
strategy = TrendFollowingStrategy(
    short_window=20,
    medium_window=50,
    long_window=200,
    atr_period=14,
    risk_per_trade=0.02
)

# Generate trading signals
signals = strategy.generate_signals(market_data)
```

## Configuration

The strategies can be configured using the `config.yaml` file:

```yaml
strategies:
  trend_following:
    enabled: true
    parameters:
      short_window: 20
      medium_window: 50
      long_window: 200
      atr_period: 14
      risk_per_trade: 0.02
```

## Risk Management

Each strategy includes built-in risk management features:

- Position sizing based on volatility
- Stop loss mechanisms
- Maximum position limits
- Drawdown controls

## Performance Monitoring

The module includes comprehensive performance monitoring:

- Sharpe and Sortino ratios
- Maximum drawdown tracking
- Win rate calculation
- Profit factor analysis

## Testing

Run the test suite:

```bash
python -m unittest src/dreamos/basicbot/test_strategies.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 