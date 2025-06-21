"""
Agent Documentation Module

This module provides documentation and description utilities for agents.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentDocumentation:
    """Provides documentation and description for agents."""
    agent_id: str
    description: Optional[str] = None
    version: str = "1.0.0"
    metadata: Optional[Dict[str, Any]] = None
    
    def get_summary(self) -> str:
        """Return a summary description for the agent."""
        return self.description or f"Agent {self.agent_id} (v{self.version})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "description": self.description,
            "version": self.version,
            "metadata": self.metadata or {},
        } 