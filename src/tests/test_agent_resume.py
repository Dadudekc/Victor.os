import pytest
from dreamos.tools.agent_resume.agent_resume import AgentResume

def test_agent_resume_init():
    agent = AgentResume(agent_id="Agent-4")
    assert agent.agent_id == "Agent-4"
    assert agent.state is not None

def test_agent_resume_cycle_stub():
    agent = AgentResume(agent_id="Agent-4")
    # Simulate one cycle tick
    result = agent.run_cycle()
    assert isinstance(result, dict) or result is None  # depends on your loop output

def test_agent_resume_headless_mode():
    agent = AgentResume(agent_id="Agent-4", headless=True)
    assert agent.headless is True
    # Verify headless mode skips GUI operations
    result = agent.run_cycle()
    assert result is not None 