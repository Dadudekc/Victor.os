"""
main_trader.py - BasicBot Trading System Main Entry Point

This script initializes and runs the BasicBot trading system with configurable options:
- Connects to your brokerage API
- Applies your selected strategy
- Manages risk parameters
- Executes live or paper trading
- Integrates with Discord for alerts
- Provides Dream.OS agent interface

Usage:
    python main_trader.py --symbols AAPL TSLA --timeframe 1d --risk 1.0 --paper
"""

import argparse
import logging
import threading
import time
import signal
import sys
import os
from pathlib import Path
from datetime import datetime

# Import BasicBot components
from basicbot.trade_executor import TradeExecutor
from basicbot.risk_manager import RiskManager
from basicbot.trading_api_alpaca import TradingAPI
from basicbot.strategy import Strategy
from basicbot.logger import setup_logging
from basicbot.config import config
from basicbot.discord_alerts import DiscordAlerts
from basicbot.agent_interface import AgentTrader


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="BasicBot Trading System")
    
    parser.add_argument("--symbols", nargs="+", default=[config.SYMBOL],
                        help="Trading symbols (default: from config)")
    
    parser.add_argument("--timeframe", type=str, default=config.TIMEFRAME,
                        help=f"Data timeframe (default: {config.TIMEFRAME})")
    
    parser.add_argument("--risk", type=float, default=1.0,
                        help="Risk percentage per trade (default: 1.0)")
    
    parser.add_argument("--max_positions", type=int, default=5,
                        help="Maximum concurrent positions (default: 5)")
    
    parser.add_argument("--poll_interval", type=int, default=60,
                        help="Market data poll interval in seconds (default: 60)")
    
    parser.add_argument("--journal", type=str, default="trade_journal.csv",
                        help="Trade journal file path (default: trade_journal.csv)")
    
    parser.add_argument("--paper", action="store_true",
                        help="Run in paper trading mode (no real orders)")
    
    parser.add_argument("--log_level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level (default: INFO)")
    
    parser.add_argument("--db_log", action="store_true",
                        help="Enable SQLite database logging")
    
    parser.add_argument("--discord", action="store_true",
                        help="Enable Discord notifications")
    
    parser.add_argument("--discord_webhook", type=str, default=None,
                        help="Discord webhook URL (overrides DISCORD_WEBHOOK_URL env var)")
    
    parser.add_argument("--agent_mode", action="store_true",
                        help="Run in agent interface mode")
    
    parser.add_argument("--daemon", action="store_true",
                        help="Run as a background daemon process")
    
    parser.add_argument("--daily_report", action="store_true",
                        help="Send daily performance reports")
    
    return parser.parse_args()


def setup_signal_handlers(executor, alerts=None):
    """Setup handlers for system signals to gracefully stop trading"""
    def signal_handler(sig, frame):
        print("\nReceived shutdown signal. Stopping trading...")
        executor.stop()
        
        # Send shutdown notification if alerts enabled
        if alerts:
            alerts.send_message("⚠️ **BasicBot Trading Stopped**", 
                               {"description": "Trading system shutdown signal received"})
        
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def setup_discord_alerts(args, logger):
    """Setup Discord alerts if enabled"""
    if not args.discord:
        return None
    
    webhook_url = args.discord_webhook or os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("Discord alerts enabled but no webhook URL provided")
        logger.warning("Set DISCORD_WEBHOOK_URL environment variable or use --discord_webhook")
        return None
    
    return DiscordAlerts(webhook_url=webhook_url, logger=logger)


