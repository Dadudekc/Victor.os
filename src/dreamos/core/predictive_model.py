"""
Predictive Model for AI-driven predictions and forecasting.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import logging
import json
import pickle
from pathlib import Path

from ..utils.common_utils import get_logger


@dataclass
class PredictionResult:
    """Represents a prediction result."""
    
    value: float
    confidence: float
    timestamp: datetime
    model_version: str
    features_used: List[str]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ModelMetrics:
    """Represents model performance metrics."""
    
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    mse: float
    mae: float
    r2_score: float
    training_date: datetime
    test_date: datetime


class PredictiveModel:
    """Base class for predictive models."""
    
    def __init__(self, model_name: str, model_type: str = "regression"):
        self.model_name = model_name
        self.model_type = model_type
        self.logger = get_logger(f"PredictiveModel_{model_name}")
        
        self.model = None
        self.is_trained = False
        self.feature_names: List[str] = []
        self.model_version = "1.0.0"
        self.last_training_date: Optional[datetime] = None
        self.metrics: Optional[ModelMetrics] = None
        
        # Model configuration
        self.config = {
            "random_state": 42,
            "test_size": 0.2,
            "validation_size": 0.1,
            "cross_validation_folds": 5
        }
    
    def set_config(self, **kwargs):
        """Set model configuration parameters."""
        self.config.update(kwargs)
        self.logger.info(f"Updated model configuration: {kwargs}")
    
    def prepare_features(self, data: Union[pd.DataFrame, np.ndarray, List[Dict]]) -> np.ndarray:
        """Prepare features for training/prediction."""
        if isinstance(data, pd.DataFrame):
            return data.values
        elif isinstance(data, np.ndarray):
            return data
        elif isinstance(data, list):
            # Convert list of dicts to DataFrame then to numpy array
            df = pd.DataFrame(data)
            return df.values
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    
    def train(self, X: Union[pd.DataFrame, np.ndarray, List[Dict]], 
              y: Union[pd.Series, np.ndarray, List], **kwargs) -> bool:
        """Train the model with given features and targets."""
        try:
            X_processed = self.prepare_features(X)
            y_processed = np.array(y) if not isinstance(y, np.ndarray) else y
            
            # Store feature names if DataFrame is provided
            if isinstance(X, pd.DataFrame):
                self.feature_names = list(X.columns)
            
            # Train the model (to be implemented by subclasses)
            success = self._train_model(X_processed, y_processed, **kwargs)
            
            if success:
                self.is_trained = True
                self.last_training_date = datetime.now()
                self.logger.info(f"Model {self.model_name} trained successfully")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            return False
    
    def predict(self, X: Union[pd.DataFrame, np.ndarray, List[Dict]]) -> Optional[np.ndarray]:
        """Make predictions using the trained model."""
        if not self.is_trained:
            self.logger.error("Model is not trained")
            return None
        
        try:
            X_processed = self.prepare_features(X)
            predictions = self._predict_model(X_processed)
            self.logger.debug(f"Made predictions for {len(X_processed)} samples")
            return predictions
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return None
    
    def predict_single(self, features: Dict[str, Any]) -> Optional[PredictionResult]:
        """Make a single prediction with confidence."""
        if not self.is_trained:
            self.logger.error("Model is not trained")
            return None
        
        try:
            # Convert single feature dict to array
            if self.feature_names:
                # Ensure features are in correct order
                feature_array = np.array([[features.get(feature, 0) for feature in self.feature_names]])
            else:
                feature_array = np.array([list(features.values())])
            
            prediction = self.predict(feature_array)
            if prediction is not None:
                # Calculate confidence (simplified - could be more sophisticated)
                confidence = 0.8  # Placeholder
                
                return PredictionResult(
                    value=float(prediction[0]),
                    confidence=confidence,
                    timestamp=datetime.now(),
                    model_version=self.model_version,
                    features_used=list(features.keys()),
                    metadata={"model_name": self.model_name}
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Single prediction failed: {e}")
            return None
    
    def evaluate(self, X_test: Union[pd.DataFrame, np.ndarray, List[Dict]], 
                y_test: Union[pd.Series, np.ndarray, List]) -> Optional[ModelMetrics]:
        """Evaluate model performance."""
        if not self.is_trained:
            self.logger.error("Model is not trained")
            return None
        
        try:
            X_processed = self.prepare_features(X_test)
            y_processed = np.array(y_test) if not isinstance(y_test, np.ndarray) else y_test
            
            predictions = self.predict(X_processed)
            if predictions is None:
                return None
            
            # Calculate metrics
            metrics = self._calculate_metrics(y_processed, predictions)
            self.metrics = metrics
            
            self.logger.info(f"Model evaluation completed: R²={metrics.r2_score:.3f}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Evaluation failed: {e}")
            return None
    
    def save_model(self, file_path: str) -> bool:
        """Save the trained model to file."""
        try:
            model_data = {
                "model_name": self.model_name,
                "model_type": self.model_type,
                "model_version": self.model_version,
                "feature_names": self.feature_names,
                "is_trained": self.is_trained,
                "last_training_date": self.last_training_date.isoformat() if self.last_training_date else None,
                "config": self.config,
                "model": self.model
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.logger.info(f"Model saved to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            return False
    
    def load_model(self, file_path: str) -> bool:
        """Load a trained model from file."""
        try:
            with open(file_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model_name = model_data["model_name"]
            self.model_type = model_data["model_type"]
            self.model_version = model_data["model_version"]
            self.feature_names = model_data["feature_names"]
            self.is_trained = model_data["is_trained"]
            self.config = model_data["config"]
            self.model = model_data["model"]
            
            if model_data["last_training_date"]:
                self.last_training_date = datetime.fromisoformat(model_data["last_training_date"])
            
            self.logger.info(f"Model loaded from {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "model_name": self.model_name,
            "model_type": self.model_type,
            "model_version": self.model_version,
            "is_trained": self.is_trained,
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
            "last_training_date": self.last_training_date.isoformat() if self.last_training_date else None,
            "metrics": self.metrics.__dict__ if self.metrics else None
        }
    
    def _train_model(self, X: np.ndarray, y: np.ndarray, **kwargs) -> bool:
        """Internal method to train the model (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _train_model")
    
    def _predict_model(self, X: np.ndarray) -> np.ndarray:
        """Internal method to make predictions (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement _predict_model")
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> ModelMetrics:
        """Calculate model performance metrics."""
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        mse = mean_squared_error(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # For classification models, calculate additional metrics
        if self.model_type == "classification":
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            accuracy = accuracy_score(y_true, y_pred)
            precision = precision_score(y_true, y_pred, average='weighted')
            recall = recall_score(y_true, y_pred, average='weighted')
            f1 = f1_score(y_true, y_pred, average='weighted')
        else:
            # For regression, use simplified metrics
            accuracy = 1.0 - (mse / np.var(y_true)) if np.var(y_true) > 0 else 0.0
            precision = 1.0 - (mae / np.mean(np.abs(y_true))) if np.mean(np.abs(y_true)) > 0 else 0.0
            recall = r2
            f1 = r2
        
        return ModelMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            mse=mse,
            mae=mae,
            r2_score=r2,
            training_date=self.last_training_date or datetime.now(),
            test_date=datetime.now()
        ) 