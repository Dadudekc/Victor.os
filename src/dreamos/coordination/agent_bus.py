import time
import logging  # For onboarding logging
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Set
from enum import Enum, auto
from dataclasses import dataclass, field
# from dreamos.coordination.config import WORKSPACE_ROOT # Removed - Config location changed
# from dreamos.config import WORKSPACE_ROOT # WORKSPACE_ROOT not defined here
from dreamos.config import PROJECT_ROOT # Use PROJECT_ROOT defined in config

logger = logging.getLogger("AgentBus")

# --- Event System --- << NEW SECTION

class EventType(Enum):
    # Standard System Events
    SYSTEM_AGENT_REGISTERED = "system.agent.registered"
    SYSTEM_AGENT_UNREGISTERED = "system.agent.unregistered"
    SYSTEM_AGENT_STATUS_CHANGE = "system.agent.status_change"
    SYSTEM_SHUTDOWN_INITIATED = "system.shutdown.initiated"
    SYSTEM_SHUTDOWN_COMPLETED = "system.shutdown.completed"
    SYSTEM_PRE_SHUTDOWN_CHECK = "system.pre_shutdown.check"
    SYSTEM_ERROR = "system.error"

    # Task Events
    TASK_RECEIVED = "task.received"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_PROGRESS = "task.progress"

    # Memory Events << NEW
    MEMORY_UPDATE = "system.memory.update" # Data was written/updated
    MEMORY_READ = "system.memory.read"     # Data was read/accessed
    MEMORY_DELETE = "system.memory.delete" # Data was deleted
    MEMORY_QUERY = "system.memory.query"   # A query was performed
    MEMORY_ERROR = "system.memory.error"   # An error occurred during a memory op

    # Coordination Events
    COORDINATION_DIRECTIVE = "coordination.directive"
    COORDINATION_PROPOSAL = "coordination.proposal"
    COORDINATION_HEARTBEAT = "coordination.heartbeat"

    # Add other high-level categories as needed
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    USER_INPUT = "user.input"
    AGENT_OUTPUT = "agent.output"
    DEBUG = "debug.info"


@dataclass
class BaseEvent:
    """Base class for all events on the AgentBus."""
    event_type: EventType
    source_id: str # ID of the agent or system component dispatching
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

# Define a structured data model for Memory Events (using dataclass for simplicity)
@dataclass
class MemoryEventData:
    agent_id: str # Agent performing the operation
    operation: str # e.g., 'set', 'get', 'delete', 'query'
    key_or_query: str # The key accessed or the query performed
    status: str # 'SUCCESS' or 'FAILURE'
    message: Optional[str] = None # Optional details or error message
    # Avoid including the actual 'value' by default to keep events light
    # value: Optional[Any] = None

class MemoryEvent(BaseEvent):
    """Specific event type for memory operations."""
    def __init__(self, event_type: EventType, source_id: str, data: MemoryEventData):
        # Basic validation that the event_type makes sense
        allowed_types = {EventType.MEMORY_UPDATE, EventType.MEMORY_READ,
                         EventType.MEMORY_DELETE, EventType.MEMORY_QUERY,
                         EventType.MEMORY_ERROR}
        if event_type not in allowed_types:
            raise ValueError(f"Invalid event_type '{event_type}' for MemoryEvent.")
        # Convert dataclass to dict for BaseEvent
        super().__init__(event_type=event_type, source_id=source_id, data=vars(data))

# --- Simple Pub/Sub Implementation --- << NEW SECTION

