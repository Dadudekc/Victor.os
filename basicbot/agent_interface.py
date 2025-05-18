"""
agent_interface.py - Dream.OS Agent Interface for BasicBot

This module provides the interface between Dream.OS agents and the BasicBot trading system.
It allows agents to:
- Trigger trading sessions
- Check trading status
- Get trade results and performance metrics
- Execute one-off trades based on agent analysis

Usage:
    from basicbot.agent_interface import AgentTrader
    agent_trader = AgentTrader()
    response = agent_trader.execute_command({"action": "start_trading", "symbols": ["TSLA"]})
"""

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Import BasicBot components
try:
    from basicbot.trade_executor import TradeExecutor
    from basicbot.risk_manager import RiskManager
    from basicbot.trading_api_alpaca import TradingAPI
    from basicbot.strategy import Strategy
    from basicbot.logger import setup_logging
    from basicbot.config import config
except ImportError:
    # For standalone testing
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from basicbot.trade_executor import TradeExecutor
    from basicbot.risk_manager import RiskManager
    from basicbot.trading_api_alpaca import TradingAPI
    from basicbot.strategy import Strategy
    from basicbot.logger import setup_logging
    from basicbot.config import config


class AgentTrader:
    """Interface between Dream.OS agents and BasicBot trading system."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the agent trader interface.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or setup_logging("agent_trader")
        self.executor = None
        self.trading_thread = None
        self.is_running = False
        self.last_command = {}
        self.command_history = []
        self.trade_history = []
        
        # Track system state
        self.status = {
            "state": "idle",
            "symbols": [],
            "started_at": None,
            "last_trade": None,
            "position_count": 0,
            "performance": {
                "win_rate": 0,
                "profit_loss": 0,
                "trade_count": 0
            }
        }
        
        self.logger.info("Agent Trader interface initialized")
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command from an agent.
        
        Args:
            command: Command dictionary with action and parameters
            
        Returns:
            Response dictionary with results and status
        """
        if not isinstance(command, dict) or "action" not in command:
            return {"status": "error", "message": "Invalid command format"}
        
        action = command.get("action", "").lower()
        self.last_command = command
        self.command_history.append({
            "timestamp": datetime.now().isoformat(),
            "command": command
        })
        
        try:
            # Route to appropriate handler based on action
            if action == "start_trading":
                return self._start_trading(command)
            elif action == "stop_trading":
                return self._stop_trading()
            elif action == "get_status":
                return self._get_status()
            elif action == "execute_trade":
                return self._execute_single_trade(command)
            elif action == "get_trade_history":
                return self._get_trade_history()
            elif action == "get_performance":
                return self._get_performance_metrics()
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
                
        except Exception as e:
            self.logger.error(f"Error executing command {action}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def _start_trading(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Start a trading session.
        
        Args:
            command: Command with trading parameters
            
        Returns:
            Status response
        """
        # Check if already running
        if self.is_running:
            return {"status": "warning", "message": "Trading already running"}
        
        # Extract parameters with defaults
        symbols = command.get("symbols", [config.SYMBOL])
        timeframe = command.get("timeframe", config.TIMEFRAME)
        risk = command.get("risk", 1.0)
        max_positions = command.get("max_positions", 5)
        poll_interval = command.get("poll_interval", 60)
        paper = command.get("paper", True)  # Default to paper trading for safety
        
        try:
            # Initialize trading API
            api = TradingAPI(paper=paper)
            
            # Initialize risk manager
            risk_manager = RiskManager(
                max_risk_pct=risk,
                max_positions=max_positions,
                logger=self.logger
            )
            
            # Initialize strategy
            strategy = Strategy(
                symbol=symbols[0] if symbols else config.SYMBOL,
                timeframe=timeframe
            )
            
            # Initialize trade executor
            self.executor = TradeExecutor(
                api=api,
                strategy=strategy,
                risk_manager=risk_manager,
                symbols=symbols,
                timeframe=timeframe,
                poll_interval=poll_interval,
                journal_file=f"agent_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                logger=self.logger,
                dry_run=paper
            )
            
            # Start trading in a separate thread
            self.trading_thread = threading.Thread(target=self.executor.start)
            self.trading_thread.daemon = True
            self.trading_thread.start()
            
            # Update status
            self.is_running = True
            self.status = {
                "state": "running",
                "symbols": symbols,
                "started_at": datetime.now().isoformat(),
                "mode": "paper" if paper else "live",
                "timeframe": timeframe,
                "risk": risk,
                "position_count": 0
            }
            
            self.logger.info(f"Trading started via agent: {symbols}, {'PAPER' if paper else 'LIVE'} mode")
            
            return {
                "status": "success", 
                "message": f"Trading started for {symbols}",
                "details": self.status
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start trading: {e}", exc_info=True)
            return {"status": "error", "message": f"Failed to start trading: {e}"}
    
    def _stop_trading(self) -> Dict[str, Any]:
        """Stop the current trading session.
        
        Returns:
            Status response
        """
        if not self.is_running or not self.executor:
            return {"status": "warning", "message": "No trading session running"}
        
        try:
            # Stop the executor
            self.executor.stop()
            
            # Wait for thread to terminate
            if self.trading_thread:
                self.trading_thread.join(timeout=5)
            
            # Update status
            self.is_running = False
            self.status["state"] = "stopped"
            self.status["stopped_at"] = datetime.now().isoformat()
            
            self.logger.info("Trading stopped via agent")
            
            return {
                "status": "success", 
                "message": "Trading stopped successfully",
                "details": self.status
            }
            
        except Exception as e:
            self.logger.error(f"Failed to stop trading: {e}", exc_info=True)
            return {"status": "error", "message": f"Failed to stop trading: {e}"}
    
    def _get_status(self) -> Dict[str, Any]:
        """Get current system status.
        
        Returns:
            Status dictionary
        """
        # If executor is running, update position information
        if self.is_running and self.executor:
            try:
                # Update position count
                self.status["position_count"] = len([
                    p for p in self.executor.active_positions.values() 
                    if p.get("quantity", 0) > 0
                ])
                
                # Get latest signals
                self.status["latest_signals"] = self.executor.last_signals
                
            except Exception as e:
                self.logger.error(f"Error updating status: {e}")
        
        return {
            "status": "success",
            "trading_active": self.is_running,
            "details": self.status
        }
    
    def _execute_single_trade(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single trade based on agent analysis.
        
        Args:
            command: Trade details (symbol, side, quantity)
            
        Returns:
            Trade result
        """
        # Extract parameters
        symbol = command.get("symbol")
        side = command.get("side")
        quantity = command.get("quantity")
        paper = command.get("paper", True)  # Default to paper trading for safety
        
        # Validate parameters
        if not symbol or not side or not quantity:
            return {"status": "error", "message": "Missing required parameters (symbol, side, quantity)"}
        
        if side.lower() not in ["buy", "sell"]:
            return {"status": "error", "message": "Side must be 'buy' or 'sell'"}
        
        try:
            # Initialize API if not already running
            if not self.is_running or not self.executor:
                api = TradingAPI(paper=paper)
            else:
                api = self.executor.api
            
            # Execute the trade
            order_result = api.place_order(symbol=symbol, qty=quantity, side=side)
            
            # Record the trade
            trade_record = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_id": order_result.get("id", "unknown") if order_result else "failed",
                "status": order_result.get("status", "unknown") if order_result else "failed",
                "initiated_by": "agent"
            }
            
            self.trade_history.append(trade_record)
            self.status["last_trade"] = trade_record
            
            self.logger.info(f"Agent-initiated trade: {side} {quantity} {symbol}")
            
            return {
                "status": "success" if order_result else "error",
                "message": f"Trade executed: {side} {quantity} {symbol}" if order_result else "Trade failed",
                "details": order_result or {}
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute trade: {e}", exc_info=True)
            return {"status": "error", "message": f"Failed to execute trade: {e}"}
    
    def _get_trade_history(self) -> Dict[str, Any]:
        """Get trade history.
        
        Returns:
            Trade history
        """
        # If executor is running, pull its trade history
        if self.is_running and self.executor:
            try:
                # Read from journal file
                if os.path.exists(self.executor.journal_file):
                    import pandas as pd
                    trade_df = pd.read_csv(self.executor.journal_file)
                    trades = trade_df.to_dict(orient="records")
                    
                    # Update local history
                    self.trade_history = trades
            except Exception as e:
                self.logger.error(f"Error reading trade history: {e}")
        
        return {
            "status": "success",
            "count": len(self.trade_history),
            "trades": self.trade_history
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get trading performance metrics.
        
        Returns:
            Performance metrics
        """
        # Initialize metrics
        metrics = {
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0,
            "profit_loss": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "largest_win": 0,
            "largest_loss": 0
        }
        
        # If executor is running, calculate metrics from journal
        if self.is_running and self.executor:
            try:
                # Read from journal file
                if os.path.exists(self.executor.journal_file):
                    import pandas as pd
                    trade_df = pd.read_csv(self.executor.journal_file)
                    
                    if not trade_df.empty:
                        # Calculate basic metrics
                        metrics["trade_count"] = len(trade_df)
                        metrics["profit_loss"] = trade_df["profit_loss"].sum()
                        
                        # Win/loss metrics
                        win_trades = trade_df[trade_df["profit_loss"] > 0]
                        loss_trades = trade_df[trade_df["profit_loss"] < 0]
                        
                        metrics["win_count"] = len(win_trades)
                        metrics["loss_count"] = len(loss_trades)
                        
                        # Win rate
                        if metrics["trade_count"] > 0:
                            metrics["win_rate"] = metrics["win_count"] / metrics["trade_count"]
                        
                        # Average win/loss
                        if not win_trades.empty:
                            metrics["avg_win"] = win_trades["profit_loss"].mean()
                            metrics["largest_win"] = win_trades["profit_loss"].max()
                        
                        if not loss_trades.empty:
                            metrics["avg_loss"] = loss_trades["profit_loss"].mean()
                            metrics["largest_loss"] = loss_trades["profit_loss"].min()
                        
                        # Update status with latest metrics
                        self.status["performance"] = metrics
            except Exception as e:
                self.logger.error(f"Error calculating performance metrics: {e}")
        
        return {
            "status": "success",
            "metrics": metrics
        }


def run_cli_interface():
    """Run a simple CLI for testing the agent interface."""
    agent_trader = AgentTrader()
    
    print("BasicBot Agent Interface CLI")
    print("Type 'help' for available commands")
    
    while True:
        cmd = input("\nCommand: ").strip().lower()
        
        if cmd == "exit" or cmd == "quit":
            break
        elif cmd == "help":
            print("\nAvailable commands:")
            print("  start - Start trading")
            print("  stop - Stop trading")
            print("  status - Get system status")
            print("  trade - Execute a single trade")
            print("  history - Get trade history")
            print("  performance - Get performance metrics")
            print("  exit - Exit the CLI")
        elif cmd == "start":
            symbols = input("Symbols (comma-separated): ").strip().split(",")
            risk = float(input("Risk percentage: ") or "1.0")
            timeframe = input("Timeframe (default: 15m): ") or "15m"
            
            command = {
                "action": "start_trading",
                "symbols": symbols,
                "risk": risk,
                "timeframe": timeframe,
                "paper": True
            }
            
            result = agent_trader.execute_command(command)
            print(json.dumps(result, indent=2))
        elif cmd == "stop":
            result = agent_trader.execute_command({"action": "stop_trading"})
            print(json.dumps(result, indent=2))
        elif cmd == "status":
            result = agent_trader.execute_command({"action": "get_status"})
            print(json.dumps(result, indent=2))
        elif cmd == "trade":
            symbol = input("Symbol: ").strip()
            side = input("Side (buy/sell): ").strip()
            quantity = int(input("Quantity: ") or "1")
            
            command = {
                "action": "execute_trade",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "paper": True
            }
            
            result = agent_trader.execute_command(command)
            print(json.dumps(result, indent=2))
        elif cmd == "history":
            result = agent_trader.execute_command({"action": "get_trade_history"})
            print(json.dumps(result, indent=2))
        elif cmd == "performance":
            result = agent_trader.execute_command({"action": "get_performance_metrics"})
            print(json.dumps(result, indent=2))
        else:
            print(f"Unknown command: {cmd}")


# For standalone testing
if __name__ == "__main__":
    run_cli_interface() 