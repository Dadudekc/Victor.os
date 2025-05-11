# src/dreamscape/events/event_types.py
from enum import Enum


class DreamscapeEventType(Enum):
    PLAN_REQUESTED = "DREAMSCAPE_PLAN_REQUESTED"
    PLAN_GENERATED = "DREAMSCAPE_PLAN_GENERATED"
    PLAN_FAILED = "dreamscape.event.plan.failed"
    WRITING_REQUESTED = "DREAMSCAPE_WRITING_REQUESTED"
    DRAFT_GENERATED = "DREAMSCAPE_DRAFT_GENERATED"
    DRAFT_FAILED = "dreamscape.event.draft.failed"
    PUBLISH_REQUESTED = "DREAMSCAPE_PUBLISH_REQUESTED"
    # Add more as needed


# class AgentStatus(Enum):
#     # Add AgentStatus enum definitions here
#     pass
