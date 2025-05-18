# BasicBot Trading System

A lightweight, customizable algorithmic trading system for live and paper trading.

## Features

- **Live Trading**: Connect to Alpaca API for real-time market data and order execution
- **Risk Management**: Configurable position sizing, maximum positions, and drawdown protection
- **Strategy Framework**: Implement custom trading strategies with technical indicators
- **Paper Trading**: Test strategies without risking real capital
- **Trade Journal**: Automatically log all trades with performance metrics
- **Database Logging**: Optional SQLite logging for trade history and analysis
- **Discord Alerts**: Real-time trade notifications and performance reports
- **Dream.OS Agent Integration**: Allow AI agents to control and monitor trading

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/basicbot.git
cd basicbot

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Create a `.env` file in the project root with your API credentials:

```
ALPACA_API_KEY=your_api_key
ALPACA_API_SECRET=your_api_secret
ALPACA_PAPER=true
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

2. Customize your trading parameters in `config.py` or override them with command-line arguments.

### Running BasicBot

```bash
# Start paper trading with default settings
python basicbot/main_trader.py --paper

# Live trading with custom parameters
python basicbot/main_trader.py --symbols AAPL MSFT --timeframe 15m --risk 0.5 --max_positions 3

# Enable Discord notifications
python basicbot/main_trader.py --paper --discord --daily_report

# Start in agent interface mode
python basicbot/main_trader.py --agent_mode
```

## System Components

### Trade Executor (`trade_executor.py`)

The core trading engine that:
- Polls market data at regular intervals
- Applies your strategy to generate signals
- Validates trades through risk management
- Executes orders via the brokerage API
- Logs trade activity and performance

### Risk Manager (`risk_manager.py`)

Handles all trading risk parameters:
- Position sizing based on account balance and risk percentage
- Maximum position limits and concurrent positions
- Drawdown protection to halt trading if losses exceed thresholds
- Trade validation to prevent invalid orders

### Trading API (`trading_api_alpaca.py`)

Connects to Alpaca Markets for:
- Real-time and historical market data
- Order execution and position management
- Account information and buying power

### Strategy Framework (`strategy.py`)

Base class for implementing trading strategies:
- Technical indicator calculation
- Signal generation rules
- Custom entry/exit logic

### Discord Alerts (`discord_alerts.py`)

Sends real-time notifications to Discord:
- Trade execution alerts with entry/exit details
- Daily performance reports
- System status updates
- Error notifications

### Agent Interface (`agent_interface.py`)

Provides an API for Dream.OS agents to:
- Start/stop trading sessions
- Execute individual trades
- Monitor system status and performance
- Get trade history and metrics

## Command Line Options

```
usage: main_trader.py [-h] [--symbols SYMBOLS [SYMBOLS ...]] [--timeframe TIMEFRAME]
                      [--risk RISK] [--max_positions MAX_POSITIONS]
                      [--poll_interval POLL_INTERVAL] [--journal JOURNAL] [--paper]
                      [--log_level {DEBUG,INFO,WARNING,ERROR}] [--db_log]
                      [--discord] [--discord_webhook DISCORD_WEBHOOK]
                      [--agent_mode] [--daemon] [--daily_report]

BasicBot Trading System

options:
  -h, --help            show this help message and exit
  --symbols SYMBOLS [SYMBOLS ...]
                        Trading symbols (default: from config)
  --timeframe TIMEFRAME
                        Data timeframe (default: from config)
  --risk RISK           Risk percentage per trade (default: 1.0)
  --max_positions MAX_POSITIONS
                        Maximum concurrent positions (default: 5)
  --poll_interval POLL_INTERVAL
                        Market data poll interval in seconds (default: 60)
  --journal JOURNAL     Trade journal file path (default: trade_journal.csv)
  --paper               Run in paper trading mode (no real orders)
  --log_level {DEBUG,INFO,WARNING,ERROR}
                        Logging level (default: INFO)
  --db_log              Enable SQLite database logging
  --discord             Enable Discord notifications
  --discord_webhook DISCORD_WEBHOOK
                        Discord webhook URL (overrides env var)
  --agent_mode          Run in agent interface mode
  --daemon              Run as a background daemon process
  --daily_report        Send daily performance reports
```

## Creating Custom Strategies

Extend the base Strategy class to implement your own trading logic:

```python
from basicbot.strategy import Strategy

class MyStrategy(Strategy):
    def __init__(self, symbol, timeframe):
        super().__init__(symbol, timeframe)
        self.short_period = 10
        self.long_period = 20

    def calculate_indicators(self, data):
        """Calculate technical indicators for the strategy."""
        # Add your indicators (SMA, EMA, RSI, etc.)
        data['SMA_short'] = data['close'].rolling(window=self.short_period).mean()
        data['SMA_long'] = data['close'].rolling(window=self.long_period).mean()
        return data

    def generate_signals(self, data):
        """Generate trading signals from indicator values."""
        signals = pd.Series(index=data.index, data="HOLD")
        
        # Simple moving average crossover strategy
        buy_signal = (data['SMA_short'] > data['SMA_long']) & \
                      (data['SMA_short'].shift(1) <= data['SMA_long'].shift(1))
        sell_signal = (data['SMA_short'] < data['SMA_long']) & \
                       (data['SMA_short'].shift(1) >= data['SMA_long'].shift(1))
                       
        signals[buy_signal] = "BUY"
        signals[sell_signal] = "SELL"
        
        return signals
```

## Dream.OS Agent Integration

Agents can control the trading system using a simple command-based API:

```python
from basicbot.agent_interface import AgentTrader

# Initialize agent interface
agent_trader = AgentTrader()

# Start trading
response = agent_trader.execute_command({
    "action": "start_trading",
    "symbols": ["TSLA", "AAPL"],
    "timeframe": "15m",
    "risk": 1.0,
    "paper": True
})

# Check status
status = agent_trader.execute_command({"action": "get_status"})

# Execute single trade based on agent analysis
trade = agent_trader.execute_command({
    "action": "execute_trade",
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 10,
    "paper": True
})

# Get performance metrics
metrics = agent_trader.execute_command({"action": "get_performance_metrics"})

# Stop trading
agent_trader.execute_command({"action": "stop_trading"})
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 