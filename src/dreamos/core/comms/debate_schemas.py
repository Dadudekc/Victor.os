# src/dreamos/core/comms/debate_schemas.py
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
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


# --- Debate Metadata (subset for agents, full in manifest) --- #


class DebateInfo(BaseModel):
    """Basic info about a debate."""

    debate_id: str
    topic: str
    status: Literal["open", "active", "paused", "closed", "archived"]
    protocol_id: Optional[str] = None


# --- Persona Schema --- #


class Persona(BaseModel):
    """Defines the role, stance, and instructions for an agent in a specific debate."""

    persona_id: str = Field(default_factory=generate_uuid)
    debate_id: str
    agent_id: str  # The agent assigned this persona
    role_name: str  # e.g., "Proponent", "Skeptic", "Data Analyst"
    stance_summary: str  # Brief description of viewpoint
    instructions: str  # Detailed instructions, potentially multi-line/markdown
    background_context: Optional[str] = None  # Supporting info provided
    created_at_utc: str = Field(default_factory=current_utc_iso)


# --- Argument Schema --- #


class ArgumentReference(BaseModel):
    """Reference cited in an argument."""

    type: Literal["message_id", "document", "url", "data_point"]
    value: str  # e.g., Message ID, file path, URL, query string
    description: Optional[str] = None


class Argument(BaseModel):
    """Represents a single contribution (argument) by an agent during a debate turn."""

    argument_id: str = Field(default_factory=generate_uuid)
    debate_id: str
    turn_number: int
    agent_id: str
    timestamp_utc: str = Field(default_factory=current_utc_iso)
    argument_text: str
    references: List[ArgumentReference] = Field(default_factory=list)
    reply_to_argument_id: Optional[str] = (
        None  # ID of argument being directly addressed
    )
    # Optional metadata
    confidence_score: Optional[float] = None
    detected_tone: Optional[str] = None


# --- Debate Manifest Schema (for manifest.json) --- #


class DebateParticipantInfo(BaseModel):
    agent_id: str
    role_name: str
    persona_id: str
    status: Literal["invited", "joined", "active_turn", "waiting", "left"] = "invited"


class DebateManifest(BaseModel):
    """Metadata stored in manifest.json for a debate arena."""

    debate_id: str
    topic: str
    proposal_ref: Optional[str] = (
        None  # Link to a specific proposal task/ID if applicable
    )
    creator_agent_id: str
    created_at_utc: str = Field(default_factory=current_utc_iso)
    last_updated_utc: str = Field(default_factory=current_utc_iso)
    current_status: Literal["open", "active", "paused", "closed", "archived"] = "open"
    protocol_id: str = "v1_simple_turn_based"  # ID or version of the protocol used
    moderator_agent_id: Optional[str] = None
    participants: List[DebateParticipantInfo] = Field(default_factory=list)
    current_turn: int = 0
    next_agent_id: Optional[str] = None  # Agent whose turn it is
    scoring_info: Optional[Dict[str, Any]] = (
        None  # Placeholder for scoring config/results
    )
    # TODO (Masterpiece Review - Captain-Agent-8): Define a specific Pydantic model
    #      for `scoring_info` if/when the scoring mechanism is implemented.


# Example Usage:
# persona_data = {
#     "debate_id": "debate-abc", "agent_id": "Agent3", "role_name": "Skeptic",
#     "stance_summary": "Question the feasibility and long-term costs.",
#     "instructions": "Focus on potential risks raised in document X. Use data points Y and Z."
# }
# persona = Persona(**persona_data)
#
# argument_data = {
#     "debate_id": "debate-abc", "turn_number": 2, "agent_id": "Agent3",
#     "argument_text": "While the proposal looks promising, the cost analysis ignores factor Z...",
#     "references": [{"type": "document", "value": "docs/analysis_X.md"}]
# }
# argument = Argument(**argument_data)
