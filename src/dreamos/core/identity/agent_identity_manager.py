# src/dreamos/core/identity/agent_identity_manager.py
import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from .agent_identity import AgentIdentity
from .agent_identity_store import AgentIdentityStore

logger = logging.getLogger(__name__)


class AgentIdentityError(Exception):
    """Custom exception for Agent Identity Manager errors."""

    pass


class AgentIdentityManager:
    """Manages agent identities, including registration and updates.

    NOTE: This class uses an async initialization pattern.
    Obtain the singleton instance using AgentIdentityManager()
    and then call `await instance.initialize()` before using other methods.
    """

    _instance = None
    _lock = asyncio.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with threading.Lock():
                if cls._instance is None:
                    cls._instance = super(AgentIdentityManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Minimal synchronous initializer for the singleton."""
        pass

    async def initialize(self, store: Optional[AgentIdentityStore] = None):
        """Asynchronously initializes the manager instance and its store."""
        if AgentIdentityManager._initialized:
            return
        async with AgentIdentityManager._lock:
            if AgentIdentityManager._initialized:
                return
            self.store = store or AgentIdentityStore()
            logger.info("AgentIdentityManager initialized.")
            AgentIdentityManager._initialized = True

    async def register_agent(
        self, agent_id: str, role: str = "GenericAgent"
    ) -> AgentIdentity:
        """Registers a new agent identity asynchronously."""
        if not self._initialized:
            raise AgentIdentityError(
                "Manager not initialized. Call await initialize() first."
            )
        existing_identity = await self.store.load(agent_id)
        if existing_identity:
            raise AgentIdentityError(f"Agent with ID '{agent_id}' already registered.")

        identity = AgentIdentity(
            agent_id=agent_id,
            role=role,
        )
        await self.store.save(identity)
        logger.info(f"Registered new agent: ID={agent_id}, Role={role}")
        return identity

    async def update_agent(
        self, agent_id: str, updates: Dict[str, Any]
    ) -> Optional[AgentIdentity]:
        """Updates an existing agent's identity asynchronously."""
        if not self._initialized:
            raise AgentIdentityError(
                "Manager not initialized. Call await initialize() first."
            )
        identity = await self.store.load(agent_id)
        if not identity:
            logger.warning(
                f"Attempted to update non-existent agent identity: {agent_id}"
            )
            return None

        updated = identity.update(updates)

        if updated:
            await self.store.save(identity)
            logger.info(f"Updated identity for agent {agent_id}.")
            return identity
        else:
            logger.debug(f"No changes detected for agent {agent_id}. Update skipped.")
            return identity

    async def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """Retrieves an agent's identity asynchronously."""
        if not self._initialized:
            raise AgentIdentityError(
                "Manager not initialized. Call await initialize() first."
            )
        return await self.store.load(agent_id)

    async def get_all_identities(self) -> List[AgentIdentity]:
        """Retrieves all registered agent identities asynchronously."""
        if not self._initialized:
            raise AgentIdentityError(
                "Manager not initialized. Call await initialize() first."
            )
        return await self.store.get_all()

    async def delete_agent(self, agent_id: str) -> bool:
        """Deletes an agent's identity asynchronously."""
        if not self._initialized:
            raise AgentIdentityError(
                "Manager not initialized. Call await initialize() first."
            )
        return await self.store.delete(agent_id)
