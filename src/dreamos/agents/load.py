"""
Agent Load Module

This module provides load balancing and resource management for agents.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentLoad:
    """Manages agent load balancing and resource allocation."""
    agent_id: str
    current_load: float = 0.0
    max_capacity: float = 1.0
    resources: Optional[Dict[str, Any]] = None
    
    def get_load_percentage(self) -> float:
        """Get current load as a percentage of capacity."""
        return (self.current_load / self.max_capacity) * 100 if self.max_capacity > 0 else 0.0
    
    def can_accept_task(self) -> bool:
        """Check if agent can accept additional tasks."""
        return self.current_load < self.max_capacity
    
    def add_load(self, load: float):
        """Add load to the agent."""
        self.current_load = min(self.current_load + load, self.max_capacity)
    
    def remove_load(self, load: float):
        """Remove load from the agent."""
        self.current_load = max(self.current_load - load, 0.0) 