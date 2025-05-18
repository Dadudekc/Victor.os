#!/usr/bin/env python
"""
start_paper_trading.py - Quick start script for BasicBot paper trading

This script provides a simple way to start BasicBot in paper trading mode
with default settings and a few popular symbols.

Usage:
    python start_paper_trading.py [--discord] [--agent] [--daemon]
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Ensure we're in the right directory
script_dir = Path(__file__).resolve().parent
os.chdir(script_dir)

# Default symbols to trade
DEFAULT_SYMBOLS = ["AAPL", "MSFT", "TSLA", "AMZN", "GOOGL"]


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Start BasicBot paper trading with defaults")
    
    parser.add_argument("--discord", action="store_true",
                        help="Enable Discord notifications")
    
    parser.add_argument("--agent", action="store_true",
                        help="Start in agent interface mode")
    
    parser.add_argument("--daemon", action="store_true",
                        help="Run as a background daemon process")
    
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS,
                        help=f"Trading symbols (default: {', '.join(DEFAULT_SYMBOLS)})")
    
    parser.add_argument("--risk", type=float, default=1.0,
                        help="Risk percentage per trade (default: 1.0)")
    
    parser.add_argument("--timeframe", type=str, default="15m",
                        help="Data timeframe (default: 15m)")
    
    return parser.parse_args()


def check_dependencies():
    """Check if required packages are installed"""
    try:
        import pandas
        import alpaca_trade_api
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required dependencies with: pip install -r requirements.txt")
        return False


def check_api_keys():
    """Check if Alpaca API keys are set"""
    # Check environment variables first
    api_key = os.environ.get("ALPACA_API_KEY")
    api_secret = os.environ.get("ALPACA_API_SECRET")
    
    # If not in environment, check for .env file
    if not (api_key and api_secret):
        env_path = script_dir.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        if key == "ALPACA_API_KEY":
                            api_key = value
                        elif key == "ALPACA_API_SECRET":
                            api_secret = value
    
    if not (api_key and api_secret):
        print("Alpaca API keys not found.")
        print("Please set ALPACA_API_KEY and ALPACA_API_SECRET in your environment")
        print("or create a .env file in the project root.")
        return False
    
    return True


def check_discord_webhook():
    """Check if Discord webhook is set when Discord option is enabled"""
    discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    
    # If not in environment, check for .env file
    if not discord_webhook:
        env_path = script_dir.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        if key == "DISCORD_WEBHOOK_URL":
                            discord_webhook = value
    
    return discord_webhook is not None


def start_paper_trading():
    """Start paper trading with BasicBot"""
    args = parse_args()
    
    # Check if we should start in agent mode
    if args.agent:
        print("Starting BasicBot in agent interface mode...")
        
        # Build command
        cmd = [
            sys.executable,
            str(script_dir / "main_trader.py"),
            "--agent_mode"
        ]
        
        # Start the process
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\nStopping agent interface...")
        
        return
    
    # Check dependencies and API keys
    if not check_dependencies() or not check_api_keys():
        return
    
    # Check Discord webhook if Discord is enabled
    if args.discord and not check_discord_webhook():
        print("\nDiscord notifications enabled but DISCORD_WEBHOOK_URL not found.")
        print("Please set DISCORD_WEBHOOK_URL in your environment or .env file.")
        print("Continuing without Discord notifications...")
        args.discord = False
    
    print("Starting BasicBot in paper trading mode...")
    print(f"Trading symbols: {', '.join(args.symbols)}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Risk per trade: {args.risk}%")
    print(f"Discord alerts: {'Enabled' if args.discord else 'Disabled'}")
    print(f"Daemon mode: {'Enabled' if args.daemon else 'Disabled'}")
    print("Press Ctrl+C to stop trading")
    print("-" * 50)
    
    # Build command
    cmd = [
        sys.executable,
        str(script_dir / "main_trader.py"),
        "--symbols"] + args.symbols + [
        "--timeframe", args.timeframe,
        "--risk", str(args.risk),
        "--poll_interval", "60",
        "--paper",
        "--log_level", "INFO",
        "--db_log"
    ]
    
    # Add Discord if enabled
    if args.discord:
        cmd.append("--discord")
        cmd.append("--daily_report")
    
    # Add daemon if enabled
    if args.daemon:
        cmd.append("--daemon")
    
    # Start the trading process
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nStopping paper trading...")


if __name__ == "__main__":
    start_paper_trading() 