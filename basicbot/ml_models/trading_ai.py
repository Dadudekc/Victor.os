"""
trading_ai.py - ML Model Integration for BasicBot Trading System

This module integrates machine learning models with the BasicBot trading system:
- Loads trained models
- Adapts trading strategies based on market regimes
- Generates ML-enhanced signals
- Provides adaptive position sizing

Usage:
    from basicbot.ml_models.trading_ai import TradingAI
    ai = TradingAI()
    enhanced_signals = ai.enhance_signals(data, signals)
"""

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# Import ML modules
from basicbot.ml_models.regime_detector import RegimeDetector

# Import BasicBot components 
try:
    from basicbot.logger import setup_logging
except ImportError:
    # For standalone testing
    import sys
    script_dir = Path(__file__).resolve().parent
    parent_dir = script_dir.parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.append(str(parent_dir))
    
    try:
        from basicbot.logger import setup_logging
    except ImportError:
        # Simple logger if BasicBot not available
        def setup_logging(name):
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            return logger


class TradingAI:
    """
    AI-enhanced trading logic that integrates machine learning models
    with BasicBot's trading strategies.
    """
    
    def __init__(
        self,
        model_dir: str = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the TradingAI module.
        
        Args:
            model_dir: Directory containing trained models
            logger: Logger instance
        """
        self.logger = logger or setup_logging("trading_ai")
        
        # Set model directory
        if model_dir is None:
            self.model_dir = Path(__file__).resolve().parent / "models"
        else:
            self.model_dir = Path(model_dir)
        
        # Initialize models
        self.regime_detector = None
        self.price_predictor = None
        
        # Current state
        self.current_regime = {}
        self.current_predictions = {}
        self.strategy_adaptations = {}
        
        # Load models
        self._load_models()
        
        self.logger.info("TradingAI initialized")
    
    def _load_models(self):
        """Load all available ML models."""
        try:
            # Try to load regime detector
            self.regime_detector = RegimeDetector(model_dir=str(self.model_dir), logger=self.logger)
            
            # TODO: Add other models as they are implemented
            # self.price_predictor = PricePredictor(model_dir=str(self.model_dir))
            
            self.logger.info("ML models loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading ML models: {e}")
    
    def detect_market_regime(
        self, 
        symbol: str,
        data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Detect current market regime for a symbol.
        
        Args:
            symbol: Trading symbol
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with regime detection results
        """
        if self.regime_detector is None:
            self.logger.warning("Regime detector not available")
            return {
                "regime": "unknown",
                "confidence": 0.0,
                "available": False
            }
        
        try:
            # Ensure enough data
            if len(data) < 50:
                self.logger.warning(f"Insufficient data for regime detection: {len(data)} rows")
                return {
                    "regime": "unknown",
                    "confidence": 0.0,
                    "available": False
                }
            
            # Make prediction
            prediction = self.regime_detector.predict(data)
            
            # Store current regime
            self.current_regime[symbol] = prediction
            
            # Log regime detection
            self.logger.info(
                f"Detected regime for {symbol}: {prediction['regime']} "
                f"(confidence: {prediction['confidence']:.2f})"
            )
            
            # Add available flag
            prediction["available"] = True
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime for {symbol}: {e}")
            return {
                "regime": "unknown",
                "confidence": 0.0,
                "available": False,
                "error": str(e)
            }
    
    def adapt_strategy(
        self,
        symbol: str,
        regime_prediction: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get adaptive strategy parameters based on market regime.
        
        Args:
            symbol: Trading symbol
            regime_prediction: Optional regime prediction (if already available)
            
        Returns:
            Dictionary with adapted strategy parameters
        """
        # Use provided prediction or stored one
        prediction = regime_prediction or self.current_regime.get(symbol, {})
        
        # If no prediction available, return default parameters
        if not prediction or prediction.get("regime") == "unknown":
            self.logger.warning(f"No regime prediction available for {symbol}, using default strategy")
            return {
                "strategy_type": "default",
                "position_size_modifier": 1.0,
                "available": False
            }
        
        # Get strategy recommendations from regime
        if self.regime_detector:
            strategy = self.regime_detector.get_regime_strategy(prediction)
            
            # Store strategy adaptations
            self.strategy_adaptations[symbol] = strategy
            
            # Log strategy adaptation
            self.logger.info(
                f"Adapted strategy for {symbol} ({prediction['regime']}): "
                f"{strategy['strategy_type']}, position modifier: {strategy['position_size_modifier']:.2f}x"
            )
            
            # Add available flag
            strategy["available"] = True
            
            return strategy
        
        # Fallback if no regime detector
        return {
            "strategy_type": "default",
            "position_size_modifier": 1.0,
            "available": False
        }
    
    def enhance_signals(
        self,
        symbol: str,
        data: pd.DataFrame,
        signals: pd.Series
    ) -> pd.Series:
        """
        Enhance trading signals using ML models.
        
        Args:
            symbol: Trading symbol
            data: DataFrame with OHLCV and indicator data
            signals: Original trading signals (BUY/SELL/HOLD)
            
        Returns:
            Enhanced signals with ML insights
        """
        # Create a copy of signals to avoid modifying the original
        enhanced_signals = signals.copy()
        
        # Detect market regime
        regime = self.detect_market_regime(symbol, data)
        
        # Adapt strategy based on regime
        strategy = self.adapt_strategy(symbol, regime)
        
        if not regime.get("available"):
            self.logger.info(f"No ML enhancements applied to {symbol} signals (regime detection unavailable)")
            return enhanced_signals
        
        # Apply strategy-specific adjustments to signals
        strategy_type = strategy.get("strategy_type", "default")
        
        # For mean reversion strategy in mean-reverting regime
        if strategy_type == "mean_reversion":
            # Enhance mean reversion signals
            self._enhance_mean_reversion_signals(enhanced_signals, data, strategy)
            
        # For momentum strategy in trending regimes
        elif strategy_type == "momentum":
            # Enhance momentum signals
            self._enhance_momentum_signals(enhanced_signals, data, strategy)
            
        # For high volatility regime
        elif strategy_type == "neutral":
            # Reduce trading frequency in high volatility
            self._reduce_signal_frequency(enhanced_signals, strategy)
        
        # Count changes made
        changes = (enhanced_signals != signals).sum()
        if changes > 0:
            self.logger.info(f"ML models modified {changes} signals for {symbol}")
            
        return enhanced_signals
    
    def _enhance_mean_reversion_signals(
        self,
        signals: pd.Series,
        data: pd.DataFrame,
        strategy: Dict[str, Any]
    ) -> None:
        """
        Enhance signals for mean-reverting market regimes.
        
        Args:
            signals: Trading signals to enhance
            data: Market data
            strategy: Strategy parameters
        """
        # Filter signals based on mean reversion characteristics
        if "bb_pos" in data.columns:  # Bollinger Band position
            # Entry threshold from strategy
            entry_threshold = strategy.get("entry_threshold", 2.0)
            
            # Enhance buy signals when price is near lower band
            buy_mask = (signals == "BUY") & (data["bb_pos"] > 0.8)
            signals.loc[buy_mask] = "HOLD"  # Filter out buys at upper bands
            
            # Enhance sell signals when price is near upper band
            sell_mask = (signals == "SELL") & (data["bb_pos"] < 0.2)
            signals.loc[sell_mask] = "HOLD"  # Filter out sells at lower bands
    
    def _enhance_momentum_signals(
        self,
        signals: pd.Series,
        data: pd.DataFrame,
        strategy: Dict[str, Any]
    ) -> None:
        """
        Enhance signals for trending market regimes.
        
        Args:
            signals: Trading signals to enhance
            data: Market data
            strategy: Strategy parameters
        """
        # Filter signals based on trend characteristics
        if "rsi" in data.columns:  # RSI indicator
            # Entry threshold from strategy
            entry_threshold = strategy.get("entry_threshold", 0.6)
            
            # For uptrends, avoid buying when RSI is already high
            if strategy.get("regime", "") == "trending_up":
                buy_mask = (signals == "BUY") & (data["rsi"] > 70)
                signals.loc[buy_mask] = "HOLD"  # Filter out buys at high RSI
            
            # For downtrends, avoid selling when RSI is already low
            elif strategy.get("regime", "") == "trending_down":
                sell_mask = (signals == "SELL") & (data["rsi"] < 30)
                signals.loc[sell_mask] = "HOLD"  # Filter out sells at low RSI
    
    def _reduce_signal_frequency(
        self,
        signals: pd.Series,
        strategy: Dict[str, Any]
    ) -> None:
        """
        Reduce trading frequency in high volatility regimes.
        
        Args:
            signals: Trading signals to enhance
            strategy: Strategy parameters
        """
        # Get position size modifier (lower = more conservative)
        modifier = strategy.get("position_size_modifier", 0.5)
        
        # Randomly filter out some signals based on modifier
        # Lower modifier = more signals filtered out
        np.random.seed(42)  # For reproducibility
        
        # Generate random numbers for each signal
        random_vals = np.random.random(len(signals))
        
        # Filter out signals with probability proportional to position size reduction
        filter_mask = random_vals > modifier
        signals.loc[filter_mask & ((signals == "BUY") | (signals == "SELL"))] = "HOLD"
    
    def calculate_position_size(
        self,
        symbol: str,
        base_position_size: float,
        price: float,
        stop_loss: Optional[float] = None
    ) -> float:
        """
        Calculate ML-adjusted position size.
        
        Args:
            symbol: Trading symbol
            base_position_size: Original position size from risk manager
            price: Current price
            stop_loss: Stop loss price
            
        Returns:
            Adjusted position size
        """
        # Get strategy adaptations if available
        strategy = self.strategy_adaptations.get(symbol, {})
        
        # If no adaptations available, return original size
        if not strategy:
            return base_position_size
        
        # Apply position size modifier
        modifier = strategy.get("position_size_modifier", 1.0)
        adjusted_size = base_position_size * modifier
        
        # Apply stop loss adjustments if available
        if stop_loss is not None and price > 0:
            # Get stop loss multiplier from strategy
            sl_multiplier = strategy.get("stop_loss_multiplier", 2.0)
            
            # Calculate original risk per share
            original_risk = abs(price - stop_loss)
            
            # Adjust stop distance based on multiplier
            adjusted_risk = original_risk * sl_multiplier
            
            # Calculate position size based on adjusted risk
            # (inversely proportional to risk)
            if adjusted_risk > 0 and original_risk > 0:
                risk_ratio = original_risk / adjusted_risk
                adjusted_size = adjusted_size * risk_ratio
        
        self.logger.info(
            f"Adjusted position size for {symbol}: {base_position_size:.2f} -> {adjusted_size:.2f} "
            f"({modifier:.2f}x modifier)"
        )
        
        return adjusted_size


# For testing
def create_sample_data():
    """Create sample data for testing."""
    # Create date range
    dates = pd.date_range(start="2022-01-01", periods=100, freq="D")
    
    # Create sample price data
    np.random.seed(42)
    close = np.random.normal(100, 5, 100).cumsum()
    
    # Create OHLCV data
    data = pd.DataFrame({
        "open": close + np.random.normal(0, 1, 100),
        "high": close + abs(np.random.normal(0, 2, 100)),
        "low": close - abs(np.random.normal(0, 2, 100)),
        "close": close,
        "volume": np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # Create sample signals
    signals = pd.Series(["HOLD"] * 100, index=dates)
    signals[20:25] = "BUY"
    signals[50:55] = "SELL"
    signals[80:85] = "BUY"
    
    return data, signals


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create AI instance
    ai = TradingAI()
    
    # Create sample data
    data, signals = create_sample_data()
    
    # Create mock functions for testing
    def mock_regime_predict(data):
        """Mock regime prediction function."""
        return {
            "regime": "trending_up",
            "confidence": 0.85,
            "probabilities": {
                "trending_up": 0.85,
                "trending_down": 0.05,
                "mean_reverting": 0.07,
                "high_volatility": 0.03
            }
        }
    
    def mock_get_strategy(prediction):
        """Mock strategy function."""
        return {
            "strategy_type": "momentum",
            "position_size_modifier": 1.2,
            "stop_loss_multiplier": 1.5,
            "entry_threshold": 0.7
        }
    
    # Mock regime detector methods for testing
    ai.regime_detector = type('obj', (object,), {
        'predict': mock_regime_predict,
        'get_regime_strategy': mock_get_strategy
    })
    
    # Test regime detection
    print("\nTesting regime detection...")
    regime = ai.detect_market_regime("SPY", data)
    print(f"Detected regime: {regime['regime']} (confidence: {regime['confidence']:.2f})")
    
    # Test strategy adaptation
    print("\nTesting strategy adaptation...")
    strategy = ai.adapt_strategy("SPY", regime)
    print(f"Adapted strategy: {strategy['strategy_type']}")
    print(f"Position size modifier: {strategy['position_size_modifier']:.2f}x")
    
    # Test signal enhancement
    print("\nTesting signal enhancement...")
    enhanced_signals = ai.enhance_signals("SPY", data, signals)
    changes = (enhanced_signals != signals).sum()
    print(f"Enhanced {changes} signals")
    
    # Test position sizing
    print("\nTesting position sizing...")
    base_position = 1000
    adjusted_position = ai.calculate_position_size("SPY", base_position, 100, 95)
    print(f"Adjusted position size: ${base_position:.2f} -> ${adjusted_position:.2f}") 