"""
Dream.OS Coordination Module
"""

from .event_bus import AgentBus, BaseEvent
from .event_payloads import TaskEventPayload, TaskValidationFailedPayload

__all__ = [
    "AgentBus",
    "BaseEvent",
    "TaskEventPayload",
    "TaskValidationFailedPayload"
] 