"""
Tests for agent initialization and basic functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
import json
import os
from pathlib import Path

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
def temp_episode(tmp_path):
    """Create a temporary episode file."""
    episode_path = tmp_path / "episodes/episode-launch-final-lock.yaml"
    episode_path.parent.mkdir(parents=True)
    return episode_path

def test_agent_initialization(mock_config, mock_pbm, temp_mailbox, temp_episode):
    """Test that an agent initializes correctly with all required components."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Verify agent properties
    assert agent.agent_id == "test-agent"
    assert agent.mailbox_path == str(temp_mailbox)
    assert agent.episode_path == str(temp_episode)
    
    # Verify mailbox structure
    assert os.path.exists(os.path.join(temp_mailbox, "inbox.json"))
    assert os.path.exists(os.path.join(temp_mailbox, "outbox.json"))
    
    # Verify initial mailbox state
    with open(os.path.join(temp_mailbox, "inbox.json"), "r") as f:
        inbox = json.load(f)
        assert inbox == []
    
    with open(os.path.join(temp_mailbox, "outbox.json"), "r") as f:
        outbox = json.load(f)
        assert outbox == []

def test_agent_mailbox_creation(mock_config, mock_pbm, temp_mailbox):
    """Test that agent creates mailbox structure correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Verify mailbox files exist
    inbox_path = os.path.join(temp_mailbox, "inbox.json")
    outbox_path = os.path.join(temp_mailbox, "outbox.json")
    
    assert os.path.exists(inbox_path)
    assert os.path.exists(outbox_path)
    
    # Verify file permissions
    assert os.access(inbox_path, os.R_OK | os.W_OK)
    assert os.access(outbox_path, os.R_OK | os.W_OK)

def test_agent_config_validation(mock_config, mock_pbm):
    """Test that agent validates configuration correctly."""
    # Test with missing required config
    with pytest.raises(ValueError):
        mock_config.agent_id = None
        BaseAgent(mock_config, mock_pbm)
    
    # Test with invalid mailbox path
    with pytest.raises(ValueError):
        mock_config.mailbox_path = None
        BaseAgent(mock_config, mock_pbm)
    
    # Test with invalid episode path
    with pytest.raises(ValueError):
        mock_config.episode_path = None
        BaseAgent(mock_config, mock_pbm)

def test_agent_state_initialization(mock_config, mock_pbm, temp_mailbox):
    """Test that agent initializes state correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Verify initial state
    assert agent.current_task is None
    assert agent.is_processing is False
    assert agent.last_activity is not None
    assert agent.error_count == 0
    assert agent.retry_count == 0

def test_agent_error_handling(mock_config, mock_pbm, temp_mailbox):
    """Test that agent handles errors correctly during initialization."""
    # Test with invalid mailbox path
    with pytest.raises(OSError):
        mock_config.mailbox_path = "/invalid/path"
        BaseAgent(mock_config, mock_pbm)
    
    # Test with invalid episode path
    with pytest.raises(OSError):
        mock_config.episode_path = "/invalid/path"
        BaseAgent(mock_config, mock_pbm)
    
    # Test with invalid project board manager
    with pytest.raises(ValueError):
        BaseAgent(mock_config, None) 