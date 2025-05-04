"""Pydantic models for Dreamscape inter-agent communication event payloads."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ..core.content_models import ContentDraft, ContentPlan


# Base model for common event fields
class BaseEventPayload(BaseModel):
    """Base model containing fields common to most Dreamscape events."""

    source_agent: str = Field(
        ..., description="The ID of the agent publishing the event."
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Optional ID to track a request across multiple events/agents.",
    )
    # timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # noqa: E501


# Specific Event Payloads


class PlanRequestedPayload(BaseEventPayload):
    """Payload for requesting a new content plan."""

    topic: str = Field(..., description="The desired topic for the content plan.")
    requester_id: Optional[str] = Field(
        default=None, description="The ID of the agent or entity requesting the plan."
    )
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional dictionary for additional planning constraints (e.g., desired length, style).",  # noqa: E501
    )


class PlanGeneratedPayload(BaseEventPayload):
    """Payload for publishing a newly generated content plan."""

    plan: ContentPlan = Field(..., description="The generated ContentPlan object.")
    requester_id: Optional[str] = Field(
        default=None,
        description="The ID of the original requester, passed through for context.",
    )


class WritingRequestedPayload(BaseEventPayload):
    """Payload for requesting content generation based on a plan."""

    plan: ContentPlan = Field(
        ..., description="The ContentPlan to be used for generation."
    )


class DraftGeneratedPayload(BaseEventPayload):
    """Payload for publishing a newly generated content draft."""

    draft: ContentDraft = Field(..., description="The generated ContentDraft object.")


class PublishRequestedPayload(BaseEventPayload):
    """Payload for requesting the publication of a content draft."""

    draft_id: Optional[str] = Field(
        default=None,
        description="Reference ID of the draft to publish (if managed separately).",
    )
    draft_content: Optional[ContentDraft] = Field(
        default=None,
        description="Alternatively, the full draft content can be included.",
    )
    target_channel: str = Field(
        ...,
        description="The intended channel for publication (e.g., 'devblog', 'twitter').",  # noqa: E501
    )
    channel_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dictionary for channel-specific options (e.g., tags, publish time).",  # noqa: E501
    )


# Potential Error/Status Event Payloads
class PlanFailedPayload(BaseEventPayload):
    """Payload indicating a failure during content plan generation."""

    topic: str = Field(..., description="The topic for which planning failed.")
    requester_id: Optional[str] = Field(
        default=None, description="The ID of the original requester."
    )
    error_message: str = Field(..., description="Description of the error encountered.")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional dictionary containing more error details or context.",
    )


class DraftFailedPayload(BaseEventPayload):
    """Payload indicating a failure during content draft generation."""

    topic: str = Field(
        ..., description="The topic (from the plan) for which writing failed."
    )
    error_message: str = Field(..., description="Description of the error encountered.")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional dictionary containing more error details or context.",
    )
