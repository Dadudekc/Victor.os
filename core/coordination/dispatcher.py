"""Event dispatcher for Dream.OS agent coordination."""

import asyncio
import logging
from enum import Enum
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import uuid

from core.agent_bus import AgentBus

logger = logging.getLogger(__name__)

class EventType(Enum):
    CURSOR = "cursor"
    CHAT = "chat"
    SYSTEM = "system"

    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    GET_AGENT_STATUS = "get_agent_status"
    AGENT_STATUS_RESPONSE = "agent_status_response"
    AGENT_LOGIN = "agent_login"
    CHECK_AGENT_LOGIN_STATUS = "check_agent_login_status"

    TASK_QUEUED = "task_queued"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    POST_CONTENT = "post_content"
    GET_ANALYTICS = "get_analytics"

    PROCESS_FEEDBACK_ITEM = "process_feedback_item"
    REQUEST_CURSOR_ACTION = "request_cursor_action"

    SHUTDOWN_REQUESTED = "shutdown_requested"
    SYSTEM_DIAGNOSTICS_REQUEST = "system_diagnostics_request"
    SYSTEM_DIAGNOSTICS_RESPONSE = "system_diagnostics_response"

    # Meredith Scanner Specific
    SCAN_MEREDITH_RESONANCE = "scan_meredith_resonance"
    MEREDITH_RESONANCE_RESULT = "meredith_resonance_result"

    # --- cleanup / refactor -------------------------------------------------
    REFACTOR_IMPORTS        = "refactor_imports"
    REMOVE_DEAD_CODE        = "remove_dead_code"
    CLEANUPTIME_REQUESTED   = "cleanuptime_requested"

    # Add more specific command/response pairs as needed
    # Example: ANALYTICS_RESULT = "analytics_result" # Could use TASK_COMPLETED with results

class Event:
    """Base event class for agent coordination."""
    
    def __init__(self,
                 type: EventType,
                 source_id: str,
                 target_id: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None,
                 priority: int = 0,
                 id: Optional[str] = None):
        self.type = type
        self.source_id = source_id
        self.target_id = target_id
        self.data = data if data is not None else {}
        self.priority = priority
        self.id = id if id else self._generate_id()
        self.timestamp: Optional[float] = None

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

class EventDispatcher:
    """Unified dispatcher for cursor and chat events."""
    
    def __init__(self, agent_bus: AgentBus):
        self._agent_bus = agent_bus
        self._handlers: Dict[EventType, List[Callable]] = {
            EventType.CURSOR: [],
            EventType.CHAT: [],
            EventType.SYSTEM: []
        }
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        
    def register_handler(self, event_type: EventType, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._handlers:
            logger.warning(f"EventType {event_type} not pre-initialized in dispatcher handlers. Adding dynamically.")
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value} events")
        
    async def dispatch_event(self, event: Event) -> None:
        """Dispatch an event to the appropriate handlers."""
        if not event.timestamp:
            event.timestamp = asyncio.get_event_loop().time()
            
        await self._event_queue.put((event.priority, event.timestamp, event))
        logger.debug(f"Dispatcher Queued {event.type.value} event {event.id} from {event.source_id} for target {event.target_id}")
        
    async def start(self) -> None:
        """Start the event dispatcher."""
        if self._running:
            return
            
        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())
        logger.info("Event dispatcher started")
        
    async def stop(self) -> None:
        """Stop the event dispatcher."""
        if not self._running:
            return
            
        self._running = False
        if self._worker_task:
            try:
                await asyncio.wait_for(self._worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Event dispatcher worker task did not finish promptly. Cancelling.")
                self._worker_task.cancel()
            except Exception as e:
                logger.error(f"Error during event dispatcher stop: {e}")
            finally:
                self._worker_task = None
        logger.info("Event dispatcher stopped")
        
    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running or not self._event_queue.empty():
            try:
                priority, timestamp, event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                
                logger.debug(f"Dispatcher processing event {event.id} ({event.type.name}). Role under review.")
                
                handlers = self._handlers.get(event.type, [])
                if not handlers:
                    logger.warning(f"Dispatcher: No handlers registered for {event.type.value} events (Event ID: {event.id})")
                else:
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(event)
                            else:
                                handler(event)
                        except Exception as e:
                            logger.error(f"Error in dispatcher event handler for {event.type.name} (Event ID: {event.id}): {e}")

                self._event_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Event processor task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error processing event in dispatcher: {e}")
                if 'event' in locals():
                    self._event_queue.task_done()

        logger.info("Event processor stopped")
        
    async def get_queue_size(self) -> int:
        """Get the current size of the event queue."""
        return self._event_queue.qsize()
        
    async def get_handlers(self, event_type: Optional[EventType] = None) -> int:
        """Get count of registered handlers, optionally filtered by type."""
        if event_type:
            return len(self._handlers.get(event_type, []))
        return sum(len(handlers) for handlers in self._handlers.values()) 