# --- Simple Pub/Sub Implementation ---


# Corrected relative imports (assuming events and errors are siblings under core)
# REMOVED Obsolete Edit/TODO comments


class BusError(Exception):
    """Base exception for AgentBus errors."""


class TopicNotFoundError(BusError):
    """Raised when a topic is not found."""


class SubscriberCallbackError(BusError):
    """Raised when a subscriber callback fails."""


class MessageValidationError(BusError):
    """Raised when message validation fails."""


# DELETE START: Remove duplicate/obsolete AgentBus skeleton
# class AgentBus:
#     """
#     An asynchronous event bus for inter-agent and system communication.
#
#     Handles event subscription, publishing, and basic error handling.
#     Uses asyncio for non-blocking operations.
#
#     Core Concepts:
#         - Topics: Hierarchical strings (e.g., "agent.status.online", "task.lifecycle.created").  # noqa: E501
#         - Events: Pydantic models inheriting from BaseEvent, containing data.
#         - Subscribers: Coroutine functions that handle specific event types on topics.
#         - Wildcards: Supports single-level (#) and multi-level (*) wildcards in topic subscriptions.  # noqa: E501
#     """
#
#     # ... existing code ...
# DELETE END

# --- Simple Pub/Sub Implementation ---

# {{ EDIT START: Uncomment and implement AgentBus using placeholder EventBus }}
import logging
import threading
import time

# from collections import defaultdict # Removed F401
# from enum import Enum # Removed F401
from typing import Any, Callable, Dict, List, Optional

# Import specific event types and enums needed by AgentBus
from dreamos.core.coordination.enums import AgentStatus  # Added AgentStatus

# Import necessary types/classes
from dreamos.core.coordination.event_payloads import (  # MOVED AgentStatusEventPayload here
    AgentRegistrationPayload,
    AgentStatusEventPayload,
)
from dreamos.core.coordination.event_types import EventType

# OMITTED: from dreamos.utils.core import Singleton
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Basic Event Bus Implementation ---
# BaseEvent needs to be defined or imported if used by SimpleEventBus methods
# Define a placeholder if it's not critical for current operation
class BaseEvent(BaseModel):  # Placeholder Definition
    event_type: EventType
    source_id: str
    data: Dict[str, Any] = Field(default_factory=dict)


