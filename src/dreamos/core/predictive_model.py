"""
Machine learning-based predictive model for drift detection and compliance forecasting.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path
import json

class PredictiveModel:
    """ML-based model for predicting agent behavior and compliance drift."""
    
    def __init__(self, model_dir: str = "models/empathy"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize models
        self.drift_detector = IsolationForest(
            contamination=0.1,
            random_state=42
        )
        self.compliance_predictor = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        
        # Load saved models if they exist
        self._load_models()
        
        # Feature tracking
        self.feature_history: Dict[str, List[Dict[str, float]]] = {}
        self.prediction_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Define base features
        self.base_features = [
            "loop_duration",
            "reflection_gap",
            "task_complexity",
            "violation_frequency",
            "thea_approval_rate",
            "response_time",
            "self_reflection_depth"
        ]
        
    def _load_models(self):
        """Load saved models if they exist."""
        try:
            self.drift_detector = joblib.load(self.model_dir / "drift_detector.joblib")
            self.compliance_predictor = joblib.load(self.model_dir / "compliance_predictor.joblib")
            self.scaler = joblib.load(self.model_dir / "scaler.joblib")
            print("Loaded existing models")
        except:
            print("No existing models found, using fresh instances")
            
    def _save_models(self):
        """Save current models to disk."""
        joblib.dump(self.drift_detector, self.model_dir / "drift_detector.joblib")
        joblib.dump(self.compliance_predictor, self.model_dir / "compliance_predictor.joblib")
        joblib.dump(self.scaler, self.model_dir / "scaler.joblib")
        
    def extract_features(self, agent_id: str, action_data: Dict) -> Dict[str, float]:
        """
        Extract and normalize features from action data.
        
        Args:
            agent_id: ID of the agent
            action_data: Dictionary containing action information
            
        Returns:
            Dictionary of normalized features
        """
        # Extract and normalize base features
        features = {}
        for feature in self.base_features:
            value = action_data.get(feature, 0.0)
            # Normalize to [0,1]
            features[feature] = max(0.0, min(1.0, value))
            
        # Add historical features only if we have enough history
        if agent_id in self.feature_history and len(self.feature_history[agent_id]) >= 5:
            recent_features = self.feature_history[agent_id][-5:]
            for i, hist in enumerate(recent_features, 1):
                for feature in self.base_features:
                    features[f"{feature}_lag_{i}"] = hist.get(feature, 0.0)
                    
        return features
        
    def update_model(self, agent_id: str, action_data: Dict, compliance_score: float):
        """
        Update the model with new action data.
        
        Args:
            agent_id: ID of the agent
            action_data: Dictionary containing action information
            compliance_score: Score indicating compliance (0-1)
        """
        # Extract features
        features = self.extract_features(agent_id, action_data)
        
        # Update feature history
        if agent_id not in self.feature_history:
            self.feature_history[agent_id] = []
        self.feature_history[agent_id].append(features)
        
        # Prepare training data
        X = np.array([list(features.values())])
        y = np.array([compliance_score])
        
        # Update scaler with reset=True for first fit
        if not hasattr(self.scaler, "n_features_in_"):
            self.scaler.fit(X)
        else:
            self.scaler.partial_fit(X)
            
        X_scaled = self.scaler.transform(X)
        
        # Update models
        self.drift_detector.fit(X_scaled)
        self.compliance_predictor.fit(X_scaled, y)
        
        # Save updated models periodically
        if len(self.feature_history[agent_id]) % 100 == 0:
            self._save_models()
            
    def predict_drift(self, agent_id: str, action_data: Dict) -> Dict:
        """
        Predict potential drift in agent behavior.
        
        Args:
            agent_id: ID of the agent
            action_data: Dictionary containing action information
            
        Returns:
            Dictionary containing drift prediction and confidence
        """
        features = self.extract_features(agent_id, action_data)
        X = np.array([list(features.values())])
        
        # Ensure scaler and drift detector are fitted
        if not hasattr(self.scaler, "n_features_in_"):
            self.scaler.fit(X)
        if not hasattr(self.drift_detector, "n_features_in_"):
            self.drift_detector.fit(X)
        X_scaled = self.scaler.transform(X)
        
        # Predict drift score
        drift_score = self.drift_detector.score_samples(X_scaled)[0]
        
        # Predict compliance probability
        try:
            compliance_prob = self.compliance_predictor.predict_proba(X_scaled)[0][1]
        except (IndexError, AttributeError):
            # If model not trained enough, use drift score as proxy
            compliance_prob = 1.0 - abs(drift_score)
        
        # Calculate confidence based on feature stability
        confidence = self._calculate_confidence(agent_id, features)
        
        # Store prediction
        prediction = {
            "timestamp": datetime.now().isoformat(),
            "drift_score": float(drift_score),
            "compliance_probability": float(compliance_prob),
            "confidence": float(confidence),
            "features": features
        }
        
        if agent_id not in self.prediction_history:
            self.prediction_history[agent_id] = []
        self.prediction_history[agent_id].append(prediction)
        
        return {
            "drift_detected": drift_score < -0.5,
            "drift_score": float(drift_score),
            "compliance_probability": float(compliance_prob),
            "confidence": float(confidence),
            "warning": self._generate_warning(drift_score, compliance_prob, confidence)
        }
        
    def _calculate_confidence(self, agent_id: str, current_features: Dict[str, float]) -> float:
        """Calculate prediction confidence based on feature stability."""
        if agent_id not in self.feature_history or len(self.feature_history[agent_id]) < 5:
            return 0.5
            
        recent_features = self.feature_history[agent_id][-5:]
        feature_stability = []
        
        for feature_name in current_features.keys():
            if feature_name.endswith("_lag_1"):
                base_feature = feature_name[:-6]
                values = [f[base_feature] for f in recent_features]
                std = np.std(values)
                mean = np.mean(values)
                if mean != 0:
                    stability = 1.0 - min(std / mean, 1.0)
                    feature_stability.append(stability)
                    
        return np.mean(feature_stability) if feature_stability else 0.5
        
    def _generate_warning(self, drift_score: float, compliance_prob: float, confidence: float) -> Optional[str]:
        """Generate warning message based on predictions."""
        if confidence < 0.5:
            return None
            
        if drift_score < -0.8 and compliance_prob < 0.3:
            return "Critical drift detected with high confidence. Immediate intervention recommended."
        elif drift_score < -0.5 and compliance_prob < 0.5:
            return "Significant drift detected. Monitor closely and prepare for potential intervention."
        elif drift_score < -0.3 and compliance_prob < 0.7:
            return "Moderate drift detected. Consider additional monitoring."
            
        return None
        
    def get_agent_insights(self, agent_id: str) -> Dict:
        """
        Get insights about agent behavior patterns.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Dictionary containing behavioral insights
        """
        if agent_id not in self.prediction_history or len(self.prediction_history[agent_id]) < 5:
            return {
                "drift_trend": 0.0,
                "compliance_trend": 0.0,
                "drift_pattern": "insufficient_data",
                "compliance_pattern": "insufficient_data",
                "recent_confidence": 0.0,
                "prediction_count": 0
            }
            
        predictions = self.prediction_history[agent_id]
        
        # Calculate trends
        drift_trend = np.polyfit(
            range(len(predictions)),
            [p["drift_score"] for p in predictions],
            1
        )[0]
        
        compliance_trend = np.polyfit(
            range(len(predictions)),
            [p["compliance_probability"] for p in predictions],
            1
        )[0]
        
        # Identify patterns
        recent_predictions = predictions[-10:]
        drift_pattern = "stable" if abs(drift_trend) < 0.1 else "improving" if drift_trend > 0 else "degrading"
        compliance_pattern = "stable" if abs(compliance_trend) < 0.1 else "improving" if compliance_trend > 0 else "degrading"
        
        return {
            "drift_trend": float(drift_trend),
            "compliance_trend": float(compliance_trend),
            "drift_pattern": drift_pattern,
            "compliance_pattern": compliance_pattern,
            "recent_confidence": float(np.mean([p["confidence"] for p in recent_predictions])),
            "prediction_count": len(predictions)
        } 