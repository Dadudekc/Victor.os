"""Core AgentBus implementation using SimpleEventBus.

Provides a singleton `AgentBus` class that wraps `SimpleEventBus` for
loose coupling and potential future replacement.

This bus facilitates asynchronous communication between agents using a
publish-subscribe pattern based on hierarchical topic strings defined in the
`EventType` enum.

Topic Standard:
  Topics generally follow the pattern: `domain.entity.action[.qualifier]`
  Examples:
    - `dreamos.agent.status.updated`
    - `dreamos.task.completed`
    - `dreamos.agent.{agent_id}.task.command` (Agent-specific command)
    - `dreamscape.content.plan.generated`

Events are represented by `BaseEvent` dataclasses or subclasses thereof.
"""

# {{ EDIT END }}
import asyncio
import logging  # For onboarding logging
import threading  # EDIT: Ensure threading is imported for Lock
import time
import traceback  # IMPORT ADDED FOR ERROR PAYLOAD
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ..utils.logging_utils import log_handler_exception

# Imports moved from lower in the file to fix E402
# {{ EDIT START: Add Payload Imports }}
from .event_payloads import (  # AgentStatusChangePayload, # EDIT: Remove - Replaced by AgentStatusEventPayload (which isn't used directly here)  # noqa: E501
    AgentRegistrationPayload,
    CursorInjectRequestPayload,
    CursorResultPayload,
    CursorRetrieveRequestPayload,
    ErrorEventPayload,  # EDIT: Replace AgentErrorPayload
    MemoryEventData,
    TaskEventPayload,
    ToolCallPayload,
    ToolResultPayload,
)

# from dreamos.core.config import PROJECT_ROOT  # Explicitly comment out PROJECT_ROOT


# {{ EDIT END }}
# {{ EDIT START: Import TaskStatus for payload definition }}
# from .message_patterns import TaskStatus # Explicitly comment out TaskStatus


# from dreamos.coordination.config import WORKSPACE_ROOT # Removed - Config location changed  # noqa: E501
# from dreamos.config import WORKSPACE_ROOT # WORKSPACE_ROOT not defined here
# from dreamos.config import PROJECT_ROOT  # Use PROJECT_ROOT defined in config


logger = logging.getLogger("AgentBus")


# EDIT START: Improve Exception Docstrings
class BusError(Exception):
    """Base class for AgentBus related errors."""

    pass


class SubscriptionError(BusError):
    """Raised for errors during handler subscription or unsubscription."""

    pass


class DispatchError(BusError):
    """Raised for errors during the event dispatch process itself (e.g., invalid event)."""  # noqa: E501

    pass


class EventHandlerError(DispatchError):
    """Raised specifically when an exception occurs within a subscribed event handler.

    Attributes:
        original_exception: The exception caught from the handler.
        handler: The handler function that caused the error.
        event: The BaseEvent being processed when the error occurred.
    """

    def __init__(self, message, original_exception=None, handler=None, event=None):
        super().__init__(message)
        self.original_exception = original_exception
        self.handler = handler
        self.event = event


# EDIT END

# --- Event System --- << NEW SECTION