class SimpleEventBus:
    """A simple, thread-safe event bus implementation."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[BaseEvent], Any]]] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger(self.__class__.__name__)

    def subscribe(self, event_type: EventType, handler: Callable[[BaseEvent], Any]):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                self.logger.debug(
                    f"Handler {handler.__name__} subscribed to {event_type}"
                )
            else:
                self.logger.warning(
                    f"Handler {handler.__name__} already subscribed to {event_type}"
                )

    def unsubscribe(self, event_type: EventType, handler: Callable[[BaseEvent], Any]):
        with self._lock:
            if (
                event_type in self._subscribers
                and handler in self._subscribers[event_type]
            ):
                self._subscribers[event_type].remove(handler)
                self.logger.debug(
                    f"Handler {handler.__name__} unsubscribed from {event_type}"
                )
            else:
                self.logger.warning(
                    f"Handler {handler.__name__} not found for event {event_type}"
                )

    def dispatch_event(self, event: BaseEvent):
        handlers_to_call: List[Callable[[BaseEvent], Any]] = []
        with self._lock:
            # Check if event_type exists and has subscribers before accessing
            if (
                event.event_type in self._subscribers
                and self._subscribers[event.event_type]
            ):
                handlers_to_call = list(
                    self._subscribers[event.event_type]
                )  # Copy list for safe iteration

        if handlers_to_call:
            self.logger.debug(
                f"Dispatching event {event.event_type} to {len(handlers_to_call)} handlers."
            )
            for handler in handlers_to_call:
                try:
                    # Ensure handler is callable
                    if callable(handler):
                        handler(event)
                    else:
                        self.logger.error(
                            f"Handler {handler} for event {event.event_type} is not callable."
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error in handler {getattr(handler, '__name__', repr(handler))} for event {event.event_type}: {e}",
                        exc_info=True,
                    )
        else:
            self.logger.debug(f"No subscribers for event {event.event_type}")


# --- Main Agent Bus Facade (Singleton) ---
# Removed metaclass=Singleton reference as it's implemented via __new__


class AgentBus:  # Removed Singleton metaclass
    _instance = None
    _bus: SimpleEventBus  # Correct type hint
    _agent_registry: Dict[str, Dict[str, Any]]
    _registry_lock: threading.Lock
    # logger: logging.Logger # Logger is defined at module level now
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        # Standard Singleton implementation using __new__
        if cls._instance is None:
            cls._instance = super(AgentBus, cls).__new__(cls)
            # Initialize instance attributes here ONLY if they MUST exist before __init__
            # Note: Initialization moved to happen only once in __init__ below
        return cls._instance

    def __init__(self):
        # Ensure initialization happens only once
        if not AgentBus._initialized:
            self._bus = SimpleEventBus()  # Initialize SimpleEventBus here
            self._agent_registry = {}
            self._registry_lock = threading.Lock()
            AgentBus._initialized = True
            logger.info("AgentBus initialized.")
        # else: logger already initialized

    def subscribe(self, event_type: EventType, handler: Callable[[BaseEvent], Any]):
        self._bus.subscribe(event_type, handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[BaseEvent], Any]):
        self._bus.unsubscribe(event_type, handler)

    def dispatch_event(self, event: BaseEvent):
        # Basic validation before dispatch
        if not isinstance(event, BaseEvent):
            logger.error(
                f"Invalid event type passed to dispatch_event: {type(event)}. Must be BaseEvent."
            )
            return
        try:
            # Pydantic validation happens implicitly if needed, or add explicit
            # BaseEvent(**event.model_dump()) # Example explicit re-validation
            self._bus.dispatch_event(event)
        except Exception as e:
            logger.error(
                f"Error during event dispatch preprocessing or call: {e}", exc_info=True
            )

    def register_agent(
        self, agent_id: str, capabilities: List[str], status: str = "Initializing"
    ):
        with self._registry_lock:
            if agent_id in self._agent_registry:
                logger.warning(f"Agent {agent_id} already registered. Updating info.")
            self._agent_registry[agent_id] = {
                "capabilities": capabilities,
                "status": status,
                "last_seen": time.time(),
            }
            logger.info(f"Agent {agent_id} registered with status {status}.")
        # Use the specific payload type
        payload = AgentRegistrationPayload(
            agent_id=agent_id, capabilities=capabilities
        )  # Status not part of this payload
        # Use the placeholder BaseEvent for wrapping
        reg_event = BaseEvent(
            event_type=EventType.SYSTEM_AGENT_REGISTERED,
            source_id="AgentBus",
            data=payload.model_dump(),
        )
        self.dispatch_event(reg_event)

    def unregister_agent(self, agent_id: str):
        with self._registry_lock:
            if agent_id in self._agent_registry:
                del self._agent_registry[agent_id]
                logger.info(f"Agent {agent_id} unregistered.")
                payload = AgentRegistrationPayload(
                    agent_id=agent_id
                )  # No caps/status needed
                unreg_event = BaseEvent(
                    event_type=EventType.SYSTEM_AGENT_UNREGISTERED,
                    source_id="AgentBus",
                    data=payload.model_dump(),
                )
                self.dispatch_event(unreg_event)
            else:
                logger.warning(
                    f"Attempted to unregister non-existent agent: {agent_id}"
                )

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._registry_lock:
            return self._agent_registry.get(agent_id)

    def update_agent_status(
        self, agent_id: str, status: AgentStatus
    ):  # Use Enum type hint
        with self._registry_lock:
            if agent_id in self._agent_registry:
                self._agent_registry[agent_id]["status"] = (
                    status.value
                )  # Store enum value
                self._agent_registry[agent_id]["last_seen"] = time.time()
                # Use AgentStatusEventPayload here
                status_payload = AgentStatusEventPayload(
                    agent_id=agent_id, status=status
                )
                status_event = BaseEvent(
                    event_type=EventType.SYSTEM_AGENT_STATUS_CHANGED,
                    source_id="AgentBus",
                    data=status_payload.model_dump(),
                )
                self.dispatch_event(status_event)
            else:
                logger.warning(
                    f"Attempted to update status for unregistered agent: {agent_id}"
                )


def get_agent_bus() -> AgentBus:
    """Provides access to the AgentBus singleton instance."""
    return AgentBus()


# {{ EDIT END }}
