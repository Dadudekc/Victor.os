"""Placeholder for Event Payload definitions."""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BaseEvent(BaseModel):
    """Base model for all events passing through the AgentBus."""

    event_id: str
    timestamp: str
    event_type: str  # Corresponds to EventType enum value typically
    data: Dict[str, Any] = {}


class AgentStatusChangePayload(BaseModel):
    """Placeholder payload for agent status changes."""

    agent_id: str
    new_status: str
    old_status: Optional[str] = None


class AgentStatusEventPayload(BaseModel):
    """Placeholder payload for agent status events."""

    agent_id: str
    status: str
    timestamp: str


class AgentRegistrationPayload(BaseModel):
    """Placeholder payload for agent registration events."""

    agent_id: str
    capabilities: List[str]
    status: str


class CursorInjectRequestPayload(BaseModel):
    """Placeholder payload for cursor injection requests."""

    target_agent_id: str
    prompt: str
    context: Optional[str] = None


class CursorResultPayload(BaseModel):
    """Placeholder payload for cursor results."""

    target_agent_id: str
    request_id: str
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None


class CursorRetrieveRequestPayload(BaseModel):
    """Placeholder payload for cursor retrieval requests."""

    target_agent_id: str
    request_id: str


class ErrorEventPayload(BaseEvent):
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = None  # Agent reporting the error


class MemoryEventData(BaseModel):
    """Placeholder payload for memory-related events."""

    agent_id: str
    memory_type: str  # e.g., 'short_term', 'long_term'
    action: str  # e.g., 'save', 'load', 'query'
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskEventPayload(BaseModel):
    """Placeholder payload for task-related events."""

    task_id: str
    agent_id: Optional[str] = None
    status: Optional[str] = None  # e.g., created, updated, completed, failed
    details: Optional[Dict[str, Any]] = None


class ToolCallPayload(BaseModel):
    """Placeholder payload for tool call events."""

    agent_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    status: str  # e.g., 'pending', 'success', 'failure'


class ToolResultPayload(BaseModel):
    """Placeholder payload for tool result events."""

    agent_id: str
    tool_name: str
    status: str  # 'success' or 'failure'
    result: Optional[Any] = None
    error: Optional[str] = None


class CursorResultEvent(BaseEvent):
    """Placeholder event for cursor results."""

    event_type: str = EventType.CURSOR_RETRIEVE_SUCCESS.value  # Or FAILURE?
    data: CursorResultPayload


# Add other payload definitions as needed

logger.warning("Loaded placeholder module: dreamos.coordination.event_payloads")


# Local definitions for placeholder statuses until proper import
class TaskStatus(Enum):
    PENDING = "PENDING"
    READY = "READY"
    WORKING = "WORKING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    ACCEPTED = "ACCEPTED"
    # Add other statuses if needed
