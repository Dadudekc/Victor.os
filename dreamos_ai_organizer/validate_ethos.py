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

class EthosValidator:
    """Validates system behavior against ethos guidelines."""
    
    def __init__(self):
        self.ethos_path = Path(__file__).parent / "ethos.json"
        self.logs_path = Path(__file__).parent / "logs"
        self.ethos = self._load_ethos()
        
    def _load_ethos(self) -> Dict[str, Any]:
        """Load the ethos.json file."""
        with open(self.ethos_path, 'r') as f:
            return json.load(f)
    
    def analyze_logs(self, days: int = 7) -> ValidationMetrics:
        """Analyze logs for the specified time period."""
        start_date = datetime.now() - timedelta(days=days)
        
        # Load and filter logs
        empathy_logs = self._load_empathy_logs(start_date)
        action_logs = self._load_action_logs(start_date)
        
        # Analyze compliance
        metrics = self._calculate_metrics(empathy_logs, action_logs)
        
        # Generate report
        self._generate_report(metrics, empathy_logs, action_logs)
        
        return metrics
    
    def _load_empathy_logs(self, start_date: datetime) -> pd.DataFrame:
        """Load and filter empathy logs."""
        log_path = self.logs_path / "empathy.log"
        if not log_path.exists():
            return pd.DataFrame()
            
        logs = []
        with open(log_path, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    if datetime.fromisoformat(log_entry['timestamp']) >= start_date:
                        logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
                    
        return pd.DataFrame(logs)
    
    def _load_action_logs(self, start_date: datetime) -> pd.DataFrame:
        """Load and filter action logs."""
        log_path = self.logs_path / "actions.log"
        if not log_path.exists():
            return pd.DataFrame()
            
        logs = []
        with open(log_path, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line)
                    if datetime.fromisoformat(log_entry['timestamp']) >= start_date:
                        logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
                    
        return pd.DataFrame(logs)
    
    def _calculate_metrics(self, empathy_logs: pd.DataFrame, action_logs: pd.DataFrame) -> ValidationMetrics:
        """Calculate validation metrics from logs."""
        total_actions = len(action_logs)
        if total_actions == 0:
            return ValidationMetrics(0, 0, 0, 0, 0.0)
            
        # Analyze compliance with core values
        compliant_actions = self._count_compliant_actions(action_logs)
        warning_actions = self._count_warning_actions(action_logs)
        non_compliant_actions = total_actions - compliant_actions - warning_actions
        
        # Calculate drift score (higher means more drift)
        drift_score = non_compliant_actions / total_actions if total_actions > 0 else 0.0
        
        return ValidationMetrics(
            total_actions=total_actions,
            compliant_actions=compliant_actions,
            warning_actions=warning_actions,
            non_compliant_actions=non_compliant_actions,
            drift_score=drift_score
        )
    
    def _count_compliant_actions(self, action_logs: pd.DataFrame) -> int:
        """Count actions that fully comply with ethos."""
        # Implementation specific to ethos guidelines
        return len(action_logs)  # Placeholder
    
    def _count_warning_actions(self, action_logs: pd.DataFrame) -> int:
        """Count actions that trigger warnings but aren't non-compliant."""
        # Implementation specific to ethos guidelines
        return 0  # Placeholder
    
    def _generate_report(self, metrics: ValidationMetrics, empathy_logs: pd.DataFrame, action_logs: pd.DataFrame):
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
            "recommendations": self._generate_recommendations(metrics)
        }
        
        report_file = report_path / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    def _generate_recommendations(self, metrics: ValidationMetrics) -> List[str]:
        """Generate recommendations based on validation metrics."""
        recommendations = []
        
        if metrics.drift_score > 0.1:  # More than 10% drift
            recommendations.append("High drift detected - review recent actions for ethos compliance")
        
        if metrics.warning_actions > metrics.total_actions * 0.2:  # More than 20% warnings
            recommendations.append("High warning rate - investigate common warning patterns")
        
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

if __name__ == "__main__":
    main() 