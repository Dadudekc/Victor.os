"""
regime_detector.py - Market Regime Detection Model

This module provides a machine learning model that detects market regimes:
- Trending (up or down)
- Mean-reverting
- High-volatility/Uncertain

The model uses price action, volatility, and other technical features to 
classify market conditions and adjust trading strategies accordingly.

Usage:
    from basicbot.ml_models.regime_detector import RegimeDetector
    detector = RegimeDetector()
    detector.train(historical_data)
    regime = detector.predict(current_data)
"""

import os
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple

# ML libraries
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib

# Technical analysis
import talib as ta

# Import BasicBot components
try:
    from basicbot.logger import setup_logging
except ImportError:
    # For standalone testing
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
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


class RegimeDetector:
    """
    Market regime detection model that classifies market conditions.
    
    Regimes:
    - 0: Mean-reverting (range-bound/oscillating)
    - 1: Trending up
    - 2: Trending down
    - 3: High volatility/uncertain
    """
    
    def __init__(
        self,
        model_dir: str = "models",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the regime detector.
        
        Args:
            model_dir: Directory to save/load models
            logger: Logger instance
        """
        self.logger = logger or setup_logging("regime_detector")
        self.model_dir = Path(model_dir)
        self.model = None
        self.scaler = None
        self.feature_names = []
        
        # Ensure model directory exists
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Try to load pre-trained model if it exists
        self._load_model()
        
        self.logger.info("Regime detector initialized")
    
    def _load_model(self) -> bool:
        """
        Load pre-trained model from disk.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        model_path = self.model_dir / "regime_model.joblib"
        scaler_path = self.model_dir / "regime_scaler.joblib"
        
        if model_path.exists() and scaler_path.exists():
            try:
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                
                # Load feature names if available
                feature_path = self.model_dir / "regime_features.txt"
                if feature_path.exists():
                    with open(feature_path, 'r') as f:
                        self.feature_names = [line.strip() for line in f.readlines()]
                
                self.logger.info(f"Loaded pre-trained regime model from {model_path}")
                return True
            except Exception as e:
                self.logger.error(f"Error loading model: {e}")
        
        self.logger.info("No pre-trained regime model found, will need training")
        return False
    
    def _save_model(self):
        """Save the trained model to disk."""
        if self.model is None or self.scaler is None:
            self.logger.warning("Cannot save model: model or scaler not initialized")
            return
        
        try:
            model_path = self.model_dir / "regime_model.joblib"
            scaler_path = self.model_dir / "regime_scaler.joblib"
            
            joblib.dump(self.model, model_path)
            joblib.dump(self.scaler, scaler_path)
            
            # Save feature names
            if self.feature_names:
                feature_path = self.model_dir / "regime_features.txt"
                with open(feature_path, 'w') as f:
                    for feature in self.feature_names:
                        f.write(f"{feature}\n")
            
            self.logger.info(f"Saved regime model to {model_path}")
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features for regime detection.
        
        Args:
            data: DataFrame with OHLCV price data
            
        Returns:
            DataFrame with extracted features
        """
        # Ensure data has required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Copy data to avoid modifying the original
        df = data.copy()
        
        # Basic price features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Volatility features
        df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        df['daily_range'] = (df['high'] - df['low']) / df['close']
        df['norm_atr'] = df['atr'] / df['close']
        
        # Momentum/trend features
        df['sma_20'] = ta.SMA(df['close'].values, timeperiod=20)
        df['sma_50'] = ta.SMA(df['close'].values, timeperiod=50)
        df['sma_ratio'] = df['sma_20'] / df['sma_50']
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)
        df['macd'], df['macd_signal'], df['macd_hist'] = ta.MACD(
            df['close'].values, fastperiod=12, slowperiod=26, signalperiod=9
        )
        
        # Mean reversion features
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = ta.BBANDS(
            df['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2
        )
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_pos'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Rolling statistics
        for window in [5, 10, 20]:
            # Rolling volatility
            df[f'volatility_{window}d'] = df['returns'].rolling(window).std()
            
            # Directional movement
            df[f'returns_{window}d'] = df['close'].pct_change(window)
            
            # Range-bound indicators
            df[f'close_to_ma_{window}d'] = np.abs(df['close'] - ta.SMA(df['close'].values, timeperiod=window)) / df['close']
        
        # Clean up NaNs from calculations
        df = df.dropna()
        
        # Store feature names for later use
        self.feature_names = [col for col in df.columns if col not in required_cols + ['date', 'timestamp']]
        
        return df
    
    def label_regimes(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Auto-label market regimes for training data.
        
        This uses heuristics to label historical data:
        - Trending up: Consistent upward price movement
        - Trending down: Consistent downward price movement
        - Mean-reverting: Oscillating within a range
        - High volatility: Abnormally high volatility
        
        Args:
            data: DataFrame with features
            window: Window size for regime detection
            
        Returns:
            DataFrame with 'regime' column added
        """
        df = data.copy()
        
        # Initialize regime column
        df['regime'] = np.nan
        
        # Trend detection parameters
        trend_threshold = 0.8  # % of time moving in same direction
        volatility_z_threshold = 1.5  # Standard deviations above mean volatility
        
        # Calculate directional consistency
        df['up_days'] = (df['returns'] > 0).rolling(window).sum() / window
        df['down_days'] = (df['returns'] < 0).rolling(window).sum() / window
        
        # Calculate volatility Z-score
        vol_mean = df['volatility_20d'].rolling(252).mean()
        vol_std = df['volatility_20d'].rolling(252).std()
        df['vol_z'] = (df['volatility_20d'] - vol_mean) / vol_std
        
        # Mean reversion indicator
        df['range_bound'] = (
            (df['close_to_ma_20d'] < df['close_to_ma_20d'].rolling(252).mean()) & 
            (df['bb_width'] < df['bb_width'].rolling(252).mean())
        )
        
        # Assign regimes based on rules
        for i in range(window, len(df)):
            if df.loc[i, 'vol_z'] > volatility_z_threshold:
                # High volatility regime
                df.loc[i, 'regime'] = 3
            elif df.loc[i, 'up_days'] > trend_threshold:
                # Trending up regime
                df.loc[i, 'regime'] = 1
            elif df.loc[i, 'down_days'] > trend_threshold:
                # Trending down regime
                df.loc[i, 'regime'] = 2
            elif df.loc[i, 'range_bound']:
                # Mean reverting regime
                df.loc[i, 'regime'] = 0
            else:
                # Default to uncertain/mixed regime
                df.loc[i, 'regime'] = 3
        
        # Convert to integer
        df['regime'] = df['regime'].astype('int')
        
        # Drop intermediate columns used for labeling
        df = df.drop(['up_days', 'down_days', 'vol_z', 'range_bound'], axis=1)
        
        return df
    
    def prepare_training_data(
        self, 
        data: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepare data for training regime model.
        
        Args:
            data: DataFrame with features and regime labels
            
        Returns:
            Tuple of (X, y, feature_names)
        """
        # Extract features and target
        X = data[self.feature_names].values
        y = data['regime'].values
        
        # Initialize and fit scaler
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        self.logger.info(f"Prepared training data: {X_scaled.shape[0]} samples, {X_scaled.shape[1]} features")
        
        return X_scaled, y, self.feature_names
    
    def train(
        self, 
        data: pd.DataFrame,
        optimize: bool = True,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train the regime detection model.
        
        Args:
            data: DataFrame with OHLCV data
            optimize: Whether to perform hyperparameter optimization
            test_size: Proportion of data to use for testing
            
        Returns:
            Dictionary with training metrics
        """
        # Extract features
        self.logger.info("Extracting features for regime detection")
        features_df = self.extract_features(data)
        
        # Label regimes
        self.logger.info("Labeling market regimes")
        labeled_df = self.label_regimes(features_df)
        
        # Prepare training data
        X, y, feature_names = self.prepare_training_data(labeled_df)
        
        # Split into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        if optimize:
            # Hyperparameter optimization
            self.logger.info("Performing hyperparameter optimization")
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
            
            grid_search = GridSearchCV(
                RandomForestClassifier(random_state=42),
                param_grid=param_grid,
                cv=5,
                scoring='accuracy',
                n_jobs=-1
            )
            
            grid_search.fit(X_train, y_train)
            self.model = grid_search.best_estimator_
            
            self.logger.info(f"Best parameters: {grid_search.best_params_}")
        else:
            # Train with default parameters
            self.logger.info("Training regime detection model with default parameters")
            self.model = RandomForestClassifier(
                n_estimators=200,
                random_state=42
            )
            self.model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Calculate feature importance
        importance = self.model.feature_importances_
        feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        # Log results
        self.logger.info(f"Model training complete. Accuracy: {accuracy:.4f}")
        self.logger.info(f"Top 5 important features: {feature_importance['feature'].head(5).tolist()}")
        
        # Save the model
        self._save_model()
        
        # Return metrics
        metrics = {
            'accuracy': accuracy,
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'feature_importance': feature_importance.to_dict('records')
        }
        
        return metrics
    
    def predict(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict market regime from price data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with regime prediction and confidence
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Extract features
        features_df = self.extract_features(data)
        
        # Get feature values
        X = features_df[self.feature_names].values
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Make prediction
        regime_proba = self.model.predict_proba(X_scaled)
        regime_id = self.model.predict(X_scaled)[0]
        
        # Map regime ID to name
        regime_names = {
            0: "mean_reverting",
            1: "trending_up",
            2: "trending_down",
            3: "high_volatility"
        }
        
        regime_name = regime_names.get(regime_id, "unknown")
        confidence = regime_proba[0][regime_id]
        
        # Get all probabilities as dict
        probabilities = {
            regime_names[i]: prob 
            for i, prob in enumerate(regime_proba[0])
        }
        
        return {
            "regime_id": int(regime_id),
            "regime": regime_name,
            "confidence": float(confidence),
            "probabilities": probabilities,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_regime_strategy(self, regime_prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get recommended strategy parameters based on detected regime.
        
        Args:
            regime_prediction: Regime prediction from predict()
            
        Returns:
            Dictionary with strategy parameters
        """
        regime = regime_prediction["regime"]
        confidence = regime_prediction["confidence"]
        
        # Base strategy parameters
        strategy = {
            "position_size_modifier": 1.0,
            "stop_loss_multiplier": 2.0,
            "take_profit_multiplier": 3.0,
            "entry_threshold": 0.7
        }
        
        # Adjust based on regime
        if regime == "trending_up":
            strategy.update({
                "strategy_type": "momentum",
                "lookback_period": 20,
                "entry_threshold": 0.6,
                "stop_loss_multiplier": 2.5,
                "take_profit_multiplier": 4.0
            })
        
        elif regime == "trending_down":
            strategy.update({
                "strategy_type": "momentum",
                "lookback_period": 20,
                "entry_threshold": 0.6,
                "stop_loss_multiplier": 2.0,
                "take_profit_multiplier": 3.0,
                "allow_shorts": True
            })
        
        elif regime == "mean_reverting":
            strategy.update({
                "strategy_type": "mean_reversion",
                "lookback_period": 5,
                "entry_threshold": 2.0,
                "stop_loss_multiplier": 1.5,
                "take_profit_multiplier": 2.0
            })
        
        elif regime == "high_volatility":
            strategy.update({
                "strategy_type": "neutral",
                "position_size_modifier": 0.5,  # Reduce position size
                "stop_loss_multiplier": 1.5,    # Tighter stops
                "take_profit_multiplier": 2.0,
                "trade_frequency": "low"
            })
        
        # Adjust based on confidence
        if confidence < 0.6:
            # Lower conviction, reduce risk
            strategy["position_size_modifier"] *= 0.8
            strategy["entry_threshold"] *= 1.2  # Require stronger signals
        
        return strategy


# For testing
def download_sample_data():
    """Download sample data for testing."""
    try:
        import yfinance as yf
        print("Downloading sample data for SPY...")
        data = yf.download("SPY", start="2019-01-01", end="2023-01-01")
        data.columns = [col.lower() for col in data.columns]
        return data
    except Exception as e:
        print(f"Error downloading data: {e}")
        return None


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Download sample data
    data = download_sample_data()
    
    if data is not None:
        # Create regime detector
        detector = RegimeDetector(model_dir="./models")
        
        # Train the model
        print("\nTraining regime detection model...")
        metrics = detector.train(data, optimize=True)
        
        print(f"\nTraining accuracy: {metrics['accuracy']:.4f}")
        
        # Get recent data for prediction
        recent_data = data.tail(50)
        
        # Predict current regime
        print("\nPredicting current market regime...")
        prediction = detector.predict(recent_data)
        
        print(f"Detected regime: {prediction['regime']} (confidence: {prediction['confidence']:.2f})")
        
        # Get strategy recommendations
        strategy = detector.get_regime_strategy(prediction)
        
        print("\nRecommended strategy parameters:")
        for param, value in strategy.items():
            print(f"- {param}: {value}")
    else:
        print("Failed to download sample data. Please ensure you have internet connection and yfinance installed.") 