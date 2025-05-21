"""
TBOW Tactics Replay Module

This module provides functionality for replaying historical market data and analyzing
trading decisions based on the TBOW Tactics system. It helps traders:
1. Review past setups and decisions
2. Train on historical scenarios
3. Validate checklist effectiveness
4. Analyze missed opportunities
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

from basicbot.tbow_tactics import TBOWTactics
from basicbot.strategy import Strategy

class TBOWReplay:
    """
    TBOW Tactics replay system for historical analysis.
    
    This class allows traders to:
    - Replay historical market data
    - Analyze trading decisions
    - Validate checklist effectiveness
    - Train on past scenarios
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "5Min",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize TBOW Replay system.
        
        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.symbol = symbol
        self.timeframe = timeframe
        
        # Initialize TBOW Tactics
        self.tbow = TBOWTactics(symbol=symbol, timeframe=timeframe)
        
        # Replay state
        self.current_index = 0
        self.historical_data = None
        self.replay_results = []
        
        self.logger.info(f"TBOW Replay initialized for {symbol} @ {timeframe}")
    
    def load_historical_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> bool:
        """
        Load historical data for replay.
        
        Args:
            start_date: Start date for historical data
            end_date: Optional end date (defaults to now)
            
        Returns:
            bool: True if successful
        """
        try:
            # Fetch historical data
            self.historical_data = self.tbow.strategy.fetch_historical_data(
                start_date=start_date,
                end_date=end_date or datetime.now()
            )
            
            if self.historical_data is None or self.historical_data.empty:
                self.logger.error("No historical data available")
                return False
            
            # Reset replay state
            self.current_index = 0
            self.replay_results = []
            
            self.logger.info(
                f"Loaded {len(self.historical_data)} candles from "
                f"{start_date} to {end_date or datetime.now()}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
            return False
    
    def step_forward(self) -> Optional[Dict[str, Any]]:
        """
        Step forward one candle in the replay.
        
        Returns:
            Dictionary with current state analysis or None if at end
        """
        if self.historical_data is None or self.current_index >= len(self.historical_data):
            return None
        
        try:
            # Get data up to current index
            current_data = self.historical_data.iloc[:self.current_index + 1]
            
            # Analyze current state
            context = self.tbow.scan_market_context(current_data)
            indicators = self.tbow.analyze_indicators(current_data)
            bias = self.tbow.generate_bias(context, indicators)
            checklist = self.tbow.check_compliance(context, indicators)
            
            # Store results
            result = {
                "timestamp": current_data.index[-1],
                "price": current_data["close"].iloc[-1],
                "context": context,
                "indicators": indicators,
                "bias": bias,
                "checklist": checklist
            }
            self.replay_results.append(result)
            
            # Move to next candle
            self.current_index += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in replay step: {e}")
            return None
    
    def step_backward(self) -> Optional[Dict[str, Any]]:
        """
        Step backward one candle in the replay.
        
        Returns:
            Dictionary with current state analysis or None if at start
        """
        if self.current_index <= 0:
            return None
        
        self.current_index -= 1
        return self.replay_results[self.current_index]
    
    def jump_to(self, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """
        Jump to a specific timestamp in the replay.
        
        Args:
            timestamp: Target timestamp
            
        Returns:
            Dictionary with state analysis or None if timestamp not found
        """
        if self.historical_data is None:
            return None
        
        try:
            # Find closest index
            self.current_index = self.historical_data.index.get_indexer([timestamp])[0]
            if self.current_index < 0:
                return None
            
            # Get data up to current index
            current_data = self.historical_data.iloc[:self.current_index + 1]
            
            # Analyze current state
            context = self.tbow.scan_market_context(current_data)
            indicators = self.tbow.analyze_indicators(current_data)
            bias = self.tbow.generate_bias(context, indicators)
            checklist = self.tbow.check_compliance(context, indicators)
            
            # Store results
            result = {
                "timestamp": current_data.index[-1],
                "price": current_data["close"].iloc[-1],
                "context": context,
                "indicators": indicators,
                "bias": bias,
                "checklist": checklist
            }
            
            # Update replay results
            if len(self.replay_results) > self.current_index:
                self.replay_results[self.current_index] = result
            else:
                self.replay_results.append(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error jumping to timestamp: {e}")
            return None
    
    def analyze_setup(self, index: int) -> Dict[str, Any]:
        """
        Analyze a specific setup in the replay.
        
        Args:
            index: Index in replay results
            
        Returns:
            Dictionary with setup analysis
        """
        if not 0 <= index < len(self.replay_results):
            return {"error": "Invalid index"}
        
        result = self.replay_results[index]
        
        # Analyze setup quality
        setup_quality = {
            "bias_strength": result["bias"]["confidence"],
            "checklist_score": sum(
                1 for item in result["checklist"].values()
                if item.get("status", False)
            ),
            "indicator_confluence": self._analyze_confluence(result["indicators"]),
            "market_alignment": result["context"].get("market_aligned", False)
        }
        
        # Calculate overall score
        setup_quality["overall_score"] = self._calculate_setup_score(setup_quality)
        
        return setup_quality
    
    def _analyze_confluence(self, indicators: Dict[str, Any]) -> int:
        """Analyze indicator confluence."""
        confluence_score = 0
        
        # MACD trend
        if indicators["macd"]["trend"] != "neutral":
            confluence_score += 1
        
        # RSI extremes
        if indicators["rsi"]["trend"] in ["oversold", "overbought"]:
            confluence_score += 1
        
        # VWAP position
        if indicators["vwap"]["position"] != "at":
            confluence_score += 1
        
        # Volume strength
        if indicators["volume"]["strength"] == "strong":
            confluence_score += 1
        
        # Bollinger squeeze
        if indicators["bollinger"]["squeeze"]:
            confluence_score += 1
        
        return confluence_score
    
    def _calculate_setup_score(self, setup_quality: Dict[str, Any]) -> float:
        """Calculate overall setup score."""
        score = 0.0
        
        # Bias strength (40%)
        bias_weights = {"A+": 1.0, "B": 0.7, "C": 0.4, "DNP": 0.0}
        score += bias_weights.get(setup_quality["bias_strength"], 0) * 0.4
        
        # Checklist score (30%)
        score += (setup_quality["checklist_score"] / 6) * 0.3
        
        # Indicator confluence (20%)
        score += (setup_quality["indicator_confluence"] / 5) * 0.2
        
        # Market alignment (10%)
        score += 0.1 if setup_quality["market_alignment"] else 0
        
        return score
    
    def export_analysis(self, filepath: str) -> bool:
        """
        Export replay analysis to CSV.
        
        Args:
            filepath: Path to save CSV file
            
        Returns:
            bool: True if successful
        """
        try:
            # Convert results to DataFrame
            df = pd.DataFrame([
                {
                    "timestamp": r["timestamp"],
                    "price": r["price"],
                    "bias": r["bias"]["bias"],
                    "confidence": r["bias"]["confidence"],
                    "checklist_score": sum(
                        1 for item in r["checklist"].values()
                        if item.get("status", False)
                    ),
                    "market_aligned": r["context"].get("market_aligned", False),
                    "setup_score": self._calculate_setup_score(
                        self.analyze_setup(i)
                    )
                }
                for i, r in enumerate(self.replay_results)
            ])
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            
            self.logger.info(f"Analysis exported to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting analysis: {e}")
            return False 