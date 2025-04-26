import asyncio
from enum import Enum
from typing import Dict, List, Callable
import itertools

class EventType(Enum):
    SYSTEM = "SYSTEM"
    CURSOR = "CURSOR"
    CHAT = "CHAT"
    # Add other event types as needed

class Event:
    def __init__(self, type: EventType, data: dict, source_id: str, priority: int = 0):
        self.type = type
        self.data = data
        self.source_id = source_id
        self.priority = priority

class EventDispatcher:
    """Dispatcher that processes events in priority order."""

    def __init__(self, agent_bus):
        self.agent_bus = agent_bus
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._counter = itertools.count()
        self._running: bool = False
        self._dispatch_task = None

    async def start(self):
        if not self._running:
            self._running = True
            self._dispatch_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self):
        self._running = False
        if self._dispatch_task:
            await self._dispatch_task

    async def _dispatch_loop(self):
        while self._running:
            try:
                priority, _, event = await self._queue.get()
            except asyncio.CancelledError:
                break
            handlers = self._handlers.get(event.type, [])
            for handler in list(handlers):
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        # Await coroutine handler to ensure sequential processing
                        await result
                except Exception:
                    # Ensure one handler error doesn't stop processing
                    pass

    def register_handler(self, event_type: EventType, handler: Callable):
        if not isinstance(event_type, EventType):
            raise ValueError(f"Invalid event type: {event_type}")
        self._handlers.setdefault(event_type, []).append(handler)

    async def dispatch_event(self, event: Event):
        # Use counter as tie-breaker to avoid comparing Event objects
        count = next(self._counter)
        await self._queue.put((event.priority, count, event))

    async def get_handlers(self, event_type: EventType) -> int:
        if not isinstance(event_type, EventType):
            raise ValueError(f"Invalid event type: {event_type}")
        return len(self._handlers.get(event_type, []))

    async def get_queue_size(self) -> int:
        return self._queue.qsize()
