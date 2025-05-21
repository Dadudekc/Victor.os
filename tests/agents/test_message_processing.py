"""
Tests for agent message processing functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
from pathlib import Path
import asyncio

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
    """Create a temporary mailbox directory with test messages."""
    mailbox_path = tmp_path / "runtime/agent_comms/agent_mailboxes/test-agent"
    mailbox_path.mkdir(parents=True)
    
    # Create test messages
    inbox_path = mailbox_path / "inbox.json"
    outbox_path = mailbox_path / "outbox.json"
    
    test_messages = [
        {"type": "task", "content": "Test task 1"},
        {"type": "notification", "content": "Test notification"}
    ]
    
    with open(inbox_path, "w") as f:
        json.dump(test_messages, f)
    
    with open(outbox_path, "w") as f:
        json.dump([], f)
    
    return mailbox_path

@pytest.mark.asyncio
async def test_process_inbox_messages(mock_config, mock_pbm, temp_mailbox):
    """Test that agent processes inbox messages correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    agent.process_message = AsyncMock()
    
    # Process messages
    await agent._process_mailbox()
    
    # Verify messages were processed
    assert agent.process_message.call_count == 2
    
    # Verify inbox is empty after processing
    with open(os.path.join(temp_mailbox, "inbox.json"), "r") as f:
        inbox = json.load(f)
        assert inbox == []

@pytest.mark.asyncio
async def test_message_validation(mock_config, mock_pbm, temp_mailbox):
    """Test that agent validates messages correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Test with invalid message format
    invalid_message = {"invalid": "format"}
    with pytest.raises(ValueError):
        await agent.process_message(invalid_message)
    
    # Test with missing required fields
    incomplete_message = {"type": "task"}
    with pytest.raises(ValueError):
        await agent.process_message(incomplete_message)

@pytest.mark.asyncio
async def test_message_handling_errors(mock_config, mock_pbm, temp_mailbox):
    """Test that agent handles message processing errors correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    agent.process_message = AsyncMock(side_effect=Exception("Test error"))
    
    # Process messages
    await agent._process_mailbox()
    
    # Verify error was handled
    assert agent.error_count == 2
    assert agent.retry_count == 0

@pytest.mark.asyncio
async def test_outbox_message_sending(mock_config, mock_pbm, temp_mailbox):
    """Test that agent sends messages to outbox correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Create test message
    test_message = {
        "type": "response",
        "content": "Test response",
        "recipient": "other-agent"
    }
    
    # Send message
    await agent.send_message(test_message)
    
    # Verify message was sent
    with open(os.path.join(temp_mailbox, "outbox.json"), "r") as f:
        outbox = json.load(f)
        assert len(outbox) == 1
        assert outbox[0] == test_message

@pytest.mark.asyncio
async def test_message_retry_mechanism(mock_config, mock_pbm, temp_mailbox):
    """Test that agent retries failed messages correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    agent.process_message = AsyncMock(side_effect=[Exception("Test error"), None])
    
    # Process messages
    await agent._process_mailbox()
    
    # Verify retry mechanism
    assert agent.error_count == 1
    assert agent.retry_count == 1
    assert agent.process_message.call_count == 2

@pytest.mark.asyncio
async def test_message_priority_handling(mock_config, mock_pbm, temp_mailbox):
    """Test that agent handles message priorities correctly."""
    # Create agent instance
    agent = BaseAgent(mock_config, mock_pbm)
    
    # Create test messages with priorities
    high_priority = {
        "type": "task",
        "content": "High priority task",
        "priority": "high"
    }
    low_priority = {
        "type": "task",
        "content": "Low priority task",
        "priority": "low"
    }
    
    # Add messages to inbox
    inbox_path = os.path.join(temp_mailbox, "inbox.json")
    with open(inbox_path, "w") as f:
        json.dump([low_priority, high_priority], f)
    
    # Process messages
    await agent._process_mailbox()
    
    # Verify high priority message was processed first
    assert agent.process_message.call_args_list[0][0][0] == high_priority
    assert agent.process_message.call_args_list[1][0][0] == low_priority 