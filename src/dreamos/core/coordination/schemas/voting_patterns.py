"""Defines message schemas (using Pydantic) for the agent voting sub-protocol."""

from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel, Field

# --- Message Schemas (Using Pydantic) ---


class VoteQuestion(BaseModel):
    """Structure for a single question within a vote."""

    id: str = Field(
        ..., description="Unique identifier for the question within the vote"
    )
    text: str = Field(..., description="The text of the question presented to agents")


class VoteInitiated(BaseModel):
    """Message schema published to initiate an agent vote."""

    vote_id: str = Field(
        ..., description="Unique identifier for this specific voting instance"
    )
    description: str = Field(
        ..., description="Brief description of what is being voted on"
    )
    questions: List[VoteQuestion] = Field(default_factory=list)
    response_format_notes: Optional[str] = Field(
        None, description="Hints on how choices should be structured"
    )
    voting_deadline_utc: Optional[str] = Field(
        None, description="Optional deadline in ISO 8601 format"
    )


# Define a flexible type for choices
VoteChoice = Union[str, Sequence[str]]


class AgentVote(BaseModel):
    """Message schema published by an agent casting its vote."""

    vote_id: str = Field(
        ..., description="Must match the vote_id from the VoteInitiated message"
    )
    agent_id: str = Field(..., description="Identifier of the agent casting the vote")
    timestamp_utc: str = Field(
        ..., description="ISO 8601 format timestamp of when the vote was cast"
    )
    choices: List[VoteChoice] = Field(default_factory=list)
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Optional: Agent's confidence (0.0 to 1.0)"
    )
    rationale: Optional[str] = Field(None, description="Optional: Brief justification")


# VoteResultsSummary remains a placeholder concept; structure depends on tally logic
# If used directly, it would also become a dataclass.
# @dataclass
# class VoteResultsSummary:
#    ... Example fields ...
#    pass


class VoteResults(BaseModel):
    """Message schema published by the coordinator with the outcome of a vote."""

    vote_id: str = Field(
        ..., description="Must match the vote_id from the VoteInitiated message"
    )
    results_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Tally results"
    )
    participating_agents: List[str] = Field(default_factory=list)
    outcome: str = Field(
        ..., description="The final decision or outcome based on the tally logic"
    )
    tally_timestamp_utc: str = Field(..., description="ISO 8601 format timestamp")
