"""
Victor.os Machine Learning Agent Optimization System
Phase 3: Intelligence Enhancement - ML for agent optimization and predictive analytics
"""

import asyncio
import json
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import structlog
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
logger = structlog.get_logger("ml_optimizer")

class OptimizationTarget(Enum):
    """Optimization targets for agent performance"""
    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    RESOURCE_USAGE = "resource_usage"
    USER_SATISFACTION = "user_satisfaction"
    TASK_COMPLETION = "task_completion"
    ERROR_RATE = "error_rate"

class ModelType(Enum):
    """Machine learning model types"""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LINEAR_REGRESSION = "linear_regression"
    NEURAL_NETWORK = "neural_network"

@dataclass
class AgentMetrics:
    """Agent performance metrics for ML training"""
    agent_id: str
    timestamp: float
    response_time: float
    success_rate: float
    cpu_usage: float
    memory_usage: float
    user_satisfaction: float
    task_completion_rate: float
    error_rate: float
    interaction_count: int
    context_length: int
    model_parameters: Dict[str, Any]

@dataclass
class OptimizationResult:
    """Result of agent optimization"""
    agent_id: str
    optimization_target: OptimizationTarget
    original_value: float
    optimized_value: float
    improvement_percentage: float
    recommended_parameters: Dict[str, Any]
    confidence_score: float
    model_used: str