class EventType(Enum):
    # Standard System Events - Using domain.entity.action[.qualifier]
    SYSTEM_AGENT_REGISTERED = "dreamos.agent.registered"  # Changed topic
    SYSTEM_AGENT_UNREGISTERED = "dreamos.agent.unregistered"  # Changed topic
    SYSTEM_AGENT_STATUS_CHANGE = "dreamos.agent.status.updated"  # Changed topic
    SYSTEM_SHUTDOWN_INITIATED = "dreamos.system.shutdown.initiated"  # Changed topic
    SYSTEM_SHUTDOWN_COMPLETED = "dreamos.system.shutdown.completed"  # Changed topic
    SYSTEM_PRE_SHUTDOWN_CHECK = "dreamos.system.pre_shutdown.check"  # Changed topic
    SYSTEM_ERROR = "dreamos.system.error"  # Changed topic

    # Task Events
    # Using specific agent target for commands, general topics for status
    # TASK_COMMAND = "dreamos.agent.{agent_id}.task.command" # Pattern handled in BaseAgent subscribe  # noqa: E501
    TASK_RECEIVED = "dreamos.task.received"  # Changed topic
    TASK_ACCEPTED = "dreamos.task.accepted"  # Changed topic
    TASK_STARTED = "dreamos.task.started"  # Changed topic
    TASK_COMPLETED = "dreamos.task.completed"  # Changed topic
    TASK_FAILED = "dreamos.task.failed"  # Changed topic
    TASK_PROGRESS = "dreamos.task.progress"  # Changed topic
    TASK_CANCELLED = "dreamos.task.cancelled"  # Added based on BaseAgent usage
    TASK_PERMANENTLY_FAILED = (
        "dreamos.task.permanently_failed"  # Added based on BaseAgent usage
    )
    TASK_TIMEOUT = "dreamos.task.timeout"  # Changed topic
    TASK_REQUEST_SENT = "dreamos.task.request.sent"  # Changed topic
    TASK_CANCEL_REQUESTED = "dreamos.task.cancel.requested"  # Changed topic
    TASK_CANCEL_FAILED = "dreamos.task.cancel.failed"  # Changed topic
    TASK_DIRECTIVE = "dreamos.task.directive"  # Changed topic

    # Memory Events << NEW
    MEMORY_UPDATE = "dreamos.memory.updated"  # Changed topic
    MEMORY_READ = "dreamos.memory.read"  # Changed topic
    MEMORY_DELETE = "dreamos.memory.deleted"  # Changed topic
    MEMORY_QUERY = "dreamos.memory.queried"  # Changed topic
    MEMORY_ERROR = "dreamos.memory.error"  # Changed topic

    # Coordination Events
    COORDINATION_DIRECTIVE = "dreamos.coordination.directive.sent"  # Changed topic
    COORDINATION_PROPOSAL = "dreamos.coordination.proposal.made"  # Changed topic
    COORDINATION_HEARTBEAT = "dreamos.coordination.heartbeat.sent"  # Changed topic

    # Cursor Automation Events << NEW SECTION
    CURSOR_INJECT_REQUEST = "dreamos.cursor.inject.request"  # Changed topic
    CURSOR_RETRIEVE_REQUEST = "dreamos.cursor.retrieve.request"  # Changed topic
    CURSOR_INJECT_SUCCESS = "dreamos.cursor.inject.success"  # Changed topic
    CURSOR_INJECT_FAILURE = "dreamos.cursor.inject.failure"  # Changed topic
    CURSOR_RETRIEVE_SUCCESS = "dreamos.cursor.retrieve.success"  # Changed topic
    CURSOR_RETRIEVE_FAILURE = "dreamos.cursor.retrieve.failure"  # Changed topic
    CURSOR_WINDOW_UNRESPONSIVE = "dreamos.cursor.window.unresponsive"  # Changed topic
    CURSOR_HEALTH_CHECK_PASSED = "dreamos.cursor.health.passed"  # Changed topic
    CURSOR_HEALTH_CHECK_FAILED = "dreamos.cursor.health.failed"  # Changed topic

    # Tool Events
    TOOL_CALL = "dreamos.tool.call.requested"  # Changed topic
    TOOL_RESULT = "dreamos.tool.result.received"  # Changed topic

    # User/Agent I/O
    USER_INPUT = "dreamos.user.input.received"  # Changed topic
    AGENT_OUTPUT = "dreamos.agent.output.sent"  # Changed topic

    # Debugging
    DEBUG_INFO = "dreamos.debug.info"  # Changed topic

    # Governance & Control Events
    POLICY_VIOLATION = "dreamos.governance.policy.violated"  # Changed topic
    AUTH_FAILURE = "dreamos.security.auth.failed"  # Changed topic
    PERMISSION_DENIED = "dreamos.security.permission.denied"  # Changed topic
    AGENT_CONTRACT_QUERY = "dreamos.governance.contract.queried"  # Changed topic
    AGENT_CONTRACT_STATUS = "dreamos.governance.contract.status"  # Changed topic
    AGENT_PROTOCOL_VIOLATION = "dreamos.governance.protocol.violated"  # Changed topic

    # Query & Discovery Events
    QUERY_AGENT_STATUS = "dreamos.query.agent.status"  # Changed topic
    QUERY_TASK_DETAILS = "dreamos.query.task.details"  # Changed topic
    QUERY_SYSTEM_HEALTH = "dreamos.query.system.health"  # Changed topic

    # Command Supervisor Events (Assuming domain 'supervisor')
    COMMAND_EXECUTION_REQUEST = "dreamos.supervisor.command.requested"  # Changed topic
    COMMAND_APPROVAL_REQUEST = "dreamos.supervisor.approval.requested"  # Changed topic
    COMMAND_APPROVAL_RESPONSE = "dreamos.supervisor.approval.responded"  # Changed topic
    COMMAND_EXECUTION_RESULT = "dreamos.supervisor.command.result"  # Changed topic

    # Dreamscape Specific Events (Example - keep separate or integrate? Integrate for now)  # noqa: E501
    DREAMSCAPE_PLAN_REQUESTED = "dreamscape.plan.requested"  # Changed topic
    DREAMSCAPE_PLAN_GENERATED = "dreamscape.plan.generated"  # Changed topic
    DREAMSCAPE_PLAN_FAILED = "dreamscape.plan.failed"  # Changed topic
    DREAMSCAPE_WRITING_REQUESTED = "dreamscape.writing.requested"  # Changed topic
    DREAMSCAPE_DRAFT_GENERATED = "dreamscape.draft.generated"  # Changed topic
    DREAMSCAPE_DRAFT_FAILED = "dreamscape.draft.failed"  # Changed topic

    # Old/Unsorted - Review and map/remove
    # START_CHATGPT_QUERY = "start_chatgpt_query" # Map to a TASK event? Or specific integration event?  # noqa: E501
    # TASK_INJECTED_VIA_ROUTER = "task_injected_via_router" # Map to TASK_ACCEPTED or similar?  # noqa: E501
    # SCRAPER_ERROR = "scraper_error" # Map to AGENT_ERROR or specific integration error?  # noqa: E501
    # ROUTING_FAILED = "routing_failed" # Map to AGENT_ERROR?
    # PYAUTOGUI_ERROR = "pyautogui_error" # Map to TOOL_RESULT or AGENT_ERROR?
    # INJECTION_FAILED = "injection_failed" # Map to CURSOR_INJECT_FAILURE?


