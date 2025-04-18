# TODO: Expand or reconnect to full version
from typing import Dict, Any, Callable, List, Optional
import asyncio # Needed for async dispatch call
import logging # Use standard logging

logger = logging.getLogger(__name__)

# Attempting to import from the *new* location of bus_types
try:
    from .bus_types import AgentStatus
except ImportError:
    # Fallback if running standalone or path issue
    from enum import Enum
    logger.warning("Failed to import AgentStatus from .bus_types, using fallback enum.")
    class AgentStatus(Enum):
        INITIALIZING = "initializing"; READY = "ready"; SHUTTING_DOWN = "shutting_down"; OFFLINE = "offline"; IDLE = "idle"; SHUTDOWN_READY = "shutdown_ready"; ERROR = "error"; BUSY = "busy"


class AgentRegistry:
    """Manages the registration and status tracking of agents."""
    def __init__(self, dispatch_event_callback: Optional[Callable] = None):
        """Initialize the registry."""
        self._statuses: Dict[str, AgentStatus] = {}
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._dispatch = dispatch_event_callback
        logger.info("[AgentRegistry] Initialized.")

    async def register_agent(self, agent_id: str, info: Dict[str, Any]):
        """Register an agent and set its initial status."""
        if agent_id in self._agents:
             logger.warning(f"[AgentRegistry] Agent {agent_id} already registered. Overwriting.")
        self._agents[agent_id] = info
        await self.update_status(agent_id, AgentStatus.IDLE) # Set initial state
        logger.info(f"[AgentRegistry] Registered agent: {agent_id}")
        # Dispatch registration event (moved here from agent_bus)
        if self._dispatch:
             await self._dispatch(
                 "agent_registered",
                 {"agent_id": agent_id, "capabilities": info.get("capabilities", [])}
             )

    async def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        if agent_id not in self._agents:
            logger.warning(f"[AgentRegistry] Attempted to unregister non-existent agent: {agent_id}")
            return

        self._agents.pop(agent_id, None)
        self._statuses.pop(agent_id, None)
        logger.info(f"[AgentRegistry] Unregistered agent: {agent_id}")
        # Dispatch unregistration event (moved here from agent_bus)
        if self._dispatch:
             await self._dispatch("agent_unregistered", {"agent_id": agent_id})

    async def update_status(self, agent_id: str, status: AgentStatus, task: Optional[str] = None, error: Optional[str] = None):
        """Update agent status and dispatch an event."""
        if agent_id not in self._agents:
            logger.error(f"[AgentRegistry] Cannot update status for unregistered agent: {agent_id}")
            # Decide whether to raise an error or just log
            # raise ValueError(f"Agent {agent_id} is not registered")
            return

        # Basic validation
        if not isinstance(status, AgentStatus):
            try:
                status = AgentStatus(status)
            except ValueError:
                 logger.error(f"[AgentRegistry] Invalid status value '{status}' provided for agent {agent_id}. Use AgentStatus enum.")
                 raise ValueError(f"Invalid status value: {status}")

        logger.debug(f"[AgentRegistry] Updating status for {agent_id} to {status.value}")
        self._statuses[agent_id] = status
        # Update agent info dict as well, if needed
        self._agents[agent_id]["status"] = status
        self._agents[agent_id]["current_task"] = task
        self._agents[agent_id]["error_message"] = error

        # Dispatch status change event
        if self._dispatch:
            await self._dispatch(
                "status_change",
                {
                    "agent_id": agent_id,
                    "status": status.value, # Send the string value
                    "task": task,
                    "error": error
                }
            )

    def get_status(self, agent_id: str) -> AgentStatus:
        """Get the current status of an agent."""
        return self._statuses.get(agent_id, AgentStatus.OFFLINE)

    async def get_available_agents(self, required_capabilities: List[str]) -> List[str]:
        """Find idle agents matching required capabilities."""
        available = []
        # No lock needed if assuming single-threaded access or handled externally by AgentBus lock
        for agent_id, info in self._agents.items():
            # Check status via get_status to handle potential OFFLINE default
            if (self.get_status(agent_id) == AgentStatus.IDLE and
                all(cap in info.get("capabilities", []) for cap in required_capabilities)):
                 available.append(agent_id)
        logger.debug(f"[AgentRegistry] Found available agents: {available} for capabilities {required_capabilities}")
        return available

    async def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the full registration info for an agent."""
        agent_info = self._agents.get(agent_id)
        logger.debug(f"[AgentRegistry] Getting info for agent {agent_id}: Found={bool(agent_info)}")
        return agent_info.copy() if agent_info else None

    async def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get info for all registered agents."""
        logger.debug(f"[AgentRegistry] Getting all agent info ({len(self._agents)} agents)")
        return self._agents.copy() 