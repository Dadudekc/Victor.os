"""
Drift detection system for monitoring agent behavior patterns and predicting compliance issues.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np


class DriftDetector:
    """Detects behavioral drift and predicts potential compliance issues."""

    def __init__(self, window_size: int = 100, threshold: float = 0.1):
        self.window_size = (
            window_size  # Number of actions to consider for drift detection
        )
        self.threshold = threshold  # Threshold for drift detection
        self.action_history: Dict[str, List[Tuple[datetime, str, float]]] = defaultdict(
            list
        )
        self.violation_patterns: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

    def add_action(
        self, agent_id: str, action_type: str, compliance_score: float
    ) -> Optional[Dict]:
        """
        Add a new action and check for drift.

        Args:
            agent_id: ID of the agent
            action_type: Type of action performed
            compliance_score: Score indicating compliance (0-1)

        Returns:
            Optional drift warning if detected
        """
        timestamp = datetime.now()
        self.action_history[agent_id].append((timestamp, action_type, compliance_score))

        # Keep only recent actions
        cutoff = timestamp - timedelta(hours=24)
        self.action_history[agent_id] = [
            (t, a, s) for t, a, s in self.action_history[agent_id] if t > cutoff
        ]

        # Check for immediate non-compliance
        if compliance_score < 0.5:
            return {
                "type": "drift_warning",
                "agent_id": agent_id,
                "severity": "medium",
                "metrics": {
                    "compliance_score": compliance_score,
                    "action_type": action_type,
                },
                "recommendation": "Non-compliant action detected. Monitor agent behavior.",
            }

        # Check for drift in history
        return self._check_drift(agent_id)

    def add_violation(self, agent_id: str, violation_type: str) -> Optional[Dict]:
        """
        Record a violation and check for patterns.

        Args:
            agent_id: ID of the agent
            violation_type: Type of violation

        Returns:
            Optional pattern warning if detected
        """
        self.violation_patterns[agent_id].append((violation_type, datetime.now()))

        # Keep only recent violations
        cutoff = datetime.now() - timedelta(hours=24)
        self.violation_patterns[agent_id] = [
            (v, t) for v, t in self.violation_patterns[agent_id] if t > cutoff
        ]

        return self._check_violation_patterns(agent_id)

    def _check_drift(self, agent_id: str) -> Optional[Dict]:
        """Check for behavioral drift in recent actions."""
        if len(self.action_history[agent_id]) < self.window_size:
            return None

        recent_actions = self.action_history[agent_id][-self.window_size :]
        scores = [s for _, _, s in recent_actions]

        # Calculate drift metrics
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        trend = np.polyfit(range(len(scores)), scores, 1)[0]

        # Check for significant drift
        if trend < -self.threshold or std_score > self.threshold:
            return {
                "type": "drift_warning",
                "agent_id": agent_id,
                "severity": "high" if trend < -self.threshold * 2 else "medium",
                "metrics": {
                    "mean_compliance": mean_score,
                    "compliance_std": std_score,
                    "trend": trend,
                },
                "recommendation": self._generate_drift_recommendation(trend, std_score),
            }

        return None

    def _check_violation_patterns(self, agent_id: str) -> Optional[Dict]:
        """Check for patterns in violations."""
        if len(self.violation_patterns[agent_id]) < 3:
            return None

        recent_violations = self.violation_patterns[agent_id][-10:]
        violation_counts = defaultdict(int)

        for violation_type, _ in recent_violations:
            violation_counts[violation_type] += 1

        # Check for repeated violations
        for violation_type, count in violation_counts.items():
            if count >= 3:  # Same violation type 3+ times
                return {
                    "type": "pattern_warning",
                    "agent_id": agent_id,
                    "severity": "high",
                    "violation_type": violation_type,
                    "count": count,
                    "recommendation": f"Agent has repeated {violation_type} violation {count} times. Consider intervention.",
                }

        return None

    def _generate_drift_recommendation(self, trend: float, std: float) -> str:
        """Generate recommendation based on drift metrics."""
        if trend < -self.threshold * 2:
            return (
                "Severe compliance drift detected. Immediate intervention recommended."
            )
        elif trend < -self.threshold:
            return "Moderate compliance drift detected. Monitor closely."
        elif std > self.threshold:
            return (
                "High variance in compliance scores. Consider reviewing recent actions."
            )
        return "No significant drift detected."

    def get_agent_metrics(self, agent_id: str) -> Dict:
        """Get current metrics for an agent."""
        if not self.action_history[agent_id]:
            return {"compliance_rate": 0.0, "drift_score": 0.0, "violation_count": 0}

        recent_actions = self.action_history[agent_id][-self.window_size :]
        scores = [s for _, _, s in recent_actions]

        return {
            "compliance_rate": np.mean(scores),
            "drift_score": abs(np.polyfit(range(len(scores)), scores, 1)[0]),
            "violation_count": len(self.violation_patterns[agent_id]),
        }

    def predict_compliance(self, agent_id: str, horizon: int = 10) -> Dict:
        """
        Predict future compliance based on current trends.

        Args:
            agent_id: ID of the agent
            horizon: Number of future actions to predict

        Returns:
            Dictionary with prediction metrics
        """
        if not self.action_history[agent_id]:
            return {
                "predicted_compliance": 0.5,  # Default to neutral
                "confidence": 0.0,
                "warning": "No historical data available",
            }

        recent_actions = self.action_history[agent_id][
            -min(self.window_size, len(self.action_history[agent_id])) :
        ]
        scores = [s for _, _, s in recent_actions]

        # Fit trend line
        x = np.array(range(len(scores)))
        y = np.array(scores)
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)

        # Predict future values
        future_x = np.array(range(len(scores), len(scores) + horizon))
        predicted = p(future_x)

        # Calculate confidence based on recent variance
        std = np.std(scores)
        confidence = 1.0 - min(std, 1.0)

        return {
            "predicted_compliance": float(predicted[-1]),
            "confidence": float(confidence),
            "trend": float(z[0]),
            "warning": (
                "High risk of compliance drop" if z[0] < -self.threshold else None
            ),
        }
