"""
Ethos Validation Script for Dream.OS

This script performs regular audits of system behavior against the defined ethos,
checking for drift and ensuring continued alignment with core values and principles.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd
from dataclasses import dataclass

from .logger import EmpathyLogger
from .compliance import (
    ValueCompliance,
    PrincipleCompliance,
    SafeguardCompliance
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationMetrics:
    """Metrics for ethos validation."""
    total_actions: int
    compliant_actions: int
    warning_actions: int
    non_compliant_actions: int
    drift_score: float  # 0-1 scale, higher means more drift
    emotional_trends: Dict[str, Any]
    action_statistics: Dict[str, Any]

class EthosValidator:
    """Validates system behavior against ethos guidelines."""
    
    def __init__(self):
        self.ethos_path = Path(__file__).parent.parent / "ethos.json"
        self.logs_path = Path(__file__).parent.parent / "logs"
        self.ethos = self._load_ethos()
        self.logger = EmpathyLogger()
        
        # Initialize compliance checkers
        self.value_checker = ValueCompliance(self.ethos)
        self.principle_checker = PrincipleCompliance(self.ethos)
        self.safeguard_checker = SafeguardCompliance(self.ethos)
        
    def _load_ethos(self) -> Dict[str, Any]:
        """Load the ethos.json file."""
        with open(self.ethos_path, 'r') as f:
            return json.load(f)
    
    def analyze_logs(self, days: int = 7) -> ValidationMetrics:
        """Analyze logs for the specified time period."""
        start_date = datetime.now() - timedelta(days=days)
        
        # Get recent logs
        empathy_logs = self.logger.get_recent_logs("empathy", days * 24 * 60)
        action_logs = self.logger.get_recent_logs("action", days * 24 * 60)
        validation_logs = self.logger.get_recent_logs("validation", days * 24 * 60)
        
        # Analyze compliance
        metrics = self._calculate_metrics(empathy_logs, action_logs, validation_logs)
        
        # Generate report
        self._generate_report(metrics, empathy_logs, action_logs, validation_logs)
        
        return metrics
    
    def _calculate_metrics(
        self,
        empathy_logs: List[Dict[str, Any]],
        action_logs: List[Dict[str, Any]],
        validation_logs: List[Dict[str, Any]]
    ) -> ValidationMetrics:
        """Calculate validation metrics from logs."""
        total_actions = len(action_logs)
        if total_actions == 0:
            return ValidationMetrics(0, 0, 0, 0, 0.0, {}, {})
        
        # Analyze compliance with core values
        compliant_actions = self._count_compliant_actions(action_logs)
        warning_actions = self._count_warning_actions(action_logs)
        non_compliant_actions = total_actions - compliant_actions - warning_actions
        
        # Calculate drift score (higher means more drift)
        drift_score = non_compliant_actions / total_actions if total_actions > 0 else 0.0
        
        # Get emotional trends and action statistics
        emotional_trends = self.logger.analyze_emotional_trends(days * 24 * 60)
        action_statistics = self.logger.get_action_statistics(days * 24 * 60)
        
        return ValidationMetrics(
            total_actions=total_actions,
            compliant_actions=compliant_actions,
            warning_actions=warning_actions,
            non_compliant_actions=non_compliant_actions,
            drift_score=drift_score,
            emotional_trends=emotional_trends,
            action_statistics=action_statistics
        )
    
    def _count_compliant_actions(self, action_logs: List[Dict[str, Any]]) -> int:
        """Count actions that fully comply with ethos."""
        compliant_count = 0
        
        for log in action_logs:
            action = log["action"]
            context = log["context"]
            
            # Check all compliance aspects
            value_result = self.value_checker.check(action, context)
            principle_result = self.principle_checker.check(action, context)
            safeguard_result = self.safeguard_checker.check(action, context)
            
            if (
                value_result.is_compliant and
                principle_result.is_compliant and
                safeguard_result.is_compliant
            ):
                compliant_count += 1
        
        return compliant_count
    
    def _count_warning_actions(self, action_logs: List[Dict[str, Any]]) -> int:
        """Count actions that trigger warnings but aren't non-compliant."""
        warning_count = 0
        
        for log in action_logs:
            action = log["action"]
            context = log["context"]
            
            # Check all compliance aspects
            value_result = self.value_checker.check(action, context)
            principle_result = self.principle_checker.check(action, context)
            safeguard_result = self.safeguard_checker.check(action, context)
            
            # Count actions with warnings but no critical issues
            if (
                value_result.is_compliant and
                principle_result.is_compliant and
                safeguard_result.is_compliant and
                (
                    len(value_result.warnings) > 0 or
                    len(principle_result.warnings) > 0 or
                    len(safeguard_result.warnings) > 0
                )
            ):
                warning_count += 1
        
        return warning_count
    
    def _generate_report(
        self,
        metrics: ValidationMetrics,
        empathy_logs: List[Dict[str, Any]],
        action_logs: List[Dict[str, Any]],
        validation_logs: List[Dict[str, Any]]
    ):
        """Generate a validation report."""
        report_path = self.logs_path / "validation_reports"
        report_path.mkdir(exist_ok=True)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total_actions": metrics.total_actions,
                "compliant_actions": metrics.compliant_actions,
                "warning_actions": metrics.warning_actions,
                "non_compliant_actions": metrics.non_compliant_actions,
                "drift_score": metrics.drift_score
            },
            "emotional_trends": metrics.emotional_trends,
            "action_statistics": metrics.action_statistics,
            "recommendations": self._generate_recommendations(metrics)
        }
        
        report_file = report_path / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    def _generate_recommendations(self, metrics: ValidationMetrics) -> List[str]:
        """Generate recommendations based on validation metrics."""
        recommendations = []
        
        # Check drift score
        if metrics.drift_score > 0.1:  # More than 10% drift
            recommendations.append("High drift detected - review recent actions for ethos compliance")
        
        # Check warning rate
        if metrics.warning_actions > metrics.total_actions * 0.2:  # More than 20% warnings
            recommendations.append("High warning rate - investigate common warning patterns")
        
        # Check emotional trends
        emotional_trends = metrics.emotional_trends
        if "emotional_contexts" in emotional_trends:
            frustration_count = sum(
                1 for ctx in emotional_trends["emotional_contexts"]
                if ctx.get("user_frustrated", False)
            )
            if frustration_count > len(emotional_trends["emotional_contexts"]) * 0.3:  # More than 30% frustration
                recommendations.append("High user frustration rate - review interaction patterns")
        
        # Check action distribution
        action_stats = metrics.action_statistics
        if "action_distribution" in action_stats:
            high_risk_actions = sum(
                count for action, count in action_stats["action_distribution"].items()
                if action.startswith("high_risk_")
            )
            if high_risk_actions > action_stats["total_actions"] * 0.1:  # More than 10% high-risk actions
                recommendations.append("High rate of high-risk actions - review risk assessment")
        
        return recommendations

def main():
    """Main entry point for ethos validation."""
    validator = EthosValidator()
    metrics = validator.analyze_logs()
    
    logger.info(f"Validation complete:")
    logger.info(f"Total actions: {metrics.total_actions}")
    logger.info(f"Compliant actions: {metrics.compliant_actions}")
    logger.info(f"Warning actions: {metrics.warning_actions}")
    logger.info(f"Non-compliant actions: {metrics.non_compliant_actions}")
    logger.info(f"Drift score: {metrics.drift_score:.2%}")
    
    # Log emotional trends
    logger.info("\nEmotional Trends:")
    for intent, count in metrics.emotional_trends.get("intent_distribution", {}).items():
        logger.info(f"  {intent}: {count}")
    
    # Log action statistics
    logger.info("\nAction Statistics:")
    for action, count in metrics.action_statistics.get("action_distribution", {}).items():
        logger.info(f"  {action}: {count}")

if __name__ == "__main__":
    main() 