"""Placeholder implementation for EventBus."""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict

logger = logging.getLogger(__name__)

class EventBus:
    """Placeholder EventBus. Logs actions but does not actually route events."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.warning("Creating placeholder EventBus instance.")
            cls._instance = super(EventBus, cls).__new__(cls)
            # Initialize any necessary attributes here if needed
            cls._instance._subscriptions = {}
        return cls._instance

    async def subscribe(
        self,
        event_type_value: str,
        handler: Callable[[Any], Coroutine[Any, Any, None]], # Basic signature
    ):
        """Placeholder subscribe method."""
        logger.info(f"[Placeholder EventBus] Subscribed handler {handler.__name__} to event type '{event_type_value}'")
        # Store subscription if needed for more advanced placeholder
        # self._subscriptions.setdefault(event_type_value, []).append(handler)
        await asyncio.sleep(0) # Yield control for async context

    async def publish(self, topic: str, data: Dict[str, Any]):
        """Placeholder publish method."""
        logger.info(f"[Placeholder EventBus] Published event to topic '{topic}' with data keys: {list(data.keys())}")
        # In a real bus, would find handlers for topic/event type and call them
        await asyncio.sleep(0) # Yield control

    async def dispatch_event(self, event: Any): # Assuming event object has attributes
        """Placeholder dispatch method used by ContextRouterAgent."""
        event_type_str = str(getattr(event, 'event_type', 'unknown_event'))
        target = getattr(event, 'data', {}).get('target_agent_id', 'unknown_target')
        logger.info(f"[Placeholder EventBus] Dispatched event type '{event_type_str}' targeting '{target}'")
        await asyncio.sleep(0)

    # Add other methods if discovered to be needed, e.g., unsubscribe


logger.warning("Using placeholder implementation for EventBus.")
