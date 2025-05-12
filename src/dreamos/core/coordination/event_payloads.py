"""
Event Payloads for Dream.OS

This module defines the payload classes for various events in the system.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

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