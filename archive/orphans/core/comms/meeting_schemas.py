# src/dreamos/core/comms/meeting_schemas.py
import logging
from datetime import datetime, timezone
from typing import List, Literal, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# TODO (Masterpiece Review - Captain-Agent-8): Ensure UUID format consistency.
#      This uses `str(uuid4())` (hyphenated), while mailbox_utils used `.hex`.
#      Decide on one standard format (e.g., hex) for IDs across the system.
def generate_uuid():
    return str(uuid4())


def current_utc_iso():
    return datetime.now(timezone.utc).isoformat()


# --- Base Message --- #


class BaseMeetingMessage(BaseModel):
    """Base model for all messages within a meeting mailbox."""

    message_id: str = Field(default_factory=generate_uuid)
    meeting_id: str
    timestamp_utc: str = Field(default_factory=current_utc_iso)
    agent_id: str  # ID of the agent posting the message
    message_type: str  # Specific type identifier (e.g., 'comment', 'proposal')


# --- Specific Message Types --- #


class MeetingComment(BaseMeetingMessage):
    """A general comment or discussion point."""

    message_type: Literal["comment"] = "comment"
    text: str
    reply_to_message_id: Optional[str] = None  # ID of the message being replied to


class MeetingProposal(BaseMeetingMessage):
    """A formal proposal for discussion or voting."""

    message_type: Literal["proposal"] = "proposal"
    proposal_id: str = Field(
        default_factory=generate_uuid
    )  # Unique ID for this proposal
    title: str
    details: str
    status: Literal["proposed", "voting", "accepted", "rejected", "withdrawn"] = (
        "proposed"
    )


class MeetingVote(BaseMeetingMessage):
    """A vote cast on a specific proposal."""

    message_type: Literal["vote"] = "vote"
    proposal_id: str  # ID of the proposal being voted on
    vote_value: Literal["yes", "no", "abstain"]
    rationale: Optional[str] = None


class MeetingSummary(BaseMeetingMessage):
    """A summary of discussion points or meeting outcomes."""

    message_type: Literal["summary"] = "summary"
    summary_text: str
    related_proposal_ids: List[str] = Field(default_factory=list)


class MeetingStateChange(BaseMeetingMessage):
    """Indicates a change in the overall meeting state."""

    message_type: Literal["state_change"] = "state_change"
    old_state: str
    new_state: str
    reason: Optional[str] = None


class MeetingAgendaItem(BaseMeetingMessage):
    """An item added to the meeting agenda."""

    message_type: Literal["agenda_item"] = "agenda_item"
    item_id: str = Field(default_factory=generate_uuid)
    description: str
    status: Literal["pending", "discussed", "resolved"] = "pending"


# --- Meeting Metadata (for manifest.json) --- #


class ParticipantInfo(BaseModel):
    agent_id: str
    status: Literal["invited", "joined", "left"] = "invited"
    joined_at_utc: Optional[str] = None
    # Add voting status if needed: last_voted_proposal_id: Optional[str] = None


class MeetingManifest(BaseModel):
    """Metadata stored in manifest.json for a meeting."""

    meeting_id: str
    topic: str
    goal: Optional[str] = None
    creator_agent_id: str
    created_at_utc: str = Field(default_factory=current_utc_iso)
    last_updated_utc: str = Field(default_factory=current_utc_iso)
    current_state: Literal["open", "discussion", "voting", "closed", "archived"] = (
        "open"
    )
    protocol_version: str = "v1"
    facilitator_agent_id: Optional[str] = None
    # Participants list might be better in participants.json for easier updates
    # initial_invitees: List[str] = Field(default_factory=list)
    # TODO (Masterpiece Review - Captain-Agent-8): Consider moving participant list
    #      (currently commented out/not present) to a separate participants.json
    #      to avoid frequent writes to the main manifest file.


# Union type for easy parsing of messages read from files
AnyMeetingMessage = Union[
    MeetingComment,
    MeetingProposal,
    MeetingVote,
    MeetingSummary,
    MeetingStateChange,
    MeetingAgendaItem,
    # Add other types as needed
]

# Example Usage (for testing/documentation):
# comment = MeetingComment(meeting_id="meeting-xyz", agent_id="Agent1", text="I agree with the proposal.")
# proposal = MeetingProposal(meeting_id="meeting-xyz", agent_id="Agent2", title="Adopt New Logging Format", details="...")
# manifest = MeetingManifest(meeting_id="meeting-xyz", topic="Discuss Logging", creator_agent_id="Agent0")
