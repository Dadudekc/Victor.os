import asyncio
import logging
from typing import Any, Dict, List, Optional

from dreamos.core.agents.capabilities.schema import AgentCapability

# Import the adapter to pass to the registry
from dreamos.core.db.sqlite_adapter import SQLiteAdapter

# Import the *specific* registry class and the Capability model
from .capability_registry import CapabilityRegistry

logger = logging.getLogger(__name__)


class CapabilityHandler:
    """Handles interactions with the CapabilityRegistry."""

    def __init__(self, adapter: SQLiteAdapter):
        """Initializes the handler and the underlying registry with the adapter."""
        if not adapter:
            logger.critical(
                "CapabilityHandler requires a valid SQLiteAdapter instance!"
            )
            # Or raise an error
            self.registry = None
        else:
            try:
                # Instantiate CapabilityRegistry with the adapter
                self.registry = CapabilityRegistry(adapter=adapter)
            except Exception as e:
                logger.critical(
                    f"Failed to initialize CapabilityRegistry: {e}", exc_info=True
                )
                self.registry = None

        if self.registry is None:
            logger.warning(
                "CapabilityHandler initialized without a valid CapabilityRegistry. Operations will fail."
            )

    async def register_capability(self, capability: AgentCapability) -> bool:
        """Registers or updates a capability via the CapabilityRegistry."""
        if not self.registry:
            logger.error(
                "CapabilityRegistry not available. Cannot register capability."
            )
            return False
        try:
            return await asyncio.to_thread(
                self.registry.register_capability, capability
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.register_capability: {e}",
                exc_info=True,
            )
            return False

    async def unregister_capability(self, agent_id: str, capability_id: str) -> bool:
        """Unregisters a capability via the CapabilityRegistry."""
        if not self.registry:
            logger.error(
                "CapabilityRegistry not available. Cannot unregister capability."
            )
            return False
        try:
            return await asyncio.to_thread(
                self.registry.unregister_capability, agent_id, capability_id
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.unregister_capability: {e}",
                exc_info=True,
            )
            return False

    async def get_capability(
        self, agent_id: str, capability_id: str
    ) -> Optional[AgentCapability]:
        """Retrieves a specific capability via the CapabilityRegistry."""
        if not self.registry:
            logger.error("CapabilityRegistry not available. Cannot get capability.")
            return None
        try:
            return await asyncio.to_thread(
                self.registry.get_capability, agent_id, capability_id
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.get_capability: {e}", exc_info=True
            )
            return None

    async def get_agent_capabilities(self, agent_id: str) -> List[AgentCapability]:
        """Retrieves all capabilities for an agent via the CapabilityRegistry."""
        if not self.registry:
            logger.error(
                "CapabilityRegistry not available. Cannot get agent capabilities."
            )
            return []
        try:
            return await asyncio.to_thread(
                self.registry.get_agent_capabilities, agent_id
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.get_agent_capabilities: {e}",
                exc_info=True,
            )
            return []

    async def find_capabilities(self, query: Dict[str, Any]) -> List[AgentCapability]:
        """Finds capabilities matching criteria via the CapabilityRegistry."""
        if not self.registry:
            logger.error("CapabilityRegistry not available. Cannot find capabilities.")
            return []
        try:
            return await asyncio.to_thread(self.registry.find_capabilities, query)
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.find_capabilities: {e}",
                exc_info=True,
            )
            return []

    async def find_agents_for_capability(
        self, capability_id: str, require_active: bool = True
    ) -> List[str]:
        """Finds agent IDs that offer a specific capability via the CapabilityRegistry."""  # noqa: E501
        if not self.registry:
            logger.error(
                "CapabilityRegistry not available. Cannot find agents for capability."
            )
            return []
        try:
            return await asyncio.to_thread(
                self.registry.find_agents_for_capability,
                capability_id,
                require_active,
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.find_agents_for_capability: {e}",
                exc_info=True,
            )
            return []

    async def update_capability_status(
        self,
        agent_id: str,
        capability_id: str,
        is_active: Optional[bool] = None,
        last_verified_utc: Optional[str] = None,
    ) -> bool:
        """Updates capability status fields via the CapabilityRegistry."""
        if not self.registry:
            logger.error(
                "CapabilityRegistry not available. Cannot update capability status."
            )
            return False
        try:
            return await asyncio.to_thread(
                self.registry.update_capability_status,
                agent_id,
                capability_id,
                is_active=is_active,
                last_verified_utc=last_verified_utc,
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.update_capability_status: {e}",
                exc_info=True,
            )
            return False
