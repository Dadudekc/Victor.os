"""
Agent coordination system for Dream.OS.
Handles agent registration, status tracking, and communication routing.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import json
from pathlib import Path

@dataclass
class AgentCoordinates:
    """Represents an agent's position and status in the system."""
    x: float
    y: float
    z: float

@dataclass
class Agent:
    """Represents a registered agent in the system."""
    id: str
    name: str
    status: str
    coordinates: AgentCoordinates
    inbox_path: Path
    outbox_path: Path

class AgentRegistry:
    """Manages agent registration and coordinates."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.agents: Dict[str, Agent] = {}
        self._load_agents()
    
    def _load_agents(self):
        """Load agent data from the coordinates file."""
        coords_file = self.base_path / "agent_coordinates.json"
        if not coords_file.exists():
            return
            
        with open(coords_file) as f:
            data = json.load(f)
            
        for agent_id, agent_data in data["agents"].items():
            coords = agent_data["coordinates"]
            agent = Agent(
                id=agent_id,
                name=agent_data["name"],
                status=agent_data["status"],
                coordinates=AgentCoordinates(**coords),
                inbox_path=self.base_path / "inboxes" / agent_id,
                outbox_path=self.base_path / "outboxes" / agent_id
            )
            self.agents[agent_id] = agent
            
            # Ensure inbox/outbox directories exist
            agent.inbox_path.mkdir(parents=True, exist_ok=True)
            agent.outbox_path.mkdir(parents=True, exist_ok=True)
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def register_agent(self, agent_id: str, name: str, coordinates: AgentCoordinates) -> Agent:
        """Register a new agent."""
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already registered")
            
        agent = Agent(
            id=agent_id,
            name=name,
            status="active",
            coordinates=coordinates,
            inbox_path=self.base_path / "inboxes" / agent_id,
            outbox_path=self.base_path / "outboxes" / agent_id
        )
        
        self.agents[agent_id] = agent
        agent.inbox_path.mkdir(parents=True, exist_ok=True)
        agent.outbox_path.mkdir(parents=True, exist_ok=True)
        
        self._save_agents()
        return agent
    
    def _save_agents(self):
        """Save agent data to the coordinates file."""
        data = {
            "agents": {
                agent.id: {
                    "id": agent.id,
                    "name": agent.name,
                    "status": agent.status,
                    "coordinates": {
                        "x": agent.coordinates.x,
                        "y": agent.coordinates.y,
                        "z": agent.coordinates.z
                    }
                }
                for agent in self.agents.values()
            }
        }
        
        with open(self.base_path / "agent_coordinates.json", "w") as f:
            json.dump(data, f, indent=4) 