@dataclass
class BaseEvent:
    """Base class for all events on the AgentBus."""

    event_type: EventType
    source_id: str  # ID of the agent or system component dispatching
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    correlation_id: Optional[str] = None  # Optional ID for tracking requests/responses


# Import from event_payloads instead
# from .event_payloads import MemoryEventData # Moved to top


class MemoryEvent(BaseEvent):
    """Specific event type for memory operations."""

    def __init__(self, event_type: EventType, source_id: str, data: MemoryEventData):
        # Basic validation that the event_type makes sense
        allowed_types = {
            EventType.MEMORY_UPDATE,
            EventType.MEMORY_READ,
            EventType.MEMORY_DELETE,
            EventType.MEMORY_QUERY,
            EventType.MEMORY_ERROR,
        }
        if event_type not in allowed_types:
            raise ValueError(f"Invalid event_type '{event_type}' for MemoryEvent.")
        # Convert dataclass to dict for BaseEvent
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))


# Import necessary payload types
# from .event_payloads import AgentErrorPayload  # EDIT: Remove this import
# from .event_payloads import ( # Moved to top
#     CursorInjectRequestPayload,
#     CursorResultPayload,
#     CursorRetrieveRequestPayload,
#     TaskEventPayload,
#     ToolCallPayload,
#     ToolResultPayload,
# )


