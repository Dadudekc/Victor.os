"""
Agent Metrics Module

This module provides metrics tracking and reporting for agents.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime

@dataclass
class AgentMetrics:
    """Tracks and reports agent metrics."""
    agent_id: str
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_task_duration: float = 0.0
    uptime_seconds: float = 0.0
    health_score: float = 1.0
    error_count: int = 0
    last_error: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.last_heartbeat:
            data["last_heartbeat"] = self.last_heartbeat.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMetrics":
        data = data.copy()
        if data.get("last_heartbeat"):
            data["last_heartbeat"] = datetime.fromisoformat(data["last_heartbeat"])
        return cls(**data)
    
    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                self.custom_metrics[k] = v 