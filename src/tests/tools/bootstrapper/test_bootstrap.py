import pytest
from dreamos.tools.bootstrapper import Bootstrapper

def test_bootstrapper_load():
    bs = Bootstrapper(agent_id="Agent-4")
    assert bs.agent_id == "Agent-4"
    assert hasattr(bs, "start")

def test_bootstrapper_start_stub(monkeypatch):
    def mock_agent_resume(agent_id, headless=False):
        return None
    monkeypatch.setattr("dreamos.tools.bootstrapper.AgentResume", mock_agent_resume)
    bs = Bootstrapper(agent_id="Agent-4")
    assert bs is not None  # placeholder until actual loop is hooked

def test_bootstrapper_headless_mode():
    bs = Bootstrapper(agent_id="Agent-4", headless=True)
    assert bs.headless is True
    # Verify headless mode is passed to AgentResume
    assert bs.agent_resume.headless is True 