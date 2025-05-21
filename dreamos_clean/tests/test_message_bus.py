"""
Tests for the Dream.OS Message Bus implementation.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import time
from dreamos import MessageBus

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

def test_message_bus_initialization(temp_dir):
    """Test message bus initialization."""
    bus = MessageBus(state_dir=temp_dir)
    
    assert bus.state_dir == temp_dir
    assert len(bus.queues) == 0
    assert len(bus.handlers) == 0
    assert len(bus.message_history) == 0

def test_agent_registration(temp_dir):
    """Test agent registration."""
    bus = MessageBus(state_dir=temp_dir)
    
    # Register agent
    bus.register_agent("test-agent")
    assert "test-agent" in bus.queues
    
    # Unregister agent
    bus.unregister_agent("test-agent")
    assert "test-agent" not in bus.queues

def test_message_subscription(temp_dir):
    """Test message subscription."""
    bus = MessageBus(state_dir=temp_dir)
    
    # Track handler calls
    handler_calls = []
    
    def handler(message):
        handler_calls.append(message)
    
    # Subscribe to messages
    bus.subscribe("test_type", handler)
    assert "test_type" in bus.handlers
    assert handler in bus.handlers["test_type"]
    
    # Publish message
    message_id = bus.publish(
        message_type="test_type",
        content={"test": "value"},
        sender="test-agent"
    )
    
    # Check handler called
    assert len(handler_calls) == 1
    assert handler_calls[0]["id"] == message_id
    
    # Unsubscribe
    bus.unsubscribe("test_type", handler)
    assert handler not in bus.handlers["test_type"]

def test_message_publishing(temp_dir):
    """Test message publishing."""
    bus = MessageBus(state_dir=temp_dir)
    
    # Register agents
    bus.register_agent("agent1")
    bus.register_agent("agent2")
    
    # Publish message to specific agent
    message_id = bus.publish(
        message_type="test_type",
        content={"test": "value"},
        sender="agent1",
        recipients=["agent2"]
    )
    
    # Check message in history
    assert message_id in bus.message_history
    
    # Check message in recipient queue
    message = bus.get_messages("agent2")
    assert message["id"] == message_id
    
    # Check message not in sender queue
    assert bus.get_messages("agent1") is None

def test_message_broadcast(temp_dir):
    """Test message broadcasting."""
    bus = MessageBus(state_dir=temp_dir)
    
    # Register agents
    bus.register_agent("agent1")
    bus.register_agent("agent2")
    bus.register_agent("agent3")
    
    # Broadcast message
    message_id = bus.publish(
        message_type="test_type",
        content={"test": "value"},
        sender="agent1"
    )
    
    # Check message in all recipient queues
    assert bus.get_messages("agent2")["id"] == message_id
    assert bus.get_messages("agent3")["id"] == message_id
    
    # Check message not in sender queue
    assert bus.get_messages("agent1") is None

def test_message_history(temp_dir):
    """Test message history."""
    bus = MessageBus(state_dir=temp_dir)
    
    # Publish some messages
    message1_id = bus.publish(
        message_type="type1",
        content={"test": "value1"},
        sender="agent1"
    )
    
    message2_id = bus.publish(
        message_type="type2",
        content={"test": "value2"},
        sender="agent2"
    )
    
    # Get all messages
    messages = bus.get_message_history()
    assert len(messages) == 2
    
    # Filter by type
    type1_messages = bus.get_message_history(message_type="type1")
    assert len(type1_messages) == 1
    assert type1_messages[0]["id"] == message1_id
    
    # Filter by sender
    agent2_messages = bus.get_message_history(sender="agent2")
    assert len(agent2_messages) == 1
    assert agent2_messages[0]["id"] == message2_id

def test_state_persistence(temp_dir):
    """Test state persistence."""
    bus = MessageBus(state_dir=temp_dir)
    
    # Publish a message
    message_id = bus.publish(
        message_type="test_type",
        content={"test": "value"},
        sender="test-agent"
    )
    
    # Create new bus instance
    new_bus = MessageBus(state_dir=temp_dir)
    
    # Check message history loaded
    assert message_id in new_bus.message_history
    assert new_bus.message_history[message_id]["type"] == "test_type" 