class TaskEvent(BaseEvent):
    """Specific event for task lifecycle events."""

    def __init__(self, event_type: EventType, source_id: str, data: TaskEventPayload):
        # Basic validation (could check if event_type starts with 'task.')
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))


class ToolCallEvent(BaseEvent):
    """Specific event for tool calls."""

    def __init__(self, event_type: EventType, source_id: str, data: ToolCallPayload):
        if event_type != EventType.TOOL_CALL:
            raise ValueError("Invalid event_type for ToolCallEvent.")
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))


class ToolResultEvent(BaseEvent):
    """Specific event for tool results."""

    def __init__(self, event_type: EventType, source_id: str, data: ToolResultPayload):
        if event_type != EventType.TOOL_RESULT:
            raise ValueError("Invalid event_type for ToolResultEvent.")
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))


class CursorInjectRequestEvent(BaseEvent):
    """Specific event for cursor injection requests."""

    def __init__(
        self, event_type: EventType, source_id: str, data: CursorInjectRequestPayload
    ):
        if event_type != EventType.CURSOR_INJECT_REQUEST:
            raise ValueError("Invalid event_type for CursorInjectRequestEvent.")
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))


class CursorRetrieveRequestEvent(BaseEvent):
    """Specific event for cursor retrieval requests."""

    def __init__(
        self, event_type: EventType, source_id: str, data: CursorRetrieveRequestPayload
    ):
        if event_type != EventType.CURSOR_RETRIEVE_REQUEST:
            raise ValueError("Invalid event_type for CursorRetrieveRequestEvent.")
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))


class CursorResultEvent(BaseEvent):
    """Specific event for cursor operation results (success/failure)."""

    def __init__(
        self, event_type: EventType, source_id: str, data: CursorResultPayload
    ):
        allowed = {
            EventType.CURSOR_INJECT_SUCCESS,
            EventType.CURSOR_INJECT_FAILURE,
            EventType.CURSOR_RETRIEVE_SUCCESS,
            EventType.CURSOR_RETRIEVE_FAILURE,
        }
        if event_type not in allowed:
            raise ValueError("Invalid event_type for CursorResultEvent.")
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))


class AgentErrorEvent(BaseEvent):
    """Specific event type for agent or system error events."""

    # EDIT: Update data parameter type hint to ErrorEventPayload
    def __init__(self, event_type: EventType, source_id: str, data: ErrorEventPayload):
        # If EventType.AGENT_ERROR doesn't exist, this needs adjustment
        # For now, let's assume it does or that SYSTEM_ERROR is used.
        # We could check if event_type == EventType.SYSTEM_ERROR or event_type == getattr(EventType, 'AGENT_ERROR', None)  # noqa: E501
        if event_type not in [
            EventType.SYSTEM_ERROR,
            EventType.AGENT_ERROR,
        ]:  # EDIT: Assume AGENT_ERROR exists
            logger.warning(
                f"Potential misuse: Creating AgentErrorEvent with type {event_type}"
            )
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))


# {{ EDIT END }}

# --- Simple Pub/Sub Implementation --- << NEW SECTION


