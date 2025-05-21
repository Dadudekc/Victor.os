"""
TBOW Tactics - Trading Intelligence System

This module implements the TBOW Tactics system, which provides:
- Market context scanning
- Indicator analysis
- Bias engine
- Checklist compliance
- Trade journal integration
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime

from basicbot.strategy import Strategy
from basicbot.ml_models.trading_ai import TradingAI
from basicbot.ml_models.regime_detector import RegimeDetector

class TBOWTactics:
    """
    TBOW Tactics trading intelligence system.
    
    This class provides a comprehensive trading decision support system that:
    1. Scans market context (trends, gaps, volatility)
    2. Analyzes technical indicators
    3. Generates trading bias
    4. Enforces checklist compliance
    5. Integrates with trade journal
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "5Min",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize TBOW Tactics system.
        
        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            logger: Optional logger instance
        """
        # Setup logger
        self.logger = logger or logging.getLogger(__name__)
        
        # Store parameters
        self.symbol = symbol
        self.timeframe = timeframe
        
        # Initialize components
        self.strategy = Strategy(symbol=symbol, timeframe=timeframe)
        self.trading_ai = TradingAI()
        self.regime_detector = RegimeDetector()
        
        # Initialize state
        self.current_bias = "NEUTRAL"
        self.confidence_score = "DNP"  # Do Not Play
        self.checklist_status = {}
        self.last_scan_time = None
        
        self.logger.info(f"TBOW Tactics initialized for {symbol} @ {timeframe}")
    
    def scan_market_context(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Scan market context including trends, gaps, and volatility.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with market context analysis
        """
        context = {
            "trend": self._detect_trend(data),
            "gaps": self._analyze_gaps(data),
            "volatility": self._analyze_volatility(data),
            "regime": self.regime_detector.detect_regime(data),
            "timestamp": datetime.now().isoformat()
        }
        
        self.last_scan_time = datetime.now()
        return context
    
    def analyze_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze technical indicators for trading signals.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with indicator analysis
        """
        # Calculate indicators
        data = self.strategy.calculate_indicators(data)
        
        # Extract latest values
        latest = data.iloc[-1]
        
        analysis = {
            "macd": {
                "value": latest.get("MACD", 0),
                "signal": latest.get("MACD_signal", 0),
                "histogram": latest.get("MACD_hist", 0),
                "trend": "bullish" if latest.get("MACD", 0) > latest.get("MACD_signal", 0) else "bearish"
            },
            "rsi": {
                "value": latest.get("RSI", 50),
                "trend": "oversold" if latest.get("RSI", 50) < 30 else "overbought" if latest.get("RSI", 50) > 70 else "neutral"
            },
            "vwap": {
                "value": latest.get("VWAP", 0),
                "position": "above" if latest.get("close", 0) > latest.get("VWAP", 0) else "below"
            },
            "volume": {
                "value": latest.get("volume", 0),
                "strength": self._analyze_volume_strength(data)
            },
            "bollinger": {
                "squeeze": self._detect_bb_squeeze(data),
                "position": self._get_bb_position(data)
            }
        }
        
        return analysis
    
    def generate_bias(self, context: Dict[str, Any], indicators: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate trading bias based on market context and indicators.
        
        Args:
            context: Market context analysis
            indicators: Technical indicator analysis
            
        Returns:
            Dictionary with bias and confidence score
        """
        # Initialize bias components
        trend_score = 0
        momentum_score = 0
        volatility_score = 0
        
        # Score trend alignment
        if context["trend"] == "bullish":
            trend_score += 1
        elif context["trend"] == "bearish":
            trend_score -= 1
            
        # Score momentum
        if indicators["macd"]["trend"] == "bullish":
            momentum_score += 1
        elif indicators["macd"]["trend"] == "bearish":
            momentum_score -= 1
            
        # Score volatility
        if context["volatility"]["state"] == "low":
            volatility_score += 1
        elif context["volatility"]["state"] == "high":
            volatility_score -= 1
            
        # Calculate total score
        total_score = trend_score + momentum_score + volatility_score
        
        # Determine bias
        if total_score >= 2:
            bias = "BULLISH"
            confidence = "A+"
        elif total_score >= 1:
            bias = "BULLISH"
            confidence = "B"
        elif total_score <= -2:
            bias = "BEARISH"
            confidence = "A+"
        elif total_score <= -1:
            bias = "BEARISH"
            confidence = "B"
        else:
            bias = "NEUTRAL"
            confidence = "DNP"
            
        # Store current bias
        self.current_bias = bias
        self.confidence_score = confidence
        
        return {
            "bias": bias,
            "confidence": confidence,
            "scores": {
                "trend": trend_score,
                "momentum": momentum_score,
                "volatility": volatility_score,
                "total": total_score
            }
        }
    
    def check_compliance(self, context: Dict[str, Any], indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check trading checklist compliance.
        
        Args:
            context: Market context analysis
            indicators: Technical indicator analysis
            
        Returns:
            Dictionary with checklist status
        """
        checklist = {
            "market_alignment": {
                "status": self._check_market_alignment(context),
                "required": True
            },
            "indicator_confluence": {
                "status": self._check_indicator_confluence(indicators),
                "required": True
            },
            "volatility_check": {
                "status": self._check_volatility(context),
                "required": True
            },
            "risk_management": {
                "status": self._check_risk_management(),
                "required": True
            }
        }
        
        # Calculate overall status
        all_required_passed = all(
            item["status"] for item in checklist.values() 
            if item["required"]
        )
        
        checklist["overall"] = {
            "status": all_required_passed,
            "ready_to_trade": all_required_passed and self.confidence_score != "DNP"
        }
        
        self.checklist_status = checklist
        return checklist
    
    def log_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        Log trade details to journal.
        
        Args:
            trade_data: Dictionary with trade details
            
        Returns:
            bool: True if successful
        """
        try:
            # Add TBOW-specific data
            trade_data.update({
                "bias": self.current_bias,
                "confidence": self.confidence_score,
                "checklist": self.checklist_status,
                "timestamp": datetime.now().isoformat()
            })
            
            # TODO: Implement trade journal storage
            # For now, just log it
            self.logger.info(f"Trade logged: {trade_data}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging trade: {e}")
            return False
    
    def _detect_trend(self, data: pd.DataFrame) -> str:
        """Detect market trend."""
        if len(data) < 2:
            return "unknown"
            
        # Calculate short and long SMAs
        data = self.strategy.calculate_indicators(data)
        
        # Get latest values
        latest = data.iloc[-1]
        
        # Check trend alignment
        if latest["SMA_short"] > latest["SMA_long"]:
            return "bullish"
        elif latest["SMA_short"] < latest["SMA_long"]:
            return "bearish"
        else:
            return "neutral"
    
    def _analyze_gaps(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price gaps."""
        if len(data) < 2:
            return {"has_gap": False}
            
        # Calculate gaps
        data["gap_up"] = data["low"] > data["high"].shift(1)
        data["gap_down"] = data["high"] < data["low"].shift(1)
        
        # Get latest gap
        latest = data.iloc[-1]
        
        return {
            "has_gap": latest["gap_up"] or latest["gap_down"],
            "direction": "up" if latest["gap_up"] else "down" if latest["gap_down"] else "none",
            "size": abs(latest["close"] - data["close"].iloc[-2]) / data["close"].iloc[-2] * 100
        }
    
    def _analyze_volatility(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market volatility."""
        if len(data) < 20:
            return {"state": "unknown"}
            
        # Calculate ATR
        data = self.strategy.calculate_indicators(data)
        
        # Get latest ATR
        latest_atr = data["ATR"].iloc[-1]
        avg_atr = data["ATR"].mean()
        
        # Determine volatility state
        if latest_atr > avg_atr * 1.5:
            state = "high"
        elif latest_atr < avg_atr * 0.5:
            state = "low"
        else:
            state = "normal"
            
        return {
            "state": state,
            "current_atr": latest_atr,
            "avg_atr": avg_atr,
            "ratio": latest_atr / avg_atr
        }
    
    def _analyze_volume_strength(self, data: pd.DataFrame) -> str:
        """Analyze volume strength."""
        if len(data) < 20:
            return "unknown"
            
        # Calculate volume moving average
        data["volume_ma"] = data["volume"].rolling(20).mean()
        
        # Get latest volume
        latest = data.iloc[-1]
        
        # Determine volume strength
        if latest["volume"] > latest["volume_ma"] * 1.5:
            return "strong"
        elif latest["volume"] < latest["volume_ma"] * 0.5:
            return "weak"
        else:
            return "normal"
    
    def _detect_bb_squeeze(self, data: pd.DataFrame) -> bool:
        """Detect Bollinger Band squeeze."""
        if len(data) < 20:
            return False
            
        # Calculate Bollinger Bands
        data["bb_width"] = (data["bb_upper"] - data["bb_lower"]) / data["bb_middle"]
        
        # Get latest width
        latest = data.iloc[-1]
        avg_width = data["bb_width"].mean()
        
        return latest["bb_width"] < avg_width * 0.8
    
    def _get_bb_position(self, data: pd.DataFrame) -> str:
        """Get price position relative to Bollinger Bands."""
        if len(data) < 20:
            return "unknown"
            
        # Get latest values
        latest = data.iloc[-1]
        
        # Determine position
        if latest["close"] > latest["bb_upper"]:
            return "above"
        elif latest["close"] < latest["bb_lower"]:
            return "below"
        else:
            return "inside"
    
    def _check_market_alignment(self, context: Dict[str, Any]) -> bool:
        """Check market alignment."""
        # Market should be in a clear trend
        if context["trend"] == "neutral":
            return False
            
        # No significant gaps
        if context["gaps"]["has_gap"]:
            return False
            
        # Volatility should be normal or low
        if context["volatility"]["state"] == "high":
            return False
            
        return True
    
    def _check_indicator_confluence(self, indicators: Dict[str, Any]) -> bool:
        """Check indicator confluence."""
        # MACD and RSI should align
        macd_trend = indicators["macd"]["trend"]
        rsi_trend = indicators["rsi"]["trend"]
        
        if macd_trend == "bullish" and rsi_trend == "oversold":
            return False
        if macd_trend == "bearish" and rsi_trend == "overbought":
            return False
            
        # Volume should be normal or strong
        if indicators["volume"]["strength"] == "weak":
            return False
            
        return True
    
    def _check_volatility(self, context: Dict[str, Any]) -> bool:
        """Check volatility conditions."""
        # Volatility should be normal or low
        if context["volatility"]["state"] == "high":
            return False
            
        # No significant gaps
        if context["gaps"]["has_gap"]:
            return False
            
        return True
    
    def _check_risk_management(self) -> bool:
        """Check risk management conditions."""
        # TODO: Implement risk management checks
        # For now, return True
        return True 