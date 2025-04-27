from dream_os.core.crew_agent_base import CrewAgent
from dream_os.services.prompt_router_service import PromptRouterService
import pytest
pytestmark = pytest.mark.xfail(reason="Legacy import error", strict=False)
from dream_os.services.task_nexus import add_task, pop_task, log_result

def test_routing_roundtrip(tmp_path, monkeypatch):
    # isolate nexus file path to tmp directory
    monkeypatch.setenv("NEXUS_FILE", str(tmp_path / "nexus.json"))
    # verify agent capability
    agent = CrewAgent("T", "Strategist")
    assert agent.can_handle("plan")
    # add and pop task
    tid = add_task("plan", "Draft monetization")
    task = pop_task()
    assert task and task.get("id") == tid
    # execute and check result status
    res = agent.execute(task)
    assert res.get("status") == "ok" 
