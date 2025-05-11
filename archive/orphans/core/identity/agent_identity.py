# src/dreamos/core/identity/agent_identity.py
import logging
import re  # Added for regex validation
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class AgentIdentity(BaseModel):
    """Represents the persistent identity and metadata of an agent."""

    agent_id: str = Field(..., description="Unique identifier for the agent.")
    # TODO (Masterpiece Review - Captain-Agent-8): Enforce consistent agent_id format
    #      (e.g., using regex validation or aligning with system-wide UUID standard).
    #      Partial step: Added basic non-empty and character check.
    role: str = Field(
        default="GenericAgent", description="Primary role or function of the agent."
    )
    version: int = Field(
        default=1, description="Version number, incremented on changes."
    )
    # TODO (Masterpiece Review - Captain-Agent-8): Use explicit timezone-aware datetimes.
    #      Replace `datetime.utcnow` with `lambda: datetime.now(timezone.utc)`
    #      and refine validator for stricter timezone handling. (DONE - lambda added below)
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),  # Use timezone.utc
        description="Timestamp when the agent was first registered.",
    )
    last_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),  # Use timezone.utc
        description="Timestamp when the identity was last updated.",
    )

    @validator("agent_id")
    def validate_agent_id_format(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("agent_id must be a non-empty string")
        # Example for a more specific format (e.g., alphanumeric, dashes, underscores)
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            logger.warning(
                f"Agent ID '{v}' contains potentially unusual characters. Recommended: alphanumeric, dash, underscore, dot."
            )
        # If a strict UUID format were required:
        # try:
        #     uuid.UUID(v)
        # except ValueError:
        #     raise ValueError("agent_id must be a valid UUID string")
        return v

    @validator("registered_at", "last_updated_at", pre=True, always=True)
    def ensure_datetime_obj(cls, v):
        if isinstance(v, str):
            try:
                # Ensure parsing results in an aware object, assuming UTC if offset missing
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                logger.error(
                    f"Invalid datetime format for AgentIdentity: {v}. Using current UTC time."  # noqa: E501
                )
                return datetime.now(timezone.utc)
        elif isinstance(v, (int, float)):  # Handle potential timestamp floats/ints
            # Ensure conversion results in an aware UTC datetime
            return datetime.fromtimestamp(v, tz=timezone.utc)
        elif isinstance(v, datetime):
            # Ensure timezone-aware (naive assumed UTC) - Pydantic v2 might handle this better  # noqa: E501
            if v.tzinfo is None:
                # Assign UTC if naive
                return v.replace(tzinfo=timezone.utc)
            return v  # Already aware
        logger.warning(
            f"Unexpected type for datetime field: {type(v)}. Using current UTC time."
        )
        return datetime.now(timezone.utc)  # Use timezone.utc fallback

    def update(self, updates: Dict[str, Any]):
        """Updates the identity fields, increments version, and sets last_updated_at."""
        updated = False
        for key, value in updates.items():
            if hasattr(self, key) and key not in {
                "agent_id",
                "version",
                "registered_at",
                "last_updated_at",
            }:
                current_value = getattr(self, key)
                if current_value != value:
                    setattr(self, key, value)
                    updated = True
        if updated:
            self.version += 1
            self.last_updated_at = datetime.now(timezone.utc)
            logger.info(
                f"Agent identity {self.agent_id} updated to version {self.version}."
            )
        return updated

    class Config:
        validate_assignment = True  # Ensure validators run on attribute assignment
