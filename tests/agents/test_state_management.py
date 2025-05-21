"""
Tests for agent state management functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
from pathlib import Path
import asyncio
from datetime import datetime, timedelta

from dreamos.core.coordination.abstract_base_agent import BaseAgent
from dreamos.core.config import AppConfig
from dreamos.core.project_board import ProjectBoardManager

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock(spec=AppConfig)
    config.agent_id = "test-agent"
    config.mailbox_path = "runtime/agent_comms/agent_mailboxes/test-agent"
    config.episode_path = "episodes/episode-launch-final-lock.yaml"
    return config

@pytest.fixture
def mock_pbm():
    """Create a mock project board manager."""
    pbm = MagicMock(spec=ProjectBoardManager)
    pbm.list_working_tasks = MagicMock(return_value=[])
    pbm.claim_task = MagicMock(return_value=True)
    return pbm

@pytest.fixture
def temp_mailbox(tmp_path):
    """Create a temporary mailbox directory."""
    mailbox_path = tmp_path / "runtime/agent_comms/agent_mailboxes/test-agent"
    mailbox_path.mkdir(parents=True)
    return mailbox_path

@pytest.fixture
def temp_state_file(tmp_path):
    """Create a temporary state file."""
    state_path = tmp_path / "runtime/agent_comms/agent_mailboxes/test-agent/state.json"
    state_path.parent.mkdir(parents=True)
    return state_path

def test_state_initialization(mock_config, mock_pbm, temp_mailbox, temp_state_file):
    """Test that agent initializes state correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Verify initial state
    assert agent.current_task is None
    assert agent.is_processing is False
    assert agent.last_activity is not None
    assert agent.error_count == 0
    assert agent.retry_count == 0
    
    # Verify state file was created
    assert os.path.exists(temp_state_file)
    
    # Verify state file contents
    with open(temp_state_file, "r") as f:
        state = json.load(f)
        assert state["current_task"] is None
        assert state["is_processing"] is False
        assert "last_activity" in state
        assert state["error_count"] == 0
        assert state["retry_count"] == 0

def test_state_update(mock_config, mock_pbm, temp_mailbox, temp_state_file):
    """Test that agent updates state correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Update state
    test_task = {"id": "task1", "content": "Test task"}
    agent.current_task = test_task
    agent.is_processing = True
    agent.error_count = 1
    agent.retry_count = 1
    
    # Save state
    agent._save_state()
    
    # Verify state file contents
    with open(temp_state_file, "r") as f:
        state = json.load(f)
        assert state["current_task"] == test_task
        assert state["is_processing"] is True
        assert state["error_count"] == 1
        assert state["retry_count"] == 1

def test_state_recovery(mock_config, mock_pbm, temp_mailbox, temp_state_file):
    """Test that agent recovers state correctly."""
    # Create initial state
    initial_state = {
        "current_task": {"id": "task1", "content": "Test task"},
        "is_processing": True,
        "last_activity": datetime.utcnow().isoformat(),
        "error_count": 1,
        "retry_count": 1
    }
    
    with open(temp_state_file, "w") as f:
        json.dump(initial_state, f)
    
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Verify state was recovered
    assert agent.current_task == initial_state["current_task"]
    assert agent.is_processing == initial_state["is_processing"]
    assert agent.error_count == initial_state["error_count"]
    assert agent.retry_count == initial_state["retry_count"]

@pytest.mark.asyncio
async def test_state_activity_tracking(mock_config, mock_pbm, temp_mailbox, temp_state_file):
    """Test that agent tracks activity correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Record initial activity
    initial_activity = agent.last_activity
    
    # Simulate some time passing
    await asyncio.sleep(0.1)
    
    # Update activity
    agent._update_activity()
    
    # Verify activity was updated
    assert agent.last_activity > initial_activity
    
    # Verify state file was updated
    with open(temp_state_file, "r") as f:
        state = json.load(f)
        assert state["last_activity"] == agent.last_activity.isoformat()

def test_state_error_handling(mock_config, mock_pbm, temp_mailbox, temp_state_file):
    """Test that agent handles state errors correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Test with invalid state file
    with open(temp_state_file, "w") as f:
        f.write("invalid json")
    
    # Verify agent handles invalid state
    agent._load_state()
    assert agent.current_task is None
    assert agent.is_processing is False
    assert agent.error_count == 0
    assert agent.retry_count == 0
    
    # Test with missing state file
    os.remove(temp_state_file)
    agent._load_state()
    assert agent.current_task is None
    assert agent.is_processing is False
    assert agent.error_count == 0
    assert agent.retry_count == 0

@pytest.mark.asyncio
async def test_state_concurrent_access(mock_config, mock_pbm, temp_mailbox, temp_state_file):
    """Test that agent handles concurrent state access correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Simulate concurrent state updates
    async def update_state():
        agent.current_task = {"id": "task1", "content": "Test task"}
        agent._save_state()
    
    async def read_state():
        return agent._load_state()
    
    # Run concurrent operations
    await asyncio.gather(
        update_state(),
        read_state(),
        update_state(),
        read_state()
    )
    
    # Verify state is consistent
    with open(temp_state_file, "r") as f:
        state = json.load(f)
        assert state["current_task"] == {"id": "task1", "content": "Test task"}

def test_state_cleanup(mock_config, mock_pbm, temp_mailbox, temp_state_file):
    """Test that agent cleans up state correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Set some state
    agent.current_task = {"id": "task1", "content": "Test task"}
    agent.is_processing = True
    agent._save_state()
    
    # Clean up state
    agent._cleanup_state()
    
    # Verify state was cleaned up
    assert agent.current_task is None
    assert agent.is_processing is False
    assert agent.error_count == 0
    assert agent.retry_count == 0
    
    # Verify state file was updated
    with open(temp_state_file, "r") as f:
        state = json.load(f)
        assert state["current_task"] is None
        assert state["is_processing"] is False
        assert state["error_count"] == 0
        assert state["retry_count"] == 0 