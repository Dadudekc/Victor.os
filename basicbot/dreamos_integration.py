"""
dreamos_integration.py - Dream.OS Agent Integration for BasicBot

This script demonstrates how to integrate BasicBot with Dream.OS agents
to enable intelligent trading automation. It shows how agents can:
- Start/stop trading sessions based on market conditions
- Execute trades based on AI-generated signals
- Monitor and analyze portfolio performance
- Generate trading reports and alerts

Usage:
    python dreamos_integration.py
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Import BasicBot components
from basicbot.agent_interface import AgentTrader
from basicbot.logger import setup_logging
from basicbot.discord_alerts import DiscordAlerts

# Set up logging
logger = setup_logging("dreamos_integration")


class DreamOSAgent:
    """Example Dream.OS agent interface for trading automation."""
    
    def __init__(self):
        """Initialize the Dream.OS agent."""
        self.agent_trader = AgentTrader(logger=logger)
        
        # Try to initialize Discord alerts
        discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL")
        self.alerts = DiscordAlerts(webhook_url=discord_webhook) if discord_webhook else None
        
        # Agent state
        self.is_trading = False
        self.symbols = []
        self.market_conditions = {}
        self.analysis_results = {}
        
        logger.info("Dream.OS agent initialized")
        if self.alerts:
            self.alerts.send_message(
                "🤖 **Dream.OS Trading Agent Initialized**",
                {"description": "Agent is ready to receive trading commands"}
            )
    
    def analyze_market_conditions(self) -> Dict[str, Any]:
        """
        Analyze current market conditions.
        
        This would typically involve:
        1. Fetching market data
        2. Running ML models or technical analysis
        3. Determining market regime (bull, bear, sideways)
        
        Returns:
            Dictionary with market condition analysis
        """
        # For demo purposes, we'll return mock data
        # In a real system, this would call Dream.OS models and market data APIs
        conditions = {
            "market_regime": "bullish",  # bullish, bearish, sideways
            "volatility": "moderate",    # low, moderate, high
            "trend_strength": 0.75,      # 0-1 scale
            "sector_performance": {
                "technology": 0.85,
                "finance": 0.65,
                "healthcare": 0.40
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.market_conditions = conditions
        logger.info(f"Market analysis complete: {conditions['market_regime']} regime")
        
        return conditions
    
    def get_trading_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate trading recommendations based on market analysis.
        
        This would typically involve:
        1. Running trading strategy ML models
        2. Analyzing portfolio allocation
        3. Generating specific trade recommendations
        
        Returns:
            List of trade recommendations
        """
        # For demo purposes, we'll return mock recommendations
        # In a real system, this would call Dream.OS prediction models
        recommendations = []
        
        if self.market_conditions.get("market_regime") == "bullish":
            recommendations.append({
                "symbol": "AAPL",
                "action": "BUY",
                "confidence": 0.82,
                "reason": "Strong technical breakout with increasing volume",
                "target_price": 185.50,
                "stop_loss": 175.25
            })
            
            recommendations.append({
                "symbol": "MSFT",
                "action": "BUY",
                "confidence": 0.78,
                "reason": "Positive earnings momentum and sector leadership",
                "target_price": 420.00,
                "stop_loss": 395.50
            })
        
        elif self.market_conditions.get("market_regime") == "bearish":
            recommendations.append({
                "symbol": "TSLA",
                "action": "SELL",
                "confidence": 0.75,
                "reason": "Breaking support levels with increasing selling pressure",
                "target_price": 180.00,
                "stop_loss": 215.00
            })
        
        self.analysis_results["recommendations"] = recommendations
        logger.info(f"Generated {len(recommendations)} trading recommendations")
        
        return recommendations
    
    def auto_start_trading(self) -> bool:
        """
        Automatically start trading based on favorable conditions.
        
        Returns:
            Success status
        """
        # Analyze market conditions
        conditions = self.analyze_market_conditions()
        
        # Get trading recommendations
        recommendations = self.get_trading_recommendations()
        
        # Determine if conditions are favorable for trading
        favorable_conditions = (
            conditions.get("market_regime") in ["bullish", "sideways"] and
            conditions.get("volatility") != "high" and
            conditions.get("trend_strength", 0) > 0.6 and
            len(recommendations) > 0
        )
        
        if favorable_conditions:
            logger.info("Favorable market conditions detected, starting trading")
            
            # Get symbols from recommendations
            symbols = [rec["symbol"] for rec in recommendations]
            
            # Start trading
            response = self.agent_trader.execute_command({
                "action": "start_trading",
                "symbols": symbols,
                "timeframe": "15m",
                "risk": 1.0,
                "paper": True  # Use paper trading by default
            })
            
            if response.get("status") == "success":
                self.is_trading = True
                self.symbols = symbols
                
                # Send alert if Discord is configured
                if self.alerts:
                    self.alerts.send_message(
                        "🚀 **Dream.OS Agent Started Trading**",
                        {
                            "description": f"Auto-started trading based on favorable market conditions",
                            "fields": [
                                {"name": "Market Regime", "value": conditions.get("market_regime", "unknown"), "inline": True},
                                {"name": "Volatility", "value": conditions.get("volatility", "unknown"), "inline": True},
                                {"name": "Trend Strength", "value": f"{conditions.get('trend_strength', 0)*100:.0f}%", "inline": True},
                                {"name": "Symbols", "value": ", ".join(symbols), "inline": False}
                            ]
                        }
                    )
                
                return True
            else:
                logger.error(f"Failed to start trading: {response.get('message')}")
                return False
        else:
            logger.info("Market conditions unfavorable for trading")
            return False
    
    def execute_recommended_trades(self) -> List[Dict[str, Any]]:
        """
        Execute trades based on recommendations.
        
        Returns:
            List of trade execution results
        """
        if not self.is_trading:
            logger.warning("Cannot execute trades without active trading session")
            return []
        
        # Get recommendations
        recommendations = self.analysis_results.get("recommendations", [])
        if not recommendations:
            recommendations = self.get_trading_recommendations()
        
        # Track results
        results = []
        
        # Execute each recommendation
        for rec in recommendations:
            symbol = rec["symbol"]
            action = rec["action"]
            confidence = rec["confidence"]
            
            # Only execute high confidence trades
            if confidence < 0.75:
                logger.info(f"Skipping low confidence trade: {symbol} {action} ({confidence:.2f})")
                continue
            
            # Determine quantity based on account size and risk
            # In a real system, this would use portfolio allocation models
            quantity = 10  # Simplified for demo
            
            # Map action to side
            side = "buy" if action == "BUY" else "sell"
            
            # Execute the trade
            logger.info(f"Executing {side} for {symbol} (confidence: {confidence:.2f})")
            response = self.agent_trader.execute_command({
                "action": "execute_trade",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "paper": True  # Use paper trading by default
            })
            
            # Save result
            results.append({
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "status": response.get("status"),
                "response": response
            })
            
            # Log result
            if response.get("status") == "success":
                logger.info(f"Successfully executed {side} for {symbol}")
            else:
                logger.error(f"Failed to execute {side} for {symbol}: {response.get('message')}")
        
        return results
    
    def monitor_portfolio_performance(self) -> Dict[str, Any]:
        """
        Monitor portfolio performance and make adjustments.
        
        Returns:
            Performance metrics
        """
        # Get current status
        status_response = self.agent_trader.execute_command({"action": "get_status"})
        
        # Get performance metrics
        metrics_response = self.agent_trader.execute_command({"action": "get_performance_metrics"})
        
        if status_response.get("status") == "success" and metrics_response.get("status") == "success":
            metrics = metrics_response.get("metrics", {})
            
            # Log performance
            logger.info(f"Portfolio performance: Win rate {metrics.get('win_rate', 0)*100:.1f}%, P&L ${metrics.get('profit_loss', 0):.2f}")
            
            # Optionally send report to Discord
            if self.alerts and metrics.get("trade_count", 0) > 0:
                self.alerts.send_performance_report(metrics)
            
            return metrics
        else:
            logger.error("Failed to get performance metrics")
            return {}
    
    def daily_trading_routine(self):
        """Run a complete daily trading routine."""
        logger.info("Starting daily trading routine")
        
        try:
            # 1. Analyze market conditions
            conditions = self.analyze_market_conditions()
            
            # 2. Start trading if conditions are favorable
            if not self.is_trading:
                self.auto_start_trading()
            
            # 3. Execute recommended trades
            if self.is_trading:
                self.execute_recommended_trades()
            
            # 4. Monitor performance
            metrics = self.monitor_portfolio_performance()
            
            # 5. Stop trading at end of day
            if self.is_trading:
                current_hour = datetime.now().hour
                if current_hour >= 16:  # After market close
                    logger.info("End of trading day, stopping trading")
                    self.agent_trader.execute_command({"action": "stop_trading"})
                    self.is_trading = False
            
            logger.info("Daily trading routine completed")
            
        except Exception as e:
            logger.error(f"Error in daily trading routine: {e}", exc_info=True)
            
            # Notify about error
            if self.alerts:
                self.alerts.send_error_alert(
                    "Error in trading routine",
                    str(e)
                )


