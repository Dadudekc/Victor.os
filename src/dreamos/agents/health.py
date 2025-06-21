"""
Agent Health Module

This module provides health monitoring and diagnostics for agents.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentHealth:
    """Monitors and reports agent health status."""
    agent_id: str
    health_score: float = 1.0
    status: str = "healthy"
    last_check: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    
    def check_health(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        return {
            "agent_id": self.agent_id,
            "health_score": self.health_score,
            "status": self.status,
            "last_check": self.last_check,
            "metrics": self.metrics or {}
        }
    
    def update_health(self, score: float, status: str = None):
        """Update health metrics."""
        self.health_score = score
        if status:
            self.status = status 