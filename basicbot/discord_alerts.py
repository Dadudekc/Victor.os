"""
discord_alerts.py - Discord integration for BasicBot trading alerts

This module provides Discord webhook integration for:
- Trade execution alerts
- Daily performance summaries
- System status updates
- Error notifications

Usage:
    from basicbot.discord_alerts import DiscordAlerts
    alerts = DiscordAlerts(webhook_url="https://discord.com/api/webhooks/...")
    alerts.send_trade_alert("BUY", "TSLA", 10, 250.50)
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import requests

# Handle both package and standalone imports
try:
    from basicbot.logger import setup_logging
except ImportError:
    from logger import setup_logging


class DiscordAlerts:
    """Discord webhook integration for BasicBot trading alerts."""
    
    def __init__(
        self, 
        webhook_url: Optional[str] = None,
        username: str = "BasicBot Trader",
        logger: Optional[logging.Logger] = None
    ):
        """Initialize Discord alerts.
        
        Args:
            webhook_url: Discord webhook URL
            username: Bot username to display in Discord
            logger: Logger instance
        """
        # Use webhook from env var if not provided
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
        self.username = username
        self.logger = logger or setup_logging("discord_alerts")
        
        # Track rate limiting
        self.last_message_time = 0
        self.rate_limit_seconds = 2  # Minimum seconds between messages
        
        # Validate webhook
        if not self.webhook_url:
            self.logger.warning("Discord webhook URL not provided - alerts will be logged but not sent")
        else:
            self.logger.info(f"Discord alerts initialized with webhook: {self.webhook_url[:20]}...")
    
    def send_message(
        self, 
        content: str, 
        embed: Optional[Dict[str, Any]] = None,
        color: int = 0x3498db  # Blue
    ) -> bool:
        """Send a message to Discord.
        
        Args:
            content: Message content
            embed: Discord embed object
            color: Embed color (hex color as int)
            
        Returns:
            Success status
        """
        if not self.webhook_url:
            self.logger.info(f"Discord message would be sent: {content}")
            return False
        
        # Check rate limiting
        now = time.time()
        time_since_last = now - self.last_message_time
        if time_since_last < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - time_since_last)
        
        # Prepare payload
        payload = {
            "username": self.username,
            "content": content
        }
        
        # Add embed if provided
        if embed:
            # Add color if not in embed
            if "color" not in embed:
                embed["color"] = color
                
            payload["embeds"] = [embed]
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            self.last_message_time = time.time()
            
            if response.status_code >= 400:
                self.logger.error(f"Discord API error: {response.status_code} - {response.text}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Discord message: {e}")
            return False
    
    def send_trade_alert(
        self, 
        side: str, 
        symbol: str, 
        quantity: Union[int, float], 
        price: float,
        profit_loss: Optional[float] = None
    ) -> bool:
        """Send a trade execution alert.
        
        Args:
            side: Trade side (BUY/SELL)
            symbol: Trading symbol
            quantity: Trade quantity
            price: Execution price
            profit_loss: Profit/loss amount (for SELL orders)
            
        Returns:
            Success status
        """
        # Determine emoji and color based on side
        if side.upper() == "BUY":
            emoji = "🟢"
            color = 0x2ecc71  # Green
            title = f"{emoji} BUY Order Executed"
        else:
            emoji = "🔴"
            color = 0xe74c3c  # Red
            title = f"{emoji} SELL Order Executed"
        
        # Calculate total value
        total_value = quantity * price
        
        # Build embed
        embed = {
            "title": title,
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {"name": "Symbol", "value": symbol, "inline": True},
                {"name": "Quantity", "value": str(quantity), "inline": True},
                {"name": "Price", "value": f"${price:.2f}", "inline": True},
                {"name": "Total Value", "value": f"${total_value:.2f}", "inline": True}
            ]
        }
        
        # Add P&L for sell orders
        if side.upper() == "SELL" and profit_loss is not None:
            profit_emoji = "📈" if profit_loss > 0 else "📉"
            embed["fields"].append({
                "name": "Profit/Loss",
                "value": f"{profit_emoji} ${profit_loss:.2f} ({profit_loss/total_value*100:.2f}%)",
                "inline": True
            })
        
        # Send the message
        return self.send_message(
            content=f"{emoji} **{side.upper()} {quantity} {symbol} @ ${price:.2f}**",
            embed=embed,
            color=color
        )
    
    def send_system_status(
        self, 
        status: Dict[str, Any],
        is_running: bool
    ) -> bool:
        """Send system status update.
        
        Args:
            status: Status dictionary
            is_running: Whether trading is active
            
        Returns:
            Success status
        """
        # Build emoji and color based on status
        if is_running:
            emoji = "✅"
            color = 0x2ecc71  # Green
            status_text = "ACTIVE"
        else:
            emoji = "⏹️"
            color = 0x95a5a6  # Gray
            status_text = "STOPPED"
        
        # Extract info from status
        symbols = status.get("symbols", [])
        symbols_str = ", ".join(symbols) if symbols else "None"
        
        mode = status.get("mode", "unknown")
        timeframe = status.get("timeframe", "unknown")
        position_count = status.get("position_count", 0)
        
        # Build embed
        embed = {
            "title": f"{emoji} BasicBot Trading Status: {status_text}",
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {"name": "Trading Mode", "value": mode.upper(), "inline": True},
                {"name": "Symbols", "value": symbols_str, "inline": True},
                {"name": "Timeframe", "value": timeframe, "inline": True},
                {"name": "Active Positions", "value": str(position_count), "inline": True}
            ]
        }
        
        # Add performance data if available
        performance = status.get("performance", {})
        if performance and isinstance(performance, dict):
            win_rate = performance.get("win_rate", 0)
            profit_loss = performance.get("profit_loss", 0)
            trade_count = performance.get("trade_count", 0)
            
            if trade_count > 0:
                embed["fields"].extend([
                    {"name": "Total Trades", "value": str(trade_count), "inline": True},
                    {"name": "Win Rate", "value": f"{win_rate*100:.1f}%", "inline": True},
                    {"name": "Total P&L", "value": f"${profit_loss:.2f}", "inline": True}
                ])
        
        # Send the message
        return self.send_message(
            content=f"{emoji} **BasicBot Status Update: {status_text}**",
            embed=embed,
            color=color
        )
    
    def send_performance_report(self, metrics: Dict[str, Any]) -> bool:
        """Send a performance report.
        
        Args:
            metrics: Performance metrics dictionary
            
        Returns:
            Success status
        """
        # Extract metrics
        trade_count = metrics.get("trade_count", 0)
        win_count = metrics.get("win_count", 0)
        loss_count = metrics.get("loss_count", 0)
        win_rate = metrics.get("win_rate", 0)
        profit_loss = metrics.get("profit_loss", 0)
        avg_win = metrics.get("avg_win", 0)
        avg_loss = metrics.get("avg_loss", 0)
        largest_win = metrics.get("largest_win", 0)
        largest_loss = metrics.get("largest_loss", 0)
        
        # Skip if no trades
        if trade_count == 0:
            self.logger.info("No trades to include in performance report")
            return False
        
        # Determine overall emoji and color
        if profit_loss > 0:
            emoji = "📈"
            color = 0x2ecc71  # Green
        else:
            emoji = "📉"
            color = 0xe74c3c  # Red
        
        # Build embed
        embed = {
            "title": f"{emoji} BasicBot Trading Performance Report",
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {"name": "Total Trades", "value": str(trade_count), "inline": True},
                {"name": "Winning Trades", "value": str(win_count), "inline": True},
                {"name": "Losing Trades", "value": str(loss_count), "inline": True},
                {"name": "Win Rate", "value": f"{win_rate*100:.1f}%", "inline": True},
                {"name": "Total P&L", "value": f"${profit_loss:.2f}", "inline": True},
                {"name": "Avg Win", "value": f"${avg_win:.2f}", "inline": True},
                {"name": "Avg Loss", "value": f"${avg_loss:.2f}", "inline": True},
                {"name": "Largest Win", "value": f"${largest_win:.2f}", "inline": True},
                {"name": "Largest Loss", "value": f"${largest_loss:.2f}", "inline": True}
            ]
        }
        
        # Send the message
        return self.send_message(
            content=f"{emoji} **Trading Performance Report: {win_rate*100:.1f}% Win Rate, ${profit_loss:.2f} P&L**",
            embed=embed,
            color=color
        )
    
    def send_error_alert(self, error_message: str, details: Optional[str] = None) -> bool:
        """Send an error alert.
        
        Args:
            error_message: Error message
            details: Additional error details
            
        Returns:
            Success status
        """
        # Build embed
        embed = {
            "title": "⚠️ BasicBot Error",
            "color": 0xe74c3c,  # Red
            "timestamp": datetime.now().isoformat(),
            "description": error_message
        }
        
        # Add details if provided
        if details:
            embed["fields"] = [
                {"name": "Details", "value": details[:1000], "inline": False}
            ]
        
        # Send the message
        return self.send_message(
            content=f"⚠️ **BasicBot Error: {error_message}**",
            embed=embed,
            color=0xe74c3c  # Red
        )


# For testing
if __name__ == "__main__":
    # Get webhook URL from environment
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL environment variable not set")
        print("Please set it to test the Discord alerts module")
        exit(1)
    
    # Test alerts
    alerts = DiscordAlerts(webhook_url=webhook_url)
    
    # Test trade alert
    print("Sending test trade alert...")
    alerts.send_trade_alert("BUY", "TSLA", 10, 250.50)
    time.sleep(2)
    alerts.send_trade_alert("SELL", "TSLA", 10, 255.75, profit_loss=52.50)
    
    # Test system status
    print("Sending test system status...")
    status = {
        "state": "running",
        "symbols": ["TSLA", "AAPL", "MSFT"],
        "mode": "paper",
        "timeframe": "15m",
        "position_count": 2,
        "performance": {
            "win_rate": 0.65,
            "profit_loss": 450.75,
            "trade_count": 20
        }
    }
    alerts.send_system_status(status, True)
    
    # Test performance report
    print("Sending test performance report...")
    metrics = {
        "trade_count": 20,
        "win_count": 13,
        "loss_count": 7,
        "win_rate": 0.65,
        "profit_loss": 450.75,
        "avg_win": 65.35,
        "avg_loss": -32.10,
        "largest_win": 120.50,
        "largest_loss": -75.25
    }
    alerts.send_performance_report(metrics)
    
    # Test error alert
    print("Sending test error alert...")
    alerts.send_error_alert(
        "Trading API connection failed",
        "HTTP 500 error connecting to Alpaca API. Retrying in 60 seconds."
    )
    
    print("All test messages sent!") 