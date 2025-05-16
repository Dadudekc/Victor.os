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