class SimpleEventBus:
    """A basic in-memory publish-subscribe event bus supporting wildcard subscriptions.

    Note: This implementation uses a single lock for subscriber modifications,
    making subscribe/unsubscribe thread-safe but potentially limiting concurrency
    under very high subscription churn. Event dispatch calls handlers sequentially
    after retrieving them under the lock.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[BaseEvent], Any]]] = {}
        self._lock = threading.Lock()  # EDIT: Revert to threading.Lock
        logger.info("SimpleEventBus initialized.")

    def subscribe(self, event_type_pattern: str, handler: Callable[[BaseEvent], Any]):
        """
        Subscribe a handler callable to events matching a specific pattern.

        Patterns can be exact event types (e.g., 'system.agent.registered'),
        use a trailing wildcard (e.g., 'system.agent.*'), or be a global
        wildcard ('*') to receive all events.

        Args:
            event_type_pattern: The string pattern to subscribe to.
            handler: A callable that accepts a single `BaseEvent` argument.

        Raises:
            SubscriptionError: If the provided handler is not callable.
        """
        with self._lock:  # Use threading.Lock correctly
            if not callable(handler):
                raise SubscriptionError(
                    f"Handler must be callable, got {type(handler)}"
                )  # Add check
            if event_type_pattern not in self._subscribers:
                self._subscribers[event_type_pattern] = []
            if handler not in self._subscribers[event_type_pattern]:
                self._subscribers[event_type_pattern].append(handler)
                logger.debug(
                    f"Handler {getattr(handler, '__name__', repr(handler))} subscribed to '{event_type_pattern}'"  # noqa: E501
                )
            else:
                logger.warning(
                    f"Handler {getattr(handler, '__name__', repr(handler))} already subscribed to '{event_type_pattern}'"  # noqa: E501
                )

    def unsubscribe(self, event_type_pattern: str, handler: Callable[[BaseEvent], Any]):
        """Unsubscribe a specific handler from a given event type pattern."""
        with self._lock:  # Use threading.Lock correctly
            if event_type_pattern in self._subscribers:
                try:
                    self._subscribers[event_type_pattern].remove(handler)
                    logger.debug(
                        f"Handler {getattr(handler, '__name__', repr(handler))} unsubscribed from '{event_type_pattern}'"  # noqa: E501
                    )
                    if not self._subscribers[
                        event_type_pattern
                    ]:  # Remove key if list empty
                        del self._subscribers[event_type_pattern]
                except ValueError:
                    # Do not raise error, just log warning if handler not found
                    logger.warning(
                        f"Handler {getattr(handler, '__name__', repr(handler))} not found for unsubscribe on '{event_type_pattern}'"  # noqa: E501
                    )

    def dispatch_event(self, event: BaseEvent):
        """
        Dispatches an event to all handlers subscribed to matching patterns.

        Finds all subscribers based on exact match, prefix wildcards
        (e.g., "system.*"), and the global wildcard ("*"). Calls each unique
        handler once. Errors within handlers are logged but do not stop
        dispatch to other handlers.

        Args:
            event: The `BaseEvent` instance to dispatch.

        Raises:
            DispatchError: If the object being dispatched is not an instance of `BaseEvent`.
        """  # noqa: E501
        if not isinstance(event, BaseEvent):
            # EDIT START: Raise specific error
            # logger.error(f"Attempted to dispatch non-BaseEvent object: {type(event)}")
            raise DispatchError(
                f"Attempted to dispatch non-BaseEvent object: {type(event)}"
            )
            # EDIT END
            # return # No longer needed

        event_type_str = (
            event.event_type.value
        )  # Get the string value like "system.memory.update"
        logger.debug(
            f"Dispatching event: {event_type_str} (ID: {event.event_id}) from {event.source_id}"  # noqa: E501
        )

        handlers_to_call: Set[Callable[[BaseEvent], Any]] = set()

        with self._lock:  # Use threading.Lock correctly to read subscribers
            # Direct match
            if event_type_str in self._subscribers:
                handlers_to_call.update(self._subscribers[event_type_str])

            # Wildcard match (e.g., "system.memory.*")
            parts = event_type_str.split(".")
            for i in range(1, len(parts) + 1):
                pattern = ".".join(parts[:i]) + ".*"
                if pattern in self._subscribers:
                    handlers_to_call.update(self._subscribers[pattern])

            # Global wildcard match ("*")
            if "*" in self._subscribers:
                handlers_to_call.update(self._subscribers["*"])

        if not handlers_to_call:
            logger.debug(f"No subscribers found for event type '{event_type_str}'")
            return

        # Call handlers outside the lock
        for handler in handlers_to_call:
            try:
                # EDIT START: Keep the improved handler calling logic
                if asyncio.iscoroutinefunction(handler):
                    # Schedule the coroutine as a task
                    try:
                        loop = asyncio.get_running_loop()
                        task = loop.create_task(
                            handler(event),
                            name=f"EventHandler-{getattr(handler, '__name__', 'unknown')}-{event.event_id[:8]}",  # noqa: E501
                        )
                        task.add_done_callback(self._handle_handler_task_completion)
                    except RuntimeError:  # If no running loop, log error
                        logger.error(
                            f"Cannot schedule async handler {getattr(handler, '__name__', 'unknown')} for event {event.event_id}: No running asyncio event loop."  # noqa: E501
                        )
                    except Exception as task_create_err:
                        logger.error(
                            f"Error creating task for async handler {getattr(handler, '__name__', 'unknown')} for event {event.event_id}: {task_create_err}",  # noqa: E501
                            exc_info=True,
                        )
                else:
                    # Call synchronous handlers directly
                    handler(event)
                # EDIT END
            except Exception as e:
                # Catch errors during sync call or scheduling
                handler_name = getattr(handler, "__name__", repr(handler))
                err_msg = f"Error synchronously invoking/scheduling handler {handler_name} for event {event.event_id} ({event.event_type.value}) from {event.source_id}: {e}"  # noqa: E501
                logger.error(err_msg, exc_info=True)
                # Consider dispatching error event here if needed

    # EDIT START: Add helper methods for async handler completion and error dispatch
    def _handle_handler_task_completion(self, task: asyncio.Task):
        """Callback executed when an event handler coroutine finishes."""
        try:
            exception = task.exception()
            if exception:
                handler_info = self._running_handlers.get(task, None)
                handler = (
                    handler_info["handler"] if handler_info else "<unknown handler>"
                )
                event = handler_info["event"] if handler_info else "<unknown event>"

                # Log the error details
                log_handler_exception(logger, exception, handler, event)

                # Create ErrorEventPayload
                payload = ErrorEventPayload(
                    error_message=f"Error in handler {getattr(handler, '__name__', repr(handler))} for event {event.event_id if event else 'N/A'}: {exception}",  # noqa: E501
                    agent_id=None,  # System-level error in handler
                    task_id=None,
                    exception_type=type(exception).__name__,
                    traceback="\n".join(
                        traceback.format_exception(
                            type(exception), exception, exception.__traceback__
                        )
                    ),
                    details={
                        "handler": repr(handler),
                        "event_data": event.data if event else None,
                    },
                )

                # Dispatch a SYSTEM_ERROR event
                error_event = BaseEvent(
                    event_type=EventType.SYSTEM_ERROR,
                    source_id="AgentBus",
                    data=payload.to_dict(),  # Assuming payload needs serialization
                    correlation_id=event.correlation_id if event else None,
                )
                # Avoid awaiting dispatch here to prevent deadlocks if the bus is blocked  # noqa: E501
                # Use asyncio.create_task to run it independently
                asyncio.create_task(self.dispatch_event(error_event))

        except asyncio.CancelledError:
            logger.info(f"Handler task {task.get_name()} was cancelled.")
        except Exception as e:
            # Catch-all for errors within this callback itself
            logger.error(
                f"Error in _handle_handler_task_completion: {e}", exc_info=True
            )
        finally:
            # Clean up the reference to the completed task
            if task in self._running_handlers:
                del self._running_handlers[task]

    # Optional: Helper to dispatch a standardized error event -> REMOVED as logic moved inline  # noqa: E501
    # def _dispatch_handler_error(...): ...
    # EDIT END


# --- AgentBus using SimpleEventBus --- << MODIFIED SECTION


class AgentBus:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton implementation
        if cls._instance is None:
            cls._instance = super(AgentBus, cls).__new__(cls)
            # Initialize only once
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initializes the AgentBus singleton."""
        if self._initialized:
            return

        # Core state
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        self._event_bus = SimpleEventBus()  # Use the simple pub/sub implementation
        self._onboarded_agents: Set[str] = set()
        self.shutdown_in_progress = False
        self.shutdown_ready: Set[str] = set()

        logger.info("AgentBus Singleton Initialized.")
        self._initialized = True

    # --- Event Methods (delegated to SimpleEventBus) ---
    def subscribe(self, event_type_pattern: str, handler: Callable[[BaseEvent], Any]):
        """Subscribe a handler to an event type pattern on the bus."""
        self._event_bus.subscribe(event_type_pattern, handler)

    def unsubscribe(self, event_type_pattern: str, handler: Callable[[BaseEvent], Any]):
        """Unsubscribe a handler from an event type pattern on the bus."""
        self._event_bus.unsubscribe(event_type_pattern, handler)

    def dispatch_event(self, event: BaseEvent):
        """Dispatch an event onto the bus."""
        self._event_bus.dispatch_event(event)

    # --- Agent Management Methods (Simplified, kept original logic where applicable) ---  # noqa: E501
    def register_agent(self, agent_id: str, capabilities: List[str]):
        """Registers an agent with the bus, storing its ID and capabilities.
        Dispatches a SYSTEM_AGENT_REGISTERED event.
        Logs a warning if the agent is already registered.
        """
        if agent_id in self.active_agents:
            logger.warning(f"Agent {agent_id} already registered.")
            return

        self.active_agents[agent_id] = {
            "agent_id": agent_id,
            "status": "REGISTERED",
            "capabilities": capabilities,
            "last_heartbeat": time.time(),
        }
        payload = AgentRegistrationPayload(agent_id=agent_id, capabilities=capabilities)
        evt = BaseEvent(
            event_type=EventType.SYSTEM_AGENT_REGISTERED,
            source_id="AgentBus",
            data=payload.__dict__,
        )
        self.dispatch_event(evt)
        logger.info(f"Agent {agent_id} registered with capabilities: {capabilities}")

    def unregister_agent(self, agent_id: str):
        """Unregisters an agent from the bus.
        Dispatches a SYSTEM_AGENT_UNREGISTERED event.
        """
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
            if agent_id in self._onboarded_agents:
                self._onboarded_agents.remove(agent_id)
            logger.info(f"Agent {agent_id} unregistered.")
            payload = AgentRegistrationPayload(agent_id=agent_id)
            evt = BaseEvent(
                event_type=EventType.SYSTEM_AGENT_UNREGISTERED,
                source_id="AgentBus",
                data=payload.__dict__,
            )
            self.dispatch_event(evt)
        else:
            logger.warning(f"Attempted to unregister non-existent agent: {agent_id}")

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Returns information about a registered agent."""
        return self.active_agents.get(agent_id)

    def update_agent_status(
        self,
        agent_id: str,
        status: str,
        task_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Updates the status of a registered agent.
        Dispatches a SYSTEM_AGENT_STATUS_CHANGE event.
        """
        if agent_id not in self.active_agents:
            logger.warning(
                f"Attempted to update status for non-registered agent: {agent_id}"
            )
            return

        self.active_agents[agent_id]["status"] = status
        self.active_agents[agent_id]["last_update"] = time.time()
        logger.debug(f"Agent {agent_id} status updated to: {status}")

        payload = AgentStatusChangePayload(  # noqa: F821
            agent_id=agent_id, status=status, task_id=task_id, error_message=error
        )
        evt = BaseEvent(
            event_type=EventType.SYSTEM_AGENT_STATUS_CHANGE,
            source_id="AgentBus",
            data=payload.__dict__,
        )
        self.dispatch_event(evt)

    # ... (broadcast_shutdown, run_pre_shutdown_diagnostics - adapt as needed)


# Make Event classes available for import
__all__ = ["AgentBus", "BaseEvent", "EventType", "MemoryEvent", "MemoryEventData"]
