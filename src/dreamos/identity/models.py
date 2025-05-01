import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


def default_timestamp() -> float:
    """Returns the current UTC timestamp."""
    return time.time()


@dataclass
class AgentIdentity:
    """Represents the static and dynamic identity attributes of an agent."""

    agent_id: str
    role: str = "Generic Agent"
    metadata: Dict[str, Any] = field(default_factory=dict)  # For extra info
    created_at: float = field(default_factory=default_timestamp)
    last_seen_at: float = field(default_factory=default_timestamp)

    def update_last_seen(self):
        """Updates the last_seen_at timestamp to the current time."""
        self.last_seen_at = default_timestamp()

    def to_dict(self) -> Dict[str, Any]:
        """Converts the dataclass instance to a dictionary."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentIdentity":
        """Creates an AgentIdentity instance from a dictionary."""
        return cls(
            agent_id=data.get("agent_id", "unknown_agent"),
            role=data.get("role", "Generic Agent"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", default_timestamp()),
            last_seen_at=data.get("last_seen_at", default_timestamp()),
        )
