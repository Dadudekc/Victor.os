"""Simple agent lifecycle manager.

This module provides basic lifecycle controls for agents.
"""
from __future__ import annotations

import logging
from typing import Dict

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentManager:
    """Manage active agents and lifecycle transitions."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}
        self._paused: Dict[str, bool] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a new agent instance."""
        self._agents[agent.agent_id] = agent
        self._paused[agent.agent_id] = False
        logger.info("Registered agent %s", agent.agent_id)

    def start_agent(self, agent_id: str) -> bool:
        """Mark an agent as started."""
        agent = self._agents.get(agent_id)
        if not agent:
            logger.error("Agent %s not registered", agent_id)
            return False
        self._paused[agent_id] = False
        logger.info("Agent %s started", agent_id)
        return True

    def pause_agent(self, agent_id: str) -> bool:
        """Pause a running agent."""
        if agent_id not in self._agents:
            logger.error("Agent %s not registered", agent_id)
            return False
        self._paused[agent_id] = True
        logger.info("Agent %s paused", agent_id)
        return True

    def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent."""
        if agent_id not in self._agents:
            logger.error("Agent %s not registered", agent_id)
            return False
        self._paused[agent_id] = False
        logger.info("Agent %s resumed", agent_id)
        return True

    def terminate_agent(self, agent_id: str) -> bool:
        """Terminate and deregister an agent."""
        if agent_id not in self._agents:
            logger.error("Agent %s not registered", agent_id)
            return False
        self._agents.pop(agent_id)
        self._paused.pop(agent_id, None)
        logger.info("Agent %s terminated", agent_id)
        return True

    def is_paused(self, agent_id: str) -> bool:
        return self._paused.get(agent_id, False)
