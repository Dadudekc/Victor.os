"""
Event Payloads for Dream.OS

This module defines the payload classes for various events in the system.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class TaskEventPayload:
    """Base class for task-related event payloads."""
    task_id: str
    details: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class TaskValidationFailedPayload(TaskEventPayload):
    """Payload for task validation failure events."""
    pass

@dataclass
class AgentStatusEventPayload:
    """Payload for agent status change events."""
    agent_id: str
    status: str
    task_id: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class CursorResultPayload:
    """Payload for cursor operation result events."""
    operation: str
    status: str
    agent_id: Optional[str] = None
    retrieved_content: Optional[str] = None
    correlation_id: Optional[str] = None
    message: Optional[str] = None
    result: Optional[Any] = None 