"""
trade_executor.py - Live Trading Execution Module

This module implements the live trading engine for the BasicBot system:
- Processes real-time market data
- Applies trading strategies to generate signals
- Validates trades through risk management
- Executes orders via brokerage API
- Logs trade activity and performance

Usage:
    from basicbot.trade_executor import TradeExecutor
    executor = TradeExecutor(api, strategy, risk_manager)
    executor.start()
"""

import time
import logging
import datetime
import os
from pathlib import Path
import json
import threading
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union

# Handle both package and standalone imports
try:
    from basicbot.config import config
    from basicbot.logger import setup_logging
    from basicbot.strategy import Strategy
    from basicbot.risk_manager import RiskManager
    from basicbot.trading_api_alpaca import TradingAPI
except ImportError:
    from config import config
    from logger import setup_logging
    from strategy import Strategy
    from risk_manager import RiskManager
    from trading_api_alpaca import TradingAPI


class TradeExecutor:
    """
    Live trading execution engine for the BasicBot system.
    """
    
    def __init__(
        self,
        api: TradingAPI = None,
        strategy: Strategy = None,
        risk_manager: RiskManager = None,
        symbols: List[str] = None,
        timeframe: str = None,
        poll_interval: int = 60,
        journal_file: str = None,
        logger: logging.Logger = None,
        dry_run: bool = False
    ):
        """
        Initialize the trade executor.
        
        Args:
            api: Trading API instance
            strategy: Trading strategy instance
            risk_manager: Risk manager instance
            symbols: List of trading symbols
            timeframe: Data timeframe
            poll_interval: Seconds between market data polls
            journal_file: Path to trade journal file
            logger: Logger instance
            dry_run: If True, don't execute actual trades
        """
        # Setup logger
        self.logger = logger or setup_logging("trade_executor")
        
        # Initialize API if not provided
        self.api = api or TradingAPI()
        
        # Initialize strategy
        self.strategy = strategy or Strategy(
            symbol=config.SYMBOL,
            timeframe=config.TIMEFRAME
        )
        
        # Initialize risk manager
        self.risk_manager = risk_manager or RiskManager()
        
        # Trading parameters
        self.symbols = symbols or [config.SYMBOL]
        self.timeframe = timeframe or config.TIMEFRAME
        self.poll_interval = poll_interval
        self.dry_run = dry_run
        
        # State tracking
        self.is_running = False
        self.last_signals = {}
        self.active_positions = {}
        self.trade_history = []
        
        # Setup journal
        self.journal_file = journal_file or "trade_journal.csv"
        self._setup_journal()
        
        self.logger.info(
            f"Trade Executor initialized: {len(self.symbols)} symbols, "
            f"{self.timeframe} timeframe, {'DRY RUN' if self.dry_run else 'LIVE MODE'}"
        )
    
    def _setup_journal(self):
        """
        Set up or initialize the trade journal file.
        """
        # Create journal file if it doesn't exist
        if not os.path.exists(self.journal_file):
            journal_df = pd.DataFrame(columns=[
                'timestamp', 'symbol', 'side', 'quantity', 'price',
                'order_id', 'status', 'profit_loss', 'notes'
            ])
            journal_df.to_csv(self.journal_file, index=False)
            self.logger.info(f"Created new trade journal at {self.journal_file}")
    
    def add_to_journal(self, trade_data: Dict[str, Any]):
        """
        Add a trade record to the journal file.
        
        Args:
            trade_data: Dictionary containing trade information
        """
        # Ensure timestamp is present
        if 'timestamp' not in trade_data:
            trade_data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Read existing journal
        try:
            journal_df = pd.read_csv(self.journal_file)
            
            # Append new trade
            journal_df = journal_df.append(trade_data, ignore_index=True)
            
            # Write back to file
            journal_df.to_csv(self.journal_file, index=False)
            
            self.logger.info(f"Trade recorded in journal: {trade_data['symbol']} {trade_data['side']} @ {trade_data['price']}")
        except Exception as e:
            self.logger.error(f"Error adding trade to journal: {e}")
    
    def start(self):
        """
        Start the trading loop.
        This runs in an infinite loop until stopped.
        """
        self.is_running = True
        self.logger.info("Trading executor started")
        
        try:
            # Update account info
            self._update_account_info()
            
            # Main trading loop
            while self.is_running:
                # Check if market is open
                # Execute strategy for each symbol
                for symbol in self.symbols:
                    try:
                        self._process_symbol(symbol)
                    except Exception as e:
                        self.logger.error(f"Error processing {symbol}: {e}")
                
                # Wait for next cycle
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Trading loop interrupted by user")
        except Exception as e:
            self.logger.error(f"Trading loop error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """
        Stop the trading loop.
        """
        self.is_running = False
        self.logger.info("Trading executor stopped")
    
    def _update_account_info(self):
        """
        Update account information and active positions.
        """
        # Get account info
        account = self.api.get_account()
        if account:
            equity = float(account.get('equity', 0))
            buying_power = float(account.get('buying_power', 0))
            
            # Update risk manager with latest account metrics
            self.risk_manager.update_account_metrics(equity, buying_power)
            
            self.logger.info(f"Account updated: equity=${equity:.2f}, buying_power=${buying_power:.2f}")
        
        # Update positions for each symbol
        for symbol in self.symbols:
            qty, cost_basis = self.api.get_position(symbol)
            self.active_positions[symbol] = {
                'quantity': qty,
                'cost_basis': cost_basis
            }
            if qty > 0:
                self.logger.info(f"Position: {symbol} - {qty} shares @ ${cost_basis:.2f}")
    
    def _process_symbol(self, symbol: str):
        """
        Process trading logic for a single symbol.
        
        Args:
            symbol: Trading symbol to process
        """
        # Get latest market data
        data = self._get_market_data(symbol)
        if data is None or data.empty:
            self.logger.warning(f"No market data available for {symbol}")
            return
        
        # Apply strategy
        data = self.strategy.calculate_indicators(data)
        signals = self.strategy.generate_signals(data)
        
        # Get latest signal
        current_signal = signals.iloc[-1] if not signals.empty else "HOLD"
        current_price = data['close'].iloc[-1] if not data.empty else 0
        
        # Store latest signal
        previous_signal = self.last_signals.get(symbol, "HOLD")
        self.last_signals[symbol] = current_signal
        
        # Check if signal changed and we need to act
        if current_signal != previous_signal:
            self.logger.info(f"Signal change for {symbol}: {previous_signal} -> {current_signal}")
            
            # Get account info for risk calculations
            account = self.api.get_account()
            equity = float(account.get('equity', 0)) if account else 0
            
            # Get current position
            position_qty = self.active_positions.get(symbol, {}).get('quantity', 0)
            current_positions = sum(1 for pos in self.active_positions.values() if pos.get('quantity', 0) > 0)
            
            # Handle BUY signal
            if current_signal == "BUY" and position_qty == 0:
                # Check if we can trade
                can_trade, reason = self.risk_manager.can_place_trade(equity, current_positions)
                
                if can_trade:
                    # Calculate position size
                    atr = data.get('ATR', pd.Series()).iloc[-1] if 'ATR' in data.columns else None
                    stop_loss = data.get('stop_loss', pd.Series()).iloc[-1] if 'stop_loss' in data.columns else None
                    
                    # Calculate position size
                    _, shares = self.risk_manager.calculate_position_size(
                        account_balance=equity,
                        price=current_price,
                        stop_loss=stop_loss,
                        atr=atr
                    )
                    
                    # Validate trade
                    is_valid, reason = self.risk_manager.validate_trade(
                        symbol=symbol,
                        side="buy",
                        quantity=shares,
                        price=current_price
                    )
                    
                    # Execute order if valid
                    if is_valid and shares > 0:
                        self._execute_order(symbol, "buy", shares, current_price)
                    else:
                        self.logger.warning(f"Trade validation failed: {reason}")
                else:
                    self.logger.info(f"Trade not allowed: {reason}")
            
            # Handle SELL signal
            elif current_signal == "SELL" and position_qty > 0:
                # Execute order
                self._execute_order(symbol, "sell", position_qty, current_price)
    
    def _get_market_data(self, symbol: str) -> pd.DataFrame:
        """
        Get the latest market data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            DataFrame with market data or None if failed
        """
        try:
            # Try to use custom method if available in the API
            if hasattr(self.api, 'get_latest_data'):
                return self.api.get_latest_data(symbol, self.timeframe)
            
            # If not available, use the strategy's method
            data = self.strategy.fetch_historical_data()
            if data is not None and not data.empty:
                return data
            
            self.logger.warning(f"Could not fetch market data for {symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    def _execute_order(self, symbol: str, side: str, quantity: int, price: float):
        """
        Execute a trading order.
        
        Args:
            symbol: Trading symbol
            side: Trade side ('buy' or 'sell')
            quantity: Number of shares to trade
            price: Current market price
        """
        # Log the order
        self.logger.info(f"ORDER: {side} {quantity} {symbol} @ ${price:.2f}")
        
        # Skip actual execution in dry run mode
        if self.dry_run:
            self.logger.info("DRY RUN MODE - Order not sent to broker")
            
            # Record trade in journal
            trade_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'order_id': 'dry-run',
                'status': 'simulated',
                'profit_loss': 0,
                'notes': 'Dry run mode - no actual execution'
            }
            
            # Add to journal
            self.add_to_journal(trade_data)
            
            # Update risk manager
            self.risk_manager.record_trade()
            
            return
        
        # Execute the order
        try:
            # Place order via API
            order_result = self.api.place_order(symbol=symbol, qty=quantity, side=side)
            
            if order_result:
                order_id = order_result.get('id', 'unknown')
                status = order_result.get('status', 'unknown')
                
                self.logger.info(f"Order executed: ID={order_id}, Status={status}")
                
                # Calculate profit/loss for sell orders
                profit_loss = 0
                if side.lower() == 'sell':
                    cost_basis = self.active_positions.get(symbol, {}).get('cost_basis', 0)
                    if cost_basis > 0:
                        profit_loss = (price - cost_basis) * quantity
                
                # Record trade in journal
                trade_data = {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'order_id': order_id,
                    'status': status,
                    'profit_loss': profit_loss,
                    'notes': ''
                }
                
                # Add to journal
                self.add_to_journal(trade_data)
                
                # Update risk manager
                self.risk_manager.record_trade()
                
                # Update position tracking (optimistic update)
                if side.lower() == 'buy':
                    self.active_positions[symbol] = {
                        'quantity': quantity,
                        'cost_basis': price
                    }
                elif side.lower() == 'sell':
                    self.active_positions[symbol] = {
                        'quantity': 0,
                        'cost_basis': 0
                    }
                
                # Update account info
                self._update_account_info()
            else:
                self.logger.error(f"Order failed: {symbol} {side} {quantity}")
        
        except Exception as e:
            self.logger.error(f"Error executing order: {e}", exc_info=True)
    
    def run_backtest_comparison(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Run a backtest for comparison with live trading results.
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            Dictionary with backtest results
        """
        from basicbot.backtester import Backtester
        
        # Setup backtester
        backtester = Backtester(
            strategy=self.strategy,
            logger=self.logger,
            symbol=self.symbols[0] if self.symbols else config.SYMBOL,
            timeframe=self.timeframe,
            initial_cash=10000  # Use a fixed amount for comparison
        )
        
        # Fetch historical data
        try:
            # Try to use yfinance if available
            import yfinance as yf
            symbol = self.symbols[0] if self.symbols else config.SYMBOL
            data = yf.download(symbol, start=start_date, end=end_date, interval=self.timeframe)
            
            if data.empty:
                self.logger.error(f"No data available for backtest comparison")
                return None
            
            # Run backtest
            results = backtester.run_backtest(data)
            
            # Return metrics
            return {
                "metrics": backtester.metrics,
                "trades": len(backtester.trades) if hasattr(backtester, "trades") else 0,
                "win_rate": backtester.metrics.get("win_rate", 0),
                "profit_factor": backtester.metrics.get("profit_factor", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error running backtest comparison: {e}")
            return None


# For testing
if __name__ == "__main__":
    # Create an instance with dry run mode
    executor = TradeExecutor(
        symbols=["TSLA"],
        timeframe="1d",
        poll_interval=60,
        journal_file="test_journal.csv",
        dry_run=True
    )
    
    # Start trading in a separate thread
    trading_thread = threading.Thread(target=executor.start)
    trading_thread.daemon = True
    trading_thread.start()
    
    print("Trading executor started in dry run mode. Press Enter to stop...")
    input()
    
    # Stop trading
    executor.stop()
    trading_thread.join(timeout=5)
    
    print("Trading executor stopped.")
    print(f"Active positions: {executor.active_positions}")
    print(f"Last signals: {executor.last_signals}") 