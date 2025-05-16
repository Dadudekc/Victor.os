"""AgentBus module for inter-agent and system communication."""

import logging
import threading
from typing import Any, Callable, Dict, List

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType:
    """Event types for the agent bus."""

    AGENT_STATUS = "agent.status"
    TASK_LIFECYCLE = "task.lifecycle"
    CURSOR_STATE = "system.cursor"
    CURSOR_STUCK = "system.cursor.stuck"


class BaseEvent(BaseModel):
    """Base event model."""

    event_type: str
    source_id: str
    data: Dict[str, Any] = Field(default_factory=dict)


class SimpleEventBus:
    """Simple event bus implementation."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, topic: str, handler: Callable):
        """Subscribe to a topic."""
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable):
        """Unsubscribe from a topic."""
        with self._lock:
            if topic in self._subscribers:
                self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, event: BaseEvent):
        """Publish an event to a topic."""
        with self._lock:
            if topic in self._subscribers:
                for handler in self._subscribers[topic]:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")


class AgentBus:
    """Agent bus for inter-agent and system communication."""

    _instance = None
    _bus: SimpleEventBus
    _agent_registry: Dict[str, Dict[str, Any]]
    _registry_lock: threading.Lock
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AgentBus, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not AgentBus._initialized:
            self._bus = SimpleEventBus()
            self._agent_registry = {}
            self._registry_lock = threading.Lock()
            AgentBus._initialized = True
            logger.info("AgentBus initialized.")

    def subscribe(self, topic: str, handler: Callable):
        """Subscribe to a topic."""
        self._bus.subscribe(topic, handler)

    def unsubscribe(self, topic: str, handler: Callable):
        """Unsubscribe from a topic."""
        self._bus.unsubscribe(topic, handler)

    async def publish(self, topic: str, event: BaseEvent):
        """Publish an event to a topic."""
        await self._bus.publish(topic, event)

    async def close(self):
        """Close the agent bus."""
        logger.info("Closing AgentBus...")
        # Add any cleanup logic here