class MLOptimizer:
    """Machine learning optimizer for agent performance enhancement"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.metrics_history: List[AgentMetrics] = []
        self.optimization_history: List[OptimizationResult] = []
        
        # Setup model storage
        self.model_dir = Path("models")
        self.model_dir.mkdir(exist_ok=True)
        
        # Initialize models
        self._initialize_models()
        
        # Start background optimization
        self._start_background_optimization()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for ML optimizer"""
        return {
            "optimization_interval": 3600,  # 1 hour
            "min_data_points": 100,
            "model_retrain_interval": 86400,  # 24 hours
            "prediction_confidence_threshold": 0.7,
            "optimization_targets": [
                OptimizationTarget.RESPONSE_TIME,
                OptimizationTarget.SUCCESS_RATE,
                OptimizationTarget.RESOURCE_USAGE,
            ],
            "model_types": {
                OptimizationTarget.RESPONSE_TIME: ModelType.GRADIENT_BOOSTING,
                OptimizationTarget.SUCCESS_RATE: ModelType.RANDOM_FOREST,
                OptimizationTarget.RESOURCE_USAGE: ModelType.LINEAR_REGRESSION,
            },
            "feature_importance_threshold": 0.1,
            "auto_optimization": True,
            "cross_validation_folds": 5,
        }
    
    def _initialize_models(self):
        """Initialize ML models for each optimization target"""
        for target in self.config["optimization_targets"]:
            model_type = self.config["model_types"].get(target, ModelType.RANDOM_FOREST)
            self.models[target.value] = self._create_model(model_type)
            self.scalers[target.value] = StandardScaler()
    
    def _create_model(self, model_type: ModelType) -> Any:
        """Create ML model based on type"""
        if model_type == ModelType.RANDOM_FOREST:
            return RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif model_type == ModelType.GRADIENT_BOOSTING:
            return GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        elif model_type == ModelType.LINEAR_REGRESSION:
            return LinearRegression()
        else:
            return RandomForestRegressor(n_estimators=100, random_state=42)
    
    def _start_background_optimization(self):
        """Start background optimization loop"""
        if self.config["auto_optimization"]:
            asyncio.create_task(self._optimization_loop())
    
    async def collect_metrics(self, metrics: AgentMetrics):
        """Collect agent metrics for ML training"""
        try:
            self.metrics_history.append(metrics)
            
            # Keep only recent data to prevent memory bloat
            max_history = self.config["min_data_points"] * 10
            if len(self.metrics_history) > max_history:
                self.metrics_history = self.metrics_history[-max_history:]
            
            logger.info("Metrics collected", 
                       agent_id=metrics.agent_id, 
                       metrics_count=len(self.metrics_history))
            
        except Exception as e:
            logger.error("Failed to collect metrics", 
                        agent_id=metrics.agent_id, 
                        error=str(e))
    
    async def optimize_agent(self, agent_id: str, target: OptimizationTarget) -> Optional[OptimizationResult]:
        """Optimize agent performance for specific target"""
        try:
            # Check if we have enough data
            if len(self.metrics_history) < self.config["min_data_points"]:
                logger.warning("Insufficient data for optimization", 
                              data_points=len(self.metrics_history),
                              required=self.config["min_data_points"])
                return None
            
            # Prepare training data
            X, y = self._prepare_training_data(target)
            
            if len(X) < self.config["min_data_points"]:
                logger.warning("Insufficient data after filtering", 
                              data_points=len(X),
                              required=self.config["min_data_points"])
                return None
            
            # Train model
            model = self.models[target.value]
            scaler = self.scalers[target.value]
            
            # Scale features
            X_scaled = scaler.fit_transform(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )
            
            # Train model
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            logger.info("Model trained", 
                       target=target.value, 
                       mse=mse, 
                       r2=r2)
            
            # Get current agent metrics
            current_metrics = self._get_current_agent_metrics(agent_id)
            if not current_metrics:
                logger.warning("No current metrics for agent", agent_id=agent_id)
                return None
            
            # Prepare current features
            current_features = self._extract_features(current_metrics)
            current_features_scaled = scaler.transform([current_features])
            
            # Predict optimal parameters
            optimal_prediction = model.predict(current_features_scaled)[0]
            
            # Generate optimization result
            original_value = self._get_target_value(current_metrics, target)
            improvement = ((optimal_prediction - original_value) / original_value) * 100
            
            # Generate recommended parameters
            recommended_params = self._generate_recommended_parameters(
                current_metrics, target, optimal_prediction
            )
            
            # Calculate confidence score
            confidence = min(1.0, max(0.0, r2))  # Use R² as confidence
            
            result = OptimizationResult(
                agent_id=agent_id,
                optimization_target=target,
                original_value=original_value,
                optimized_value=optimal_prediction,
                improvement_percentage=improvement,
                recommended_parameters=recommended_params,
                confidence_score=confidence,
                model_used=type(model).__name__
            )
            
            # Store result
            self.optimization_history.append(result)
            
            logger.info("Agent optimization completed", 
                       agent_id=agent_id,
                       target=target.value,
                       improvement=f"{improvement:.2f}%",
                       confidence=f"{confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error("Agent optimization failed", 
                        agent_id=agent_id,
                        target=target.value,
                        error=str(e))
            return None
    
    def _prepare_training_data(self, target: OptimizationTarget) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ML model"""
        features = []
        targets = []
        
        for metrics in self.metrics_history:
            # Extract features
            feature_vector = self._extract_features(metrics)
            features.append(feature_vector)
            
            # Extract target value
            target_value = self._get_target_value(metrics, target)
            targets.append(target_value)
        
        return np.array(features), np.array(targets)
    
    def _extract_features(self, metrics: AgentMetrics) -> List[float]:
        """Extract features from agent metrics"""
        return [
            metrics.cpu_usage,
            metrics.memory_usage,
            metrics.interaction_count,
            metrics.context_length,
            metrics.user_satisfaction,
            metrics.task_completion_rate,
            metrics.error_rate,
            # Add model parameters as features
            metrics.model_parameters.get("temperature", 0.7),
            metrics.model_parameters.get("max_tokens", 1000),
            metrics.model_parameters.get("top_p", 0.9),
        ]
    
    def _get_target_value(self, metrics: AgentMetrics, target: OptimizationTarget) -> float:
        """Get target value from metrics"""
        if target == OptimizationTarget.RESPONSE_TIME:
            return metrics.response_time
        elif target == OptimizationTarget.SUCCESS_RATE:
            return metrics.success_rate
        elif target == OptimizationTarget.RESOURCE_USAGE:
            return (metrics.cpu_usage + metrics.memory_usage) / 2
        elif target == OptimizationTarget.USER_SATISFACTION:
            return metrics.user_satisfaction
        elif target == OptimizationTarget.TASK_COMPLETION:
            return metrics.task_completion_rate
        elif target == OptimizationTarget.ERROR_RATE:
            return metrics.error_rate
        else:
            return 0.0
    
    def _get_current_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        """Get current metrics for specific agent"""
        # Get most recent metrics for agent
        agent_metrics = [m for m in self.metrics_history if m.agent_id == agent_id]
        if agent_metrics:
            return max(agent_metrics, key=lambda x: x.timestamp)
        return None
    
    def _generate_recommended_parameters(self, metrics: AgentMetrics, target: OptimizationTarget, optimal_value: float) -> Dict[str, Any]:
        """Generate recommended parameters based on optimization"""
        current_params = metrics.model_parameters.copy()
        
        if target == OptimizationTarget.RESPONSE_TIME:
            # Optimize for faster response
            if optimal_value < metrics.response_time:
                # Reduce context length and max tokens for faster response
                current_params["max_tokens"] = max(100, int(current_params.get("max_tokens", 1000) * 0.8))
                current_params["temperature"] = min(1.0, current_params.get("temperature", 0.7) * 1.1)
        
        elif target == OptimizationTarget.SUCCESS_RATE:
            # Optimize for higher success rate
            if optimal_value > metrics.success_rate:
                # Increase context length and adjust temperature for better accuracy
                current_params["max_tokens"] = min(2000, int(current_params.get("max_tokens", 1000) * 1.2))
                current_params["temperature"] = max(0.1, current_params.get("temperature", 0.7) * 0.9)
        
        elif target == OptimizationTarget.RESOURCE_USAGE:
            # Optimize for lower resource usage
            if optimal_value < (metrics.cpu_usage + metrics.memory_usage) / 2:
                # Reduce resource-intensive parameters
                current_params["max_tokens"] = max(500, int(current_params.get("max_tokens", 1000) * 0.7))
                current_params["temperature"] = min(1.0, current_params.get("temperature", 0.7) * 1.05)
        
        return current_params
    
    async def get_optimization_insights(self, agent_id: str) -> Dict[str, Any]:
        """Get optimization insights for agent"""
        try:
            agent_optimizations = [o for o in self.optimization_history if o.agent_id == agent_id]
            
            if not agent_optimizations:
                return {"message": "No optimization data available"}
            
            # Calculate average improvements
            improvements = {}
            for target in OptimizationTarget:
                target_optimizations = [o for o in agent_optimizations if o.optimization_target == target]
                if target_optimizations:
                    avg_improvement = sum(o.improvement_percentage for o in target_optimizations) / len(target_optimizations)
                    improvements[target.value] = {
                        "average_improvement": avg_improvement,
                        "optimization_count": len(target_optimizations),
                        "latest_optimization": max(target_optimizations, key=lambda x: x.original_value).__dict__
                    }
            
            # Get feature importance
            feature_importance = self._get_feature_importance()
            
            return {
                "agent_id": agent_id,
                "total_optimizations": len(agent_optimizations),
                "improvements_by_target": improvements,
                "feature_importance": feature_importance,
                "recommendations": self._generate_recommendations(agent_optimizations)
            }
            
        except Exception as e:
            logger.error("Failed to get optimization insights", 
                        agent_id=agent_id,
                        error=str(e))
            return {"error": str(e)}
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from models"""
        importance = {}
        
        for target in self.config["optimization_targets"]:
            model = self.models[target.value]
            if hasattr(model, 'feature_importances_'):
                feature_names = [
                    "cpu_usage", "memory_usage", "interaction_count", "context_length",
                    "user_satisfaction", "task_completion_rate", "error_rate",
                    "temperature", "max_tokens", "top_p"
                ]
                
                for name, importance_val in zip(feature_names, model.feature_importances_):
                    if importance_val > self.config["feature_importance_threshold"]:
                        importance[f"{target.value}_{name}"] = float(importance_val)
        
        return importance
    
    def _generate_recommendations(self, optimizations: List[OptimizationResult]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Analyze patterns in optimizations
        response_time_optimizations = [o for o in optimizations if o.optimization_target == OptimizationTarget.RESPONSE_TIME]
        success_rate_optimizations = [o for o in optimizations if o.optimization_target == OptimizationTarget.SUCCESS_RATE]
        
        if response_time_optimizations:
            avg_improvement = sum(o.improvement_percentage for o in response_time_optimizations) / len(response_time_optimizations)
            if avg_improvement > 10:
                recommendations.append("Consider reducing max_tokens and context_length for faster response times")
        
        if success_rate_optimizations:
            avg_improvement = sum(o.improvement_percentage for o in success_rate_optimizations) / len(success_rate_optimizations)
            if avg_improvement > 5:
                recommendations.append("Consider increasing context_length and adjusting temperature for better accuracy")
        
        return recommendations
    
    async def _optimization_loop(self):
        """Background optimization loop"""
        while True:
            try:
                await self._perform_background_optimization()
                await asyncio.sleep(self.config["optimization_interval"])
            except Exception as e:
                logger.error("Background optimization error", error=str(e))
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _perform_background_optimization(self):
        """Perform background optimization for all agents"""
        # Get unique agent IDs
        agent_ids = list(set(m.agent_id for m in self.metrics_history))
        
        for agent_id in agent_ids:
            for target in self.config["optimization_targets"]:
                try:
                    await self.optimize_agent(agent_id, target)
                except Exception as e:
                    logger.error("Background optimization failed", 
                                agent_id=agent_id,
                                target=target.value,
                                error=str(e))
    
    async def save_models(self):
        """Save trained models to disk"""
        try:
            for target, model in self.models.items():
                model_path = self.model_dir / f"{target}_model.joblib"
                joblib.dump(model, model_path)
                
                # Save scaler
                scaler_path = self.model_dir / f"{target}_scaler.joblib"
                joblib.dump(self.scalers[target], scaler_path)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error("Failed to save models", error=str(e))
    
    async def load_models(self):
        """Load trained models from disk"""
        try:
            for target in self.config["optimization_targets"]:
                model_path = self.model_dir / f"{target.value}_model.joblib"
                scaler_path = self.model_dir / f"{target.value}_scaler.joblib"
                
                if model_path.exists() and scaler_path.exists():
                    self.models[target.value] = joblib.load(model_path)
                    self.scalers[target.value] = joblib.load(scaler_path)
            
            logger.info("Models loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load models", error=str(e))
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get ML optimizer system status"""
        return {
            "total_metrics": len(self.metrics_history),
            "total_optimizations": len(self.optimization_history),
            "models_trained": len(self.models),
            "optimization_targets": [t.value for t in self.config["optimization_targets"]],
            "auto_optimization": self.config["auto_optimization"],
            "min_data_points": self.config["min_data_points"],
            "recent_optimizations": [
                asdict(o) for o in self.optimization_history[-5:]
            ]
        } 