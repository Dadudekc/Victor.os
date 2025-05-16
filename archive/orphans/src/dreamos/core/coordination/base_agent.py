"""Base agent class providing common functionality for all Dream.OS agents."""

import logging
from abc import ABC

# Minimal imports for compatibility
# (Assume ProjectBoardManager, AppConfig, AgentBus are available in the active codebase)


class BaseAgent(ABC):
    """Base class for all Dream.OS agents providing common functionality."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._active_tasks = {}
        self.logger = logging.getLogger(agent_id)
        self.cycle_count = 0

    async def execute_task(self, task):
        """Stub for task execution, to be implemented by subclasses."""
        raise NotImplementedError(
            "execute_task must be implemented by agent subclasses."
        )
