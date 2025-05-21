"""
Feedback Manager Module

Handles feedback metrics tracking, health checks, and reporting.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger('feedback_manager')

class FeedbackManager:
    def __init__(self):
        self.feedback_metrics = {
            "status_reports": 0,
            "resource_checks": 0,
            "channel_health": 0,
            "task_verifications": 0,
            "error_reports": 0
        }
        self.last_update = datetime.now(timezone.utc)
        
    def update_metric(self, metric_type: str) -> None:
        """Update feedback loop metrics."""
        if metric_type in self.feedback_metrics:
            self.feedback_metrics[metric_type] += 1
            self.last_update = datetime.now(timezone.utc)
            
    def check_health(self) -> bool:
        """Check health of feedback loop metrics."""
        try:
            # Verify all metrics are being updated
            for metric, count in self.feedback_metrics.items():
                if count == 0:
                    logger.warning(f"Feedback metric {metric} not updated")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking feedback health: {e}")
            return False
            
    def get_metrics(self) -> Dict[str, int]:
        """Get current feedback metrics."""
        return self.feedback_metrics.copy()
        
    def reset_metrics(self) -> None:
        """Reset all feedback metrics to zero."""
        for metric in self.feedback_metrics:
            self.feedback_metrics[metric] = 0
        self.last_update = datetime.now(timezone.utc) 