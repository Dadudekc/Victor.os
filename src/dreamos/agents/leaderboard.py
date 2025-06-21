"""
Agent Leaderboard Module

This module provides leaderboard tracking for agent performance.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class AgentLeaderboard:
    """Tracks and ranks agents by performance metrics."""
    leaderboard: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_agent(self, agent_id: str, score: float, metadata: Optional[Dict[str, Any]] = None):
        self.leaderboard.append({
            "agent_id": agent_id,
            "score": score,
            "metadata": metadata or {}
        })
        self.leaderboard.sort(key=lambda x: x["score"], reverse=True)
    
    def get_top_agents(self, n: int = 10) -> List[Dict[str, Any]]:
        return self.leaderboard[:n]
    
    def to_dict(self) -> Dict[str, Any]:
        return {"leaderboard": self.leaderboard} 