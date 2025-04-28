import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Assume AgentBus is now at the new location
from dreamos.coordination.agent_bus import AgentBus, EventType, Event

@pytest.fixture
def agent_bus():
    # Basic AgentBus instance for testing
    bus = AgentBus()
    # Prevent singleton issues in tests if metaclass is used
    if type(bus).__name__ == 'Singleton':
         AgentBus._instances = {} # Clear singleton instance if necessary
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
    test_event = Event(type=event_type, data={'test': 'data'}, source_id='test_source')

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
    test_event = Event(type=event_type, data={}, source_id='test')
    await agent_bus.publish(event_type, test_event)
    await asyncio.sleep(0.01)
    handler.assert_not_called() 