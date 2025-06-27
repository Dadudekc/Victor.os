"""Tests for agent lifecycle events in AgentManager."""

import pytest
from dreamos.agents.agent_manager import AgentManager
from dreamos.agents.base_agent import BaseAgent


class DummyAgent(BaseAgent):
    def process_message(self, message):
        return {"ok": True}


def test_lifecycle_events():
    manager = AgentManager()
    agent = DummyAgent("agent-1")
    manager.register_agent(agent)

    assert manager.start_agent("agent-1") is True
    assert manager.is_paused("agent-1") is False

    assert manager.pause_agent("agent-1") is True
    assert manager.is_paused("agent-1") is True

    assert manager.resume_agent("agent-1") is True
    assert manager.is_paused("agent-1") is False

    assert manager.terminate_agent("agent-1") is True
    assert "agent-1" not in manager._agents
