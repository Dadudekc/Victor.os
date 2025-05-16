"""
Event Bus for Dream.OS

This module provides the event bus system for inter-agent communication.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class BaseEvent:
    """Base class for all events."""

    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.now()


class AgentBus:
    """Event bus for inter-agent communication."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "AgentBus":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize the event bus."""
        self.handlers: Dict[str, List[Callable]] = {}

    async def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event.

        Args:
            event_type: Type of event to emit
            data: Event data
        """
        event = BaseEvent(event_type=event_type, data=data)

        # Call handlers
        for handler in self.handlers.get(event_type, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Handler function to call
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
