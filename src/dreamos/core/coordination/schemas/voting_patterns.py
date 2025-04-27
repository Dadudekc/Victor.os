"""Defines message schemas and constants for the agent voting sub-protocol."""

from typing import TypedDict, List, Dict, Any, Literal, Optional, Union, Sequence

# --- Event Type Constants ---

VOTE_INITIATED: Literal["VOTE_INITIATED"] = "VOTE_INITIATED"
AGENT_VOTE: Literal["AGENT_VOTE"] = "AGENT_VOTE"
VOTE_RESULTS: Literal["VOTE_RESULTS"] = "VOTE_RESULTS"

# --- Message Schemas ---

class VoteQuestion(TypedDict):
    """Structure for a single question within a vote."""
    id: str # Unique identifier for the question within the vote
    text: str # The text of the question presented to agents

class VoteInitiated(TypedDict):
    """Message schema published to initiate an agent vote."""
    type: Literal["VOTE_INITIATED"] # Matches VOTE_INITIATED constant
    vote_id: str # Unique identifier for this specific voting instance
    description: str # Brief description of what is being voted on
    questions: List[VoteQuestion] # List of questions agents need to answer
    response_format_notes: Optional[str] # Hints on how choices should be structured
    voting_deadline_utc: Optional[str] # Optional deadline in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)

# Define a flexible type for choices, as they might be single strings or lists (for multi-part answers)
VoteChoice = Union[str, Sequence[str]]

class AgentVote(TypedDict):
    """Message schema published by an agent casting its vote."""
    type: Literal["AGENT_VOTE"] # Matches AGENT_VOTE constant
    vote_id: str # Must match the vote_id from the VoteInitiated message
    agent_id: str # Identifier of the agent casting the vote
    timestamp_utc: str # ISO 8601 format timestamp of when the vote was cast
    choices: List[VoteChoice] # List of choices corresponding to the order of questions in VoteInitiated
    confidence: Optional[float] # Optional: Agent's confidence in its vote (e.g., 0.0 to 1.0)
    rationale: Optional[str] # Optional: Brief justification for the vote

class VoteResultsSummary(TypedDict):
    """Structure holding the tallied results for a vote (adapt structure as needed)."""
    # Example structure - this will vary significantly based on vote type
    # Keys should ideally match question IDs or be descriptive
    q1_counts: Dict[str, int] # e.g., {"counts_only": 5, "include_breach": 1}
    q2a_autoscroll_counts: Dict[str, int]
    q2b_override_counts: Dict[str, int]
    q3_colors_counts: Dict[str, int]
    q4_frequency_counts: Dict[str, int]
    # Add other fields as needed, like raw vote counts per agent, etc.
    pass # Use pass for now, specific tally structure depends on implementation

class VoteResults(TypedDict):
    """Message schema published by the coordinator with the outcome of a vote."""
    type: Literal["VOTE_RESULTS"] # Matches VOTE_RESULTS constant
    vote_id: str # Must match the vote_id from the VoteInitiated message
    results_summary: Dict[str, Any] # Dictionary containing tallied results (structure depends on tally logic)
    participating_agents: List[str] # List of agent IDs that submitted a valid vote
    outcome: str # The final decision or outcome based on the tally logic
    tally_timestamp_utc: str # ISO 8601 format timestamp of when the results were tallied

# --- Optional Validation Stub ---

def validate_vote_message(message: Dict[str, Any]) -> bool:
    """Basic validation stub for incoming vote-related messages (can be expanded)."""
    msg_type = message.get("type")
    if msg_type == VOTE_INITIATED:
        # Check required fields for VoteInitiated
        return all(k in message for k in ["vote_id", "description", "questions"])
    elif msg_type == AGENT_VOTE:
        # Check required fields for AgentVote
        return all(k in message for k in ["vote_id", "agent_id", "timestamp_utc", "choices"])
    elif msg_type == VOTE_RESULTS:
        # Check required fields for VoteResults
        return all(k in message for k in ["vote_id", "results_summary", "participating_agents", "outcome", "tally_timestamp_utc"])
    else:
        # Unknown message type
        return False 