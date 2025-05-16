import json
from datetime import datetime, timedelta

import pytest

from apps.dashboard.core.autonomy.agent_autonomy_manager import AgentAutonomyManager


@pytest.fixture
def tmp_inbox_base(tmp_path):
    """Create a temporary inbox base directory."""
    inbox_base = tmp_path / "inbox"
    inbox_base.mkdir()
    return inbox_base


@pytest.fixture
def manager(tmp_inbox_base):
    """Create an AgentAutonomyManager instance."""
    return AgentAutonomyManager(tmp_inbox_base)


@pytest.fixture
def agent_status(tmp_inbox_base):
    """Create a test agent status file."""
    agent_id = "test-agent"
    status_path = tmp_inbox_base / agent_id / "status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)

    status = {
        "agent_id": agent_id,
        "current_task": "test-task",
        "loop_active": True,
        "last_heartbeat": datetime.utcnow().isoformat(),
        "compliance_score": 100,
    }

    status_path.write_text(json.dumps(status))
    return status


def test_detect_drift_no_status(manager):
    """Test drift detection when no status file exists."""
    assert not manager.detect_drift("non-existent-agent")


def test_detect_drift_recent_heartbeat(manager, agent_status):
    """Test drift detection with recent heartbeat."""
    assert not manager.detect_drift("test-agent")


def test_detect_drift_old_heartbeat(manager, agent_status):
    """Test drift detection with old heartbeat."""
    status = manager._load_agent_status("test-agent")
    status["last_heartbeat"] = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
    manager._save_agent_status("test-agent", status)

    assert manager.detect_drift("test-agent")


def test_should_resume_agent_no_status(manager):
    """Test should_resume_agent when no status file exists."""
    assert manager.should_resume_agent("non-existent-agent")


def test_should_resume_agent_inactive_loop(manager, agent_status):
    """Test should_resume_agent when loop is inactive."""
    status = manager._load_agent_status("test-agent")
    status["loop_active"] = False
    manager._save_agent_status("test-agent", status)

    assert manager.should_resume_agent("test-agent")


def test_mark_agent_resumed(manager, agent_status):
    """Test marking agent as resumed."""
    manager.mark_agent_resumed("test-agent")

    status = manager._load_agent_status("test-agent")
    assert status["loop_active"]
    assert status["compliance_score"] == 100
    assert datetime.fromisoformat(
        status["last_heartbeat"]
    ) > datetime.utcnow() - timedelta(seconds=1)


def test_update_agent_status(manager, agent_status):
    """Test updating agent status."""
    manager.update_agent_status(
        "test-agent", current_task="new-task", compliance_score=75
    )

    status = manager._load_agent_status("test-agent")
    assert status["current_task"] == "new-task"
    assert status["compliance_score"] == 75
    assert datetime.fromisoformat(
        status["last_heartbeat"]
    ) > datetime.utcnow() - timedelta(seconds=1)


def test_enqueue_resume_prompt(manager, tmp_path):
    """Test enqueueing a resume prompt."""
    agent_id = "Agent-1"
    bridge_file = tmp_path / "agent_prompts.jsonl"

    # Create manager with custom bridge file
    manager = AgentAutonomyManager(tmp_path, bridge_file=bridge_file)
    manager.enqueue_resume_prompt(agent_id, "Test reason")

    assert bridge_file.exists()

    # Verify prompt content
    with open(bridge_file) as f:
        prompt = json.loads(f.readline())

    assert prompt["agent_id"] == agent_id
    assert prompt["prompt"] == "resume autonomy"
    assert prompt["reason"] == "Test reason"
    assert "timestamp" in prompt