def run_dream_agent_demo():
    """Run a demonstration of the Dream.OS trading agent."""
    print("Starting Dream.OS Trading Agent Demo")
    print("=" * 50)
    
    # Create agent
    agent = DreamOSAgent()
    
    # Run initial demo cycle
    print("\n1. Analyzing market conditions...")
    conditions = agent.analyze_market_conditions()
    print(f"   Market regime: {conditions.get('market_regime')}")
    print(f"   Volatility: {conditions.get('volatility')}")
    print(f"   Trend strength: {conditions.get('trend_strength')}")
    
    print("\n2. Generating trading recommendations...")
    recommendations = agent.get_trading_recommendations()
    for i, rec in enumerate(recommendations, 1):
        print(f"   Recommendation {i}: {rec['action']} {rec['symbol']} (confidence: {rec['confidence']:.2f})")
        print(f"     Reason: {rec['reason']}")
    
    print("\n3. Starting automated trading...")
    success = agent.auto_start_trading()
    print(f"   Trading started: {'Yes' if success else 'No'}")
    
    if success:
        print("\n4. Executing recommended trades...")
        results = agent.execute_recommended_trades()
        for i, res in enumerate(results, 1):
            print(f"   Trade {i}: {res['side'].upper()} {res['symbol']} - {res['status']}")
        
        print("\n5. Monitoring portfolio performance...")
        metrics = agent.monitor_portfolio_performance()
        if metrics:
            print(f"   Trades: {metrics.get('trade_count', 0)}")
            print(f"   Win rate: {metrics.get('win_rate', 0)*100:.1f}%")
            print(f"   P&L: ${metrics.get('profit_loss', 0):.2f}")
        
        print("\n6. Stopping trading session...")
        agent.agent_trader.execute_command({"action": "stop_trading"})
        print("   Trading stopped")
    
    print("\nDemo complete! In a production environment, this agent would:")
    print("- Run on a schedule (e.g., daily before market open)")
    print("- Continuously monitor portfolio and market conditions")
    print("- Adjust positions based on real-time signals")
    print("- Generate reports and alerts for human review")
    print("=" * 50)


if __name__ == "__main__":
    run_dream_agent_demo() 