def setup_trade_executor(args, logger, alerts=None):
    """Setup and configure the trade executor"""
    # Initialize trading API
    api = TradingAPI(paper=args.paper)
    
    # Initialize risk manager
    risk_manager = RiskManager(
        max_risk_pct=args.risk,
        max_positions=args.max_positions,
        logger=logger
    )
    
    # Initialize strategies (one per symbol)
    strategies = {}
    for symbol in args.symbols:
        strategies[symbol] = Strategy(
            symbol=symbol,
            timeframe=args.timeframe
        )
    
    # Use the first strategy for the executor (for multi-symbol support)
    strategy = next(iter(strategies.values())) if strategies else Strategy()
    
    # Setup database logging if requested
    if args.db_log:
        try:
            import sqlite3
            from datetime import datetime
            
            # Create or connect to SQLite database
            db_path = Path("basicbot_trades.db")
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Create trades table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                quantity INTEGER,
                price REAL,
                order_id TEXT,
                status TEXT,
                profit_loss REAL
            )
            ''')
            conn.commit()
            
            logger.info(f"Database logging enabled: {db_path}")
        except Exception as e:
            logger.error(f"Failed to setup database logging: {e}")
            args.db_log = False
    
    # Create a custom trade monitor class to handle trade events
    class TradeMonitor:
        def __init__(self, executor, alerts):
            self.executor = executor
            self.alerts = alerts
            self.last_position_count = 0
            self.last_status_time = 0
            self.last_report_day = None
        
        def check_for_trade_events(self):
            """Check for trade events to send alerts"""
            if not self.alerts:
                return
            
            # Check for new trades by monitoring the journal file
            if os.path.exists(self.executor.journal_file):
                try:
                    import pandas as pd
                    trades_df = pd.read_csv(self.executor.journal_file)
                    if not trades_df.empty:
                        # Get the latest trade
                        latest_trade = trades_df.iloc[-1]
                        
                        # Check if this is a new trade (last row)
                        if 'status' in latest_trade and latest_trade['status'] != 'alerted':
                            # Send trade alert
                            self.alerts.send_trade_alert(
                                side=latest_trade['side'],
                                symbol=latest_trade['symbol'],
                                quantity=latest_trade['quantity'],
                                price=latest_trade['price'],
                                profit_loss=latest_trade.get('profit_loss', 0)
                            )
                            
                            # Mark as alerted
                            trades_df.at[len(trades_df)-1, 'status'] = 'alerted'
                            trades_df.to_csv(self.executor.journal_file, index=False)
                except Exception as e:
                    logger.error(f"Error checking for trade events: {e}")
            
            # Check for status updates (every 15 minutes)
            current_time = time.time()
            if current_time - self.last_status_time > 15 * 60:  # 15 minutes
                try:
                    # Get position count
                    position_count = sum(1 for pos in self.executor.active_positions.values() 
                                        if pos.get('quantity', 0) > 0)
                    
                    # If position count changed, or it's been over an hour, send status
                    if position_count != self.last_position_count or current_time - self.last_status_time > 60 * 60:
                        # Get status info
                        status = {
                            "symbols": args.symbols,
                            "mode": "paper" if args.paper else "live",
                            "timeframe": args.timeframe,
                            "position_count": position_count,
                            "performance": {}  # Will be populated if available
                        }
                        
                        # Try to get performance metrics
                        try:
                            if os.path.exists(self.executor.journal_file):
                                import pandas as pd
                                trades_df = pd.read_csv(self.executor.journal_file)
                                
                                if not trades_df.empty:
                                    # Basic metrics
                                    win_trades = trades_df[trades_df['profit_loss'] > 0]
                                    loss_trades = trades_df[trades_df['profit_loss'] < 0]
                                    
                                    status["performance"] = {
                                        "trade_count": len(trades_df),
                                        "win_count": len(win_trades),
                                        "loss_count": len(loss_trades),
                                        "win_rate": len(win_trades) / len(trades_df) if len(trades_df) > 0 else 0,
                                        "profit_loss": trades_df['profit_loss'].sum()
                                    }
                        except Exception as e:
                            logger.error(f"Error calculating performance metrics: {e}")
                        
                        # Send status update
                        self.alerts.send_system_status(status, True)
                        
                        # Update last status time and position count
                        self.last_status_time = current_time
                        self.last_position_count = position_count
                except Exception as e:
                    logger.error(f"Error sending status update: {e}")
            
            # Check if we should send a daily report
            if args.daily_report:
                current_day = datetime.now().date()
                current_hour = datetime.now().hour
                
                # Send report at end of day (after market close) if we haven't already today
                if (current_hour >= 16 and self.last_report_day != current_day):
                    try:
                        # Calculate performance metrics
                        if os.path.exists(self.executor.journal_file):
                            import pandas as pd
                            trades_df = pd.read_csv(self.executor.journal_file)
                            
                            if not trades_df.empty:
                                # Filter for today's trades
                                today_df = trades_df[pd.to_datetime(trades_df['timestamp']).dt.date == current_day]
                                
                                if not today_df.empty:
                                    # Calculate metrics
                                    win_trades = today_df[today_df['profit_loss'] > 0]
                                    loss_trades = today_df[today_df['profit_loss'] < 0]
                                    
                                    metrics = {
                                        "trade_count": len(today_df),
                                        "win_count": len(win_trades),
                                        "loss_count": len(loss_trades),
                                        "win_rate": len(win_trades) / len(today_df) if len(today_df) > 0 else 0,
                                        "profit_loss": today_df['profit_loss'].sum(),
                                        "avg_win": win_trades['profit_loss'].mean() if not win_trades.empty else 0,
                                        "avg_loss": loss_trades['profit_loss'].mean() if not loss_trades.empty else 0,
                                        "largest_win": win_trades['profit_loss'].max() if not win_trades.empty else 0,
                                        "largest_loss": loss_trades['profit_loss'].min() if not loss_trades.empty else 0
                                    }
                                    
                                    # Send performance report
                                    self.alerts.send_performance_report(metrics)
                                    
                                    # Update last report day
                                    self.last_report_day = current_day
                    except Exception as e:
                        logger.error(f"Error sending daily report: {e}")
    
    # Initialize trade executor
    executor = TradeExecutor(
        api=api,
        strategy=strategy,
        risk_manager=risk_manager,
        symbols=args.symbols,
        timeframe=args.timeframe,
        poll_interval=args.poll_interval,
        journal_file=args.journal,
        logger=logger,
        dry_run=args.paper
    )
    
    # Initialize trade monitor if alerts enabled
    monitor = None
    if alerts:
        monitor = TradeMonitor(executor, alerts)
        
        # Send startup notification
        mode = "Paper" if args.paper else "Live"
        symbols_str = ", ".join(args.symbols)
        alerts.send_message(
            f"🚀 **BasicBot {mode} Trading Started**",
            {
                "description": f"Trading {symbols_str} on {args.timeframe} timeframe",
                "color": 0x3498db,  # Blue
                "fields": [
                    {"name": "Risk per Trade", "value": f"{args.risk}%", "inline": True},
                    {"name": "Max Positions", "value": str(args.max_positions), "inline": True},
                    {"name": "Poll Interval", "value": f"{args.poll_interval}s", "inline": True}
                ]
            }
        )
    
    return executor, monitor


def start_agent_interface(args, logger):
    """Start the agent interface"""
    logger.info("Starting agent interface")
    
    try:
        from basicbot.agent_interface import AgentTrader
        agent = AgentTrader(logger=logger)
        
        # This is where you'd integrate with Dream.OS
        # For now, we'll just run the CLI interface
        logger.info("Agent interface ready for commands")
        from basicbot.agent_interface import run_cli_interface
        run_cli_interface()
        
    except Exception as e:
        logger.error(f"Failed to start agent interface: {e}", exc_info=True)


def main():
    """Main entry point for the trading system"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    log_level = getattr(logging, args.log_level)
    logger = setup_logging("main_trader", level=log_level)
    logger.info(f"Starting BasicBot Trading System with symbols: {args.symbols}")
    
    # Check for agent mode
    if args.agent_mode:
        start_agent_interface(args, logger)
        return
    
    # Setup Discord alerts if enabled
    alerts = setup_discord_alerts(args, logger)
    
    # Setup trade executor
    executor, monitor = setup_trade_executor(args, logger, alerts)
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers(executor, alerts)
    
    # Start trading in a separate thread
    trading_thread = threading.Thread(target=executor.start)
    trading_thread.daemon = True
    trading_thread.start()
    
    logger.info(f"Trading started in {'PAPER' if args.paper else 'LIVE'} mode")
    logger.info("Press Ctrl+C to stop trading")
    
    # Enable daemon mode if requested
    if args.daemon:
        # Run as a daemon that automatically restarts on errors
        try:
            import daemon
            with daemon.DaemonContext():
                run_trading_loop(executor, trading_thread, monitor, logger)
        except ImportError:
            logger.warning("python-daemon package not installed, running in foreground")
            run_trading_loop(executor, trading_thread, monitor, logger)
    else:
        # Run in foreground
        run_trading_loop(executor, trading_thread, monitor, logger)


def run_trading_loop(executor, trading_thread, monitor, logger):
    """Run the main trading loop"""
    try:
        while trading_thread.is_alive():
            # Process any trade events for alerts
            if monitor:
                monitor.check_for_trade_events()
            
            # Sleep to prevent high CPU usage
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping trading...")
        executor.stop()
        trading_thread.join(timeout=5)
    except Exception as e:
        logger.error(f"Error in trading loop: {e}", exc_info=True)
        # Try to stop executor gracefully
        try:
            executor.stop()
        except:
            pass
    finally:
        logger.info("Trading system stopped")


if __name__ == "__main__":
    main() 