# src/dreamos/agents/base_agent.py
import logging
from abc import ABC, abstractmethod
from typing import Optional

# Assuming these might be needed, import placeholders/actual implementations
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all DreamOS agents."""

    def __init__(self, agent_id: str, config: AppConfig, agent_bus: AgentBus, **kwargs):
        """
        Initializes the BaseAgent.

        Args:
            agent_id: The unique identifier for this agent instance.
            config: The global application configuration.
            agent_bus: The system-wide event bus for communication.
            **kwargs: Absorbs extra arguments from subclasses or instantiation.
        """
        self.agent_id = agent_id
        self.config = config
        self.agent_bus = agent_bus
        self._current_status: str = "INITIALIZING"  # Example status tracking
        logger.info(f"BaseAgent {self.agent_id} initialized.")
        # Store any extra kwargs if needed by potential future base logic
        self._extra_kwargs = kwargs

    @property
    def status(self) -> str:
        """Returns the current status of the agent."""
        return self._current_status

    async def set_status(self, status: str, details: Optional[dict] = None):
        """Sets the agent's status and optionally publishes an event."""
        # Basic status update, subclasses might override
        old_status = self._current_status
        self._current_status = status
        logger.info(f"Agent {self.agent_id} status changed: {old_status} -> {status}")
        # TODO: Implement event publishing (requires EventType, Payloads)
        # Example:
        # if self.agent_bus:
        #     from dreamos.core.coordination.event_payloads import AgentStatusChangePayload
        #     from dreamos.core.coordination.events import AgentStatusChangeEvent # Assuming exists
        #     payload = AgentStatusChangePayload(agent_id=self.agent_id, new_status=status, old_status=old_status)
        #     event = AgentStatusChangeEvent(data=payload) # Need full event structure
        #     await self.agent_bus.publish(f"agent.{self.agent_id}.status", event.model_dump())
        await asyncio.sleep(0)  # Placeholder for potential async operations

    @abstractmethod
    async def run_autonomous_loop(self):
        """The main autonomous execution loop for the agent."""
        pass

    async def _handle_bus_message(self, topic: str, data: dict):
        """Placeholder for handling messages received from the bus."""
        logger.debug(
            f"Agent {self.agent_id} received message on topic {topic}: {data.keys()}"
        )
        pass

    async def initialize(self):
        """Optional asynchronous initialization steps for the agent."""
        logger.info(f"Agent {self.agent_id} performing async initialization...")
        await self.set_status("IDLE")
        logger.info(f"Agent {self.agent_id} initialized and IDLE.")
        # Example: Subscribe to relevant topics
        # await self.agent_bus.subscribe(f"agent.{self.agent_id}.command", self._handle_bus_message)

    async def shutdown(self):
        """Optional asynchronous cleanup steps for the agent."""
        logger.info(f"Agent {self.agent_id} shutting down...")
        await self.set_status("SHUTDOWN")
        # Example: Unsubscribe from topics
        # await self.agent_bus.unsubscribe(f"agent.{self.agent_id}.command", self._handle_bus_message)


# Need to import asyncio if used above
import asyncio

logger.warning("Loaded placeholder: dreamos.agents.base_agent")
