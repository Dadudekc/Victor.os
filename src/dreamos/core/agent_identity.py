"""
Agent Identity module for managing agent identification and roles.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class AgentIdentity:
    """Represents the identity of an agent in the system."""
    
    agent_id: str
    name: str
    role: str
    capabilities: list
    created_at: datetime
    last_seen: Optional[datetime] = None
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.last_seen is None:
            self.last_seen = self.created_at
    
    def update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "created_at": self.created_at.isoformat(),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "status": self.status,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentIdentity':
        """Create from dictionary representation."""
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            role=data["role"],
            capabilities=data["capabilities"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            status=data.get("status", "active"),
            metadata=data.get("metadata", {})
        )


class AgentIdentityManager:
    """Manages agent identities in the system."""
    
    def __init__(self):
        self.identities: Dict[str, AgentIdentity] = {}
    
    def register_agent(self, name: str, role: str, capabilities: list, 
                      metadata: Optional[Dict[str, Any]] = None) -> AgentIdentity:
        """Register a new agent identity."""
        agent_id = str(uuid.uuid4())
        identity = AgentIdentity(
            agent_id=agent_id,
            name=name,
            role=role,
            capabilities=capabilities,
            created_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        self.identities[agent_id] = identity
        return identity
    
    def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get agent identity by ID."""
        return self.identities.get(agent_id)
    
    def update_identity(self, agent_id: str, **kwargs) -> bool:
        """Update agent identity."""
        if agent_id not in self.identities:
            return False
        
        identity = self.identities[agent_id]
        for key, value in kwargs.items():
            if hasattr(identity, key):
                setattr(identity, key, value)
        
        identity.update_last_seen()
        return True
    
    def list_identities(self) -> list[AgentIdentity]:
        """List all agent identities."""
        return list(self.identities.values())
    
    def remove_identity(self, agent_id: str) -> bool:
        """Remove an agent identity."""
        if agent_id in self.identities:
            del self.identities[agent_id]
            return True
        return False 