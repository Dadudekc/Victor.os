"""
Tests for Agent-4 implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from dreamos.core.coordination.agent_bus import AgentBus, EventType
from dreamos.apps.agent_004.core.agent import Agent4

@pytest.fixture
def mock_agent_bus():
    """Create a mock agent bus for testing."""
    bus = Mock(spec=AgentBus)
    bus.publish = Mock()
    return bus

@pytest.fixture
async def agent(mock_agent_bus):
    """Create an Agent-4 instance for testing."""
    agent = Agent4("Agent-4", mock_agent_bus)
    await agent.start()
    yield agent
    await agent.stop()

@pytest.mark.asyncio
async def test_agent_initialization(agent, mock_agent_bus):
    """Test agent initialization."""
    assert agent.agent_id == "Agent-4"
    assert agent._running is True
    assert mock_agent_bus.publish.called

@pytest.mark.asyncio
async def test_handle_user_query(agent, mock_agent_bus):
    """Test handling a user query."""
    # Create test query
    query_data = {
        "user_id": "test_user",
        "query": "test query"
    }
    
    # Handle query
    await agent._handle_user_query(query_data)
    
    # Verify response was sent
    assert mock_agent_bus.publish.called
    call_args = mock_agent_bus.publish.call_args
    assert call_args[0][0] == EventType.USER_RESPONSE.value
    assert call_args[0][1]["user_id"] == "test_user"
    assert "response" in call_args[0][1]

@pytest.mark.asyncio
async def test_update_user_context(agent):
    """Test updating user context."""
    # Update context
    user_id = "test_user"
    data = {"key": "value"}
    await agent._update_user_context(user_id, data)
    
    # Verify context was updated
    assert user_id in agent._user_contexts
    assert agent._user_contexts[user_id]["key"] == "value"

@pytest.mark.asyncio
async def test_error_handling(agent, mock_agent_bus):
    """Test error handling."""
    # Create test error
    error = Exception("Test error")
    
    # Handle error
    await agent._handle_error(error)
    
    # Verify error was published
    assert mock_agent_bus.publish.called
    call_args = mock_agent_bus.publish.call_args
    assert call_args[0][0] == EventType.ERROR.value
    assert call_args[0][1]["agent_id"] == "Agent-4"
    assert "Test error" in call_args[0][1]["error"]

@pytest.mark.asyncio
async def test_agent_stop(agent):
    """Test agent stop."""
    # Stop agent
    await agent.stop()
    
    # Verify agent stopped
    assert agent._running is False
    assert len(agent._user_contexts) == 0
    assert len(agent._active_tasks) == 0

@pytest.mark.asyncio
async def test_message_processing(agent, mock_agent_bus):
    """Test message processing."""
    # Create test message
    message = {
        "type": "user_query",
        "data": {
            "user_id": "test_user",
            "query": "test query"
        }
    }
    
    # Process message
    await agent._handle_message(message)
    
    # Verify response was sent
    assert mock_agent_bus.publish.called
    call_args = mock_agent_bus.publish.call_args
    assert call_args[0][0] == EventType.USER_RESPONSE.value
    assert call_args[0][1]["user_id"] == "test_user" 