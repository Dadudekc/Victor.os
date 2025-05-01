import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Assume AgentBus is now at the new location
from dreamos.coordination.agent_bus import AgentBus, Event, EventType


@pytest.fixture
def agent_bus():
    # Basic AgentBus instance for testing
    bus = AgentBus()
    # Prevent singleton issues in tests if metaclass is used
    if type(bus).__name__ == "Singleton":
        AgentBus._instances = {}  # Clear singleton instance if necessary
    return bus


@pytest.mark.asyncio
async def test_agent_bus_register_handler(agent_bus):
    handler = AsyncMock()
    sub_id = await agent_bus.register_handler(EventType.SYSTEM, handler)
    assert sub_id is not None
    assert EventType.SYSTEM in agent_bus._handlers
    assert sub_id in agent_bus._handlers[EventType.SYSTEM]


@pytest.mark.asyncio
async def test_agent_bus_publish_subscribe(agent_bus):
    handler = AsyncMock()
    event_type = EventType.SYSTEM
    test_event = Event(type=event_type, data={"test": "data"}, source_id="test_source")

    sub_id = await agent_bus.register_handler(event_type, handler)
    await agent_bus.publish(event_type, test_event)

    # Allow time for event processing
    await asyncio.sleep(0.01)

    handler.assert_called_once_with(test_event)


@pytest.mark.asyncio
async def test_agent_bus_unsubscribe(agent_bus):
    handler = AsyncMock()
    event_type = EventType.AGENT
    sub_id = await agent_bus.register_handler(event_type, handler)
    assert event_type in agent_bus._handlers
    assert sub_id in agent_bus._handlers[event_type]

    unsub_result = await agent_bus.unsubscribe(sub_id)
    assert unsub_result is True
    assert sub_id not in agent_bus._handlers.get(event_type, {})

    # Verify publish doesn't call handler after unsubscribe
    test_event = Event(type=event_type, data={}, source_id="test")
    await agent_bus.publish(event_type, test_event)
    await asyncio.sleep(0.01)
    handler.assert_not_called()


# --- Test AgentBus Singleton and Delegation ---


def test_agent_bus_singleton():
    bus1 = AgentBus()
    bus2 = AgentBus()
    assert bus1 is bus2


@patch("dreamos.coordination.agent_bus.SimpleEventBus", autospec=True)
def test_agent_bus_delegates_to_simple_bus(MockSimpleEventBus):
    # Reset singleton instance for isolation
    AgentBus._instance = None

    mock_simple_bus_instance = MockSimpleEventBus.return_value
    agent_bus = AgentBus()  # This should create and store the mock instance

    assert agent_bus._event_bus is mock_simple_bus_instance

    # Test delegation
    handler = lambda e: print(e)
    event = BaseEvent(EventType.SYSTEM_ERROR, "test_src")

    try:
        # Intentional wildcard subscription for comprehensive logging
        agent_bus.subscribe("system.*", handler)
    except AttributeError as e:
        logger.error(f"Failed to subscribe: {e}")

    mock_simple_bus_instance.subscribe.assert_called_once_with("system.*", handler)

    agent_bus.unsubscribe("system.*", handler)
    mock_simple_bus_instance.unsubscribe.assert_called_once_with("system.*", handler)

    agent_bus.dispatch_event(event)
    mock_simple_bus_instance.dispatch_event.assert_called_once_with(event)


# --- Add Unsubscribe Tests for SimpleEventBus ---


def test_unsubscribe_removes_handler(simple_bus):
    """Test that unsubscribe removes a specific handler."""
    handler1_called = False
    handler2_called = False

    def handler1(event):
        nonlocal handler1_called
        handler1_called = True

    def handler2(event):
        nonlocal handler2_called
        handler2_called = True

    topic = "test.topic"
    event = BaseEvent(
        EventType.SYSTEM_ERROR, "test_src", data={}
    )  # Type doesn't matter here
    event.event_type.value = topic  # Force topic for matching

    simple_bus.subscribe(topic, handler1)
    simple_bus.subscribe(topic, handler2)

    # Unsubscribe handler1
    simple_bus.unsubscribe(topic, handler1)

    # Dispatch - only handler2 should be called
    simple_bus.dispatch_event(event)

    assert not handler1_called
    assert handler2_called
    # Check internal state (optional but good)
    assert topic in simple_bus._subscribers
    assert handler1 not in simple_bus._subscribers[topic]
    assert handler2 in simple_bus._subscribers[topic]


def test_unsubscribe_removes_topic_if_empty(simple_bus):
    """Test that the topic key is removed if no handlers remain."""
    handler_called = False

    def handler(event):
        nonlocal handler_called
        handler_called = True

    topic = "empty.topic"
    event = BaseEvent(EventType.SYSTEM_ERROR, "test_src", data={})
    event.event_type.value = topic

    simple_bus.subscribe(topic, handler)
    assert topic in simple_bus._subscribers

    simple_bus.unsubscribe(topic, handler)

    # Topic should be gone
    assert topic not in simple_bus._subscribers

    # Dispatching should not call the handler
    simple_bus.dispatch_event(event)
    assert not handler_called


def test_unsubscribe_nonexistent_handler(simple_bus):
    """Test that unsubscribing a handler not subscribed to a topic is safe."""
    handler1_called = False

    def handler1(event):
        nonlocal handler1_called
        handler1_called = True

    def handler_never_subscribed(event):
        pass

    topic = "safe.unsubscribe"
    event = BaseEvent(EventType.SYSTEM_ERROR, "test_src", data={})
    event.event_type.value = topic

    simple_bus.subscribe(topic, handler1)

    # Unsubscribe a handler that was never added to this topic
    simple_bus.unsubscribe(topic, handler_never_subscribed)

    # Check internal state and dispatch
    assert handler1 in simple_bus._subscribers[topic]
    simple_bus.dispatch_event(event)
    assert handler1_called


def test_unsubscribe_nonexistent_topic(simple_bus):
    """Test that unsubscribing from a topic with no subscribers is safe."""

    def handler(event):
        pass

    topic = "never.subscribed.topic"

    # Should not raise an error
    simple_bus.unsubscribe(topic, handler)
    assert topic not in simple_bus._subscribers
