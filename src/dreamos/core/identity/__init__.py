"""Agent identity management for DreamOS.

This package handles the definition, storage, and retrieval of agent identities,
ensuring each agent can be uniquely identified and its metadata accessed.
"""

# Expose key components from this package.
from .agent_identity import AgentIdentity
from .agent_identity_store import AgentIdentityStore
from .agent_identity_manager import AgentIdentityManager, AgentIdentityError

__all__ = [
    "AgentIdentity",
    "AgentIdentityStore",
    "AgentIdentityManager",
    "AgentIdentityError",
] 