class SimpleEventBus:
    """A basic in-memory publish-subscribe event bus."""
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[BaseEvent], Any]]] = {}
        self._lock = threading.Lock()
        logger.info("SimpleEventBus initialized.")

    def subscribe(self, event_type_pattern: str, handler: Callable[[BaseEvent], Any]):
        """
        Subscribe a handler to an event type or pattern.
        Supports simple wildcard matching (e.g., "system.memory.*", "*").
        """
        with self._lock:
            if event_type_pattern not in self._subscribers:
                self._subscribers[event_type_pattern] = []
            if handler not in self._subscribers[event_type_pattern]:
                self._subscribers[event_type_pattern].append(handler)
                logger.debug(f"Handler {handler.__name__} subscribed to '{event_type_pattern}'")
            else:
                 logger.warning(f"Handler {handler.__name__} already subscribed to '{event_type_pattern}'")


    def unsubscribe(self, event_type_pattern: str, handler: Callable[[BaseEvent], Any]):
        """Unsubscribe a handler from an event type or pattern."""
        with self._lock:
            if event_type_pattern in self._subscribers:
                try:
                    self._subscribers[event_type_pattern].remove(handler)
                    logger.debug(f"Handler {handler.__name__} unsubscribed from '{event_type_pattern}'")
                    if not self._subscribers[event_type_pattern]: # Remove key if list empty
                         del self._subscribers[event_type_pattern]
                except ValueError:
                    logger.warning(f"Handler {handler.__name__} not found for unsubscribe on '{event_type_pattern}'")

    def dispatch_event(self, event: BaseEvent):
        """
        Dispatch an event to all relevant subscribers.
        Handles wildcard subscriptions.
        """
        if not isinstance(event, BaseEvent):
            logger.error(f"Attempted to dispatch non-BaseEvent object: {type(event)}")
            return

        event_type_str = event.event_type.value # Get the string value like "system.memory.update"
        logger.debug(f"Dispatching event: {event_type_str} (ID: {event.event_id}) from {event.source_id}")

        handlers_to_call: Set[Callable[[BaseEvent], Any]] = set()

        with self._lock:
            # Direct match
            if event_type_str in self._subscribers:
                handlers_to_call.update(self._subscribers[event_type_str])

            # Wildcard match (e.g., "system.memory.*")
            parts = event_type_str.split('.')
            for i in range(1, len(parts) + 1):
                pattern = '.'.join(parts[:i]) + '.*'
                if pattern in self._subscribers:
                    handlers_to_call.update(self._subscribers[pattern])

            # Global wildcard match ("*")
            if "*" in self._subscribers:
                handlers_to_call.update(self._subscribers["*"])

        if not handlers_to_call:
            logger.debug(f"No subscribers found for event type '{event_type_str}'")
            return

        # Call handlers outside the lock to prevent deadlocks if a handler dispatches
        for handler in handlers_to_call:
            try:
                # Consider running handlers in threads/async tasks for non-blocking
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler {handler.__name__} for event {event_type_str}: {e}", exc_info=True)

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
        self._event_bus = SimpleEventBus() # Use the simple pub/sub implementation
        self._onboarded_agents: Set[str] = set()
        self.shutdown_in_progress = False
        self.shutdown_ready: Set[str] = set()

        logger.info("AgentBus Singleton Initialized.")
        self._initialized = True

    # --- Event Methods (delegated to SimpleEventBus) ---
    def subscribe(self, event_type_pattern: str, handler: Callable[[BaseEvent], Any]):
        self._event_bus.subscribe(event_type_pattern, handler)

    def unsubscribe(self, event_type_pattern: str, handler: Callable[[BaseEvent], Any]):
        self._event_bus.unsubscribe(event_type_pattern, handler)

    def dispatch_event(self, event: BaseEvent):
        self._event_bus.dispatch_event(event)

    # --- Agent Management Methods (Simplified, kept original logic where applicable) ---
    def register_agent(self, agent_id: str, capabilities: List[str]):
        if agent_id in self.active_agents:
            logger.warning(f"Agent {agent_id} already registered.")
            # raise ValueError("Agent already registered") # Maybe just warn
            return # Or update capabilities?

        self.active_agents[agent_id] = {
            "agent_id": agent_id,
            "status": "REGISTERED", # Use string status initially
            "capabilities": capabilities,
            "current_task": None,
            "error_message": None
        }
        logger.info(f"Agent registered: {agent_id} with capabilities: {capabilities}")
        # Dispatch system event
        evt = BaseEvent(event_type=EventType.SYSTEM_AGENT_REGISTERED,
                        source_id="AgentBus",
                        data={"agent_id": agent_id, "capabilities": capabilities})
        self.dispatch_event(evt)
        # TODO: Re-integrate onboarding logic if needed

    def unregister_agent(self, agent_id: str):
        if agent_id not in self.active_agents:
            logger.warning(f"Attempted to unregister non-existent agent: {agent_id}")
            # raise ValueError("Agent not registered")
            return

        del self.active_agents[agent_id]
        logger.info(f"Agent unregistered: {agent_id}")
        # Dispatch system event
        evt = BaseEvent(event_type=EventType.SYSTEM_AGENT_UNREGISTERED,
                        source_id="AgentBus",
                        data={"agent_id": agent_id})
        self.dispatch_event(evt)

    # ... (get_agent_info, update_agent_status, get_available_agents - adapt to use BaseEvent/string status)
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.active_agents.get(agent_id)

    def update_agent_status(self, agent_id: str, status: str, task_id: Optional[str] = None, error: Optional[str] = None):
        if agent_id not in self.active_agents:
             logger.warning(f"Cannot update status for unknown agent: {agent_id}")
             return
        info = self.active_agents[agent_id]
        info['status'] = status
        info['current_task'] = task_id
        info['error_message'] = error
        logger.info(f"Agent {agent_id} status updated: {status} (Task: {task_id}, Error: {error})")
        # Add to shutdown ready set if applicable
        if status == "SHUTDOWN_READY": # Assuming string status
             self.shutdown_ready.add(agent_id)
        # Dispatch event
        evt_data = {"agent_id": agent_id, "status": status}
        if task_id: evt_data["task_id"] = task_id
        if error: evt_data["error"] = error
        evt = BaseEvent(event_type=EventType.SYSTEM_AGENT_STATUS_CHANGE,
                        source_id=agent_id, # Source is the agent itself
                        data=evt_data)
        self.dispatch_event(evt)

    # ... (broadcast_shutdown, run_pre_shutdown_diagnostics - adapt as needed)

# Make Event classes available for import
__all__ = ["AgentBus", "BaseEvent", "EventType", "MemoryEvent", "MemoryEventData"]
