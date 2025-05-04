"""Defines the base event structure for the AgentBus."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

# Assuming EventType is defined elsewhere, e.g., core.coordination.event_types
# We need to import it carefully to avoid circular dependencies if this file
# is moved under core/events.
# If EventType is in core/coordination, this relative import might work:
from ..coordination.event_types import EventType

# Or use an absolute import if structure allows:
# from dreamos.core.coordination.event_types import EventType


def get_utc_iso_timestamp() -> str:
    """Returns the current UTC time in ISO 8601 format with Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class BaseDreamEvent(BaseModel):
    """Base Pydantic model for all events dispatched via the AgentBus."""

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this event instance.",
    )
    timestamp_utc: str = Field(
        default_factory=get_utc_iso_timestamp,
        description="Timestamp of event creation in UTC ISO 8601 format.",
    )
    source_id: str = Field(
        ...,
        description="Identifier of the agent or system component that originated the event.",  # noqa: E501
    )
    event_type: EventType = Field(..., description="The canonical type of the event.")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Payload data specific to the event type."
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Optional identifier to correlate related events, like request/response pairs.",  # noqa: E501
    )

    class Config:
        """Pydantic config settings."""

        use_enum_values = True  # Ensure EventType enum values are used
        frozen = True  # Make events immutable after creation
