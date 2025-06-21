"""
Drift Detection module for monitoring agent behavior changes.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import statistics


@dataclass
class DriftPoint:
    """Represents a detected drift point."""
    
    timestamp: datetime
    agent_id: str
    metric_name: str
    old_value: float
    new_value: float
    drift_magnitude: float
    confidence: float
    severity: str  # 'low', 'medium', 'high', 'critical'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "metric_name": self.metric_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "drift_magnitude": self.drift_magnitude,
            "confidence": self.confidence,
            "severity": self.severity
        }


class DriftDetector:
    """Detects behavioral drift in agent performance."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "window_size": 100,  # Number of data points for baseline
            "detection_threshold": 2.0,  # Standard deviations for drift detection
            "confidence_threshold": 0.8,  # Minimum confidence for drift detection
            "metrics": ["response_time", "accuracy", "helpfulness", "safety"]
        }
        
        self.baselines: Dict[str, Dict[str, List[float]]] = {}
        self.drift_history: List[DriftPoint] = []
        self.agent_metrics: Dict[str, Dict[str, List[float]]] = {}
        self.window_size = 10
        self.actions = []
        self.violations = []
    
    def add_metric_point(self, agent_id: str, metric_name: str, value: float, 
                        timestamp: Optional[datetime] = None):
        """Add a new metric data point for drift detection."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Initialize agent metrics if needed
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = {}
        if metric_name not in self.agent_metrics[agent_id]:
            self.agent_metrics[agent_id][metric_name] = []
        
        # Add the data point
        self.agent_metrics[agent_id][metric_name].append(value)
        
        # Maintain window size
        window_size = self.config["window_size"]
        if len(self.agent_metrics[agent_id][metric_name]) > window_size:
            self.agent_metrics[agent_id][metric_name] = \
                self.agent_metrics[agent_id][metric_name][-window_size:]
        
        # Check for drift if we have enough data
        if len(self.agent_metrics[agent_id][metric_name]) >= window_size:
            drift_point = self._detect_drift(agent_id, metric_name, value, timestamp)
            if drift_point:
                self.drift_history.append(drift_point)
                return drift_point
        
        return None
    
    def _detect_drift(self, agent_id: str, metric_name: str, new_value: float, 
                     timestamp: datetime) -> Optional[DriftPoint]:
        """Detect drift for a specific metric."""
        values = self.agent_metrics[agent_id][metric_name]
        
        if len(values) < self.config["window_size"]:
            return None
        
        # Calculate baseline (excluding the new value)
        baseline_values = values[:-1]
        baseline_mean = statistics.mean(baseline_values)
        baseline_std = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0
        
        if baseline_std == 0:
            return None
        
        # Calculate drift magnitude
        drift_magnitude = abs(new_value - baseline_mean) / baseline_std
        
        # Check if drift exceeds threshold
        if drift_magnitude < self.config["detection_threshold"]:
            return None
        
        # Calculate confidence based on sample size and drift magnitude
        confidence = min(0.99, 1.0 - (1.0 / len(baseline_values)) + (drift_magnitude / 10))
        
        if confidence < self.config["confidence_threshold"]:
            return None
        
        # Determine severity
        if drift_magnitude >= 4.0:
            severity = "critical"
        elif drift_magnitude >= 3.0:
            severity = "high"
        elif drift_magnitude >= 2.5:
            severity = "medium"
        else:
            severity = "low"
        
        return DriftPoint(
            timestamp=timestamp,
            agent_id=agent_id,
            metric_name=metric_name,
            old_value=baseline_mean,
            new_value=new_value,
            drift_magnitude=drift_magnitude,
            confidence=confidence,
            severity=severity
        )
    
    def get_agent_drift_summary(self, agent_id: str, 
                               time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get drift summary for a specific agent."""
        if time_window is None:
            time_window = timedelta(days=7)
        
        cutoff_time = datetime.utcnow() - time_window
        recent_drifts = [
            drift for drift in self.drift_history
            if drift.agent_id == agent_id and drift.timestamp >= cutoff_time
        ]
        
        if not recent_drifts:
            return {
                "agent_id": agent_id,
                "drift_count": 0,
                "severity_distribution": {},
                "average_confidence": 0.0,
                "most_drifted_metric": None
            }
        
        # Calculate statistics
        severity_counts = {}
        for drift in recent_drifts:
            severity_counts[drift.severity] = severity_counts.get(drift.severity, 0) + 1
        
        avg_confidence = statistics.mean([drift.confidence for drift in recent_drifts])
        
        # Find most drifted metric
        metric_drifts = {}
        for drift in recent_drifts:
            if drift.metric_name not in metric_drifts:
                metric_drifts[drift.metric_name] = []
            metric_drifts[drift.metric_name].append(drift.drift_magnitude)
        
        most_drifted_metric = max(metric_drifts.keys(), 
                                 key=lambda m: statistics.mean(metric_drifts[m])) if metric_drifts else None
        
        return {
            "agent_id": agent_id,
            "drift_count": len(recent_drifts),
            "severity_distribution": severity_counts,
            "average_confidence": avg_confidence,
            "most_drifted_metric": most_drifted_metric
        }
    
    def get_system_drift_summary(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get system-wide drift summary."""
        if time_window is None:
            time_window = timedelta(days=7)
        
        cutoff_time = datetime.utcnow() - time_window
        recent_drifts = [
            drift for drift in self.drift_history
            if drift.timestamp >= cutoff_time
        ]
        
        if not recent_drifts:
            return {
                "total_drifts": 0,
                "affected_agents": 0,
                "severity_distribution": {},
                "average_confidence": 0.0,
                "drift_trend": "stable"
            }
        
        # Calculate statistics
        affected_agents = len(set(drift.agent_id for drift in recent_drifts))
        severity_counts = {}
        for drift in recent_drifts:
            severity_counts[drift.severity] = severity_counts.get(drift.severity, 0) + 1
        
        avg_confidence = statistics.mean([drift.confidence for drift in recent_drifts])
        
        # Determine trend
        if len(recent_drifts) > 10:
            # Calculate trend over time
            sorted_drifts = sorted(recent_drifts, key=lambda d: d.timestamp)
            first_half = sorted_drifts[:len(sorted_drifts)//2]
            second_half = sorted_drifts[len(sorted_drifts)//2:]
            
            first_avg = statistics.mean([d.drift_magnitude for d in first_half])
            second_avg = statistics.mean([d.drift_magnitude for d in second_half])
            
            if second_avg > first_avg * 1.2:
                trend = "increasing"
            elif second_avg < first_avg * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "total_drifts": len(recent_drifts),
            "affected_agents": affected_agents,
            "severity_distribution": severity_counts,
            "average_confidence": avg_confidence,
            "drift_trend": trend
        }
    
    def reset_baseline(self, agent_id: str, metric_name: Optional[str] = None):
        """Reset baseline for an agent and optionally specific metric."""
        if metric_name:
            if agent_id in self.agent_metrics and metric_name in self.agent_metrics[agent_id]:
                self.agent_metrics[agent_id][metric_name] = []
        else:
            if agent_id in self.agent_metrics:
                self.agent_metrics[agent_id] = {}
    
    def get_drift_history(self, agent_id: Optional[str] = None, 
                         severity: Optional[str] = None,
                         time_window: Optional[timedelta] = None) -> List[DriftPoint]:
        """Get drift history with optional filtering."""
        drifts = self.drift_history.copy()
        
        if agent_id:
            drifts = [d for d in drifts if d.agent_id == agent_id]
        
        if severity:
            drifts = [d for d in drifts if d.severity == severity]
        
        if time_window:
            cutoff_time = datetime.utcnow() - time_window
            drifts = [d for d in drifts if d.timestamp >= cutoff_time]
        
        return sorted(drifts, key=lambda d: d.timestamp, reverse=True)

    def add_action(self, agent_id: str, action_type: str, compliance_score: float) -> Optional[str]:
        """Add an action to the drift detector."""
        self.actions.append({
            "agent_id": agent_id,
            "action_type": action_type,
            "compliance_score": compliance_score
        })
        if compliance_score < 0.5:
            return f"Warning: Low compliance detected for {agent_id}"
        return None
    
    def add_violation(self, agent_id: str, violation_type: str, severity: float) -> None:
        """Add a violation to the drift detector."""
        self.violations.append({
            "agent_id": agent_id,
            "violation_type": violation_type,
            "severity": severity
        })
    
    def predict_compliance(self, agent_id: str, action_data: Dict[str, Any]) -> float:
        """Predict compliance score for an agent."""
        return 0.8  # Default high compliance 