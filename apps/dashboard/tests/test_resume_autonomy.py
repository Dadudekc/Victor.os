import pytest
import json
import asyncio
import platform
import os
from pathlib import Path
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QApplication
from apps.dashboard.modules.resume_autonomy import ResumeAutonomyAgentTab, TaskActionMenu
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def app():
    return QApplication([])

@pytest.fixture
def agent_tab(app):
    inbox_base = Path("runtime/agent_comms/agent_mailboxes")
    thea_handler = MagicMock()
    tab = ResumeAutonomyAgentTab("Agent-1", inbox_base, thea_handler)
    tab.notifier = AsyncMock()
    return tab

@pytest.fixture
def status_file(tmp_path):
    status = {
        "agent_id": "Agent-1",
        "current_task": "idle",
        "loop_active": True,
        "last_heartbeat": (datetime.utcnow() - timedelta(minutes=6)).isoformat(),
        "compliance_score": 100
    }
    status_path = tmp_path / "status.json"
    status_path.write_text(json.dumps(status))
    return status_path

def test_agent_tab_initialization(agent_tab):
    """Test that the agent tab initializes correctly"""
    assert agent_tab.agent_id == "Agent-1"
    assert agent_tab.current_task is None
    assert agent_tab.notifier is not None

@pytest.mark.skipif(platform.system() == "Windows", reason="GUI tests not supported on Windows")
def test_task_action_menu(agent_tab):
    """Test that the task action menu has all required actions"""
    menu = TaskActionMenu(agent_tab)
    actions = [action.text() for action in menu.actions()]
    assert "Resume Autonomy" in actions
    assert "Stop Task" in actions
    assert "View Logs" in actions

@pytest.mark.skipif(platform.system() == "Windows", reason="GUI tests not supported on Windows")
def test_theme_application(agent_tab):
    """Test that themes can be applied"""
    agent_tab.apply_theme("dark")
    stylesheet = agent_tab.styleSheet()
    assert "background-color: #212529" in stylesheet
    assert "color: #ffffff" in stylesheet

    agent_tab.apply_theme("light")
    stylesheet = agent_tab.styleSheet()
    assert "background-color: #ffffff" in stylesheet
    assert "color: #000000" in stylesheet

def test_resume_trigger_on_drift(agent_tab, status_file, tmp_path, monkeypatch):
    """Test that drift detection triggers resume action"""
    # Use a real temp file for the bridge queue
    bridge_file = tmp_path / "agent_prompts.jsonl"
    monkeypatch.setattr(
        agent_tab,
        "check_drift",
        lambda: ResumeAutonomyAgentTab.check_drift.__func__(
            agent_tab
        )
    )
    # Patch the bridge file path in the method
    original_bridge_file = "runtime/bridge/queue/agent_prompts.jsonl"
    monkeypatch.setattr(
        "apps.dashboard.modules.resume_autonomy.Path",
        lambda *args, **kwargs: bridge_file if args and args[0] == original_bridge_file else Path(*args, **kwargs)
    )
    # Run drift check
    asyncio.run(agent_tab.check_drift())
    # Verify notification was sent
    agent_tab.notifier.send_alert.assert_called_once_with(
        level="warning",
        title="Drift Detected",
        message="Agent Agent-1 has drifted",
        fields={"Agent": "Agent-1", "Last Heartbeat": pytest.ANY}
    )
    # Verify resume prompt was enqueued
    assert bridge_file.exists()
    prompts = [json.loads(line) for line in bridge_file.read_text().strip().split("\n") if line.strip()]
    assert len(prompts) > 0
    assert prompts[-1]["prompt"] == "resume autonomy"
    assert prompts[-1]["agent_id"] == "Agent-1"

def test_autonomy_loop_recovery(agent_tab, status_file):
    """Test that autonomy loop recovers after resume"""
    # Run resume autonomy
    asyncio.run(agent_tab.resume_autonomy())
    
    # Verify status was updated
    status = json.loads(status_file.read_text())
    assert status["loop_active"] is True
    assert status["compliance_score"] == 100
    
    # Verify notification was sent
    agent_tab.notifier.send_alert.assert_called_once_with(
        level="info",
        title="Autonomy Resumed",
        message="Agent Agent-1 autonomy resumed",
        fields={"Agent": "Agent-1"}
    )

def test_status_file_update(agent_tab, status_file):
    """Test that status file is correctly updated"""
    # Update status
    agent_tab.update_status(
        current_task="testing",
        compliance_score=95
    )
    
    # Verify updates
    status = json.loads(status_file.read_text())
    assert status["current_task"] == "testing"
    assert status["compliance_score"] == 95
    assert status["loop_active"] is True
    
    # Verify timestamp was updated
    last_heartbeat = datetime.fromisoformat(status["last_heartbeat"])
    assert datetime.utcnow() - last_heartbeat < timedelta(seconds=5) 