# src/dreamos/core/identity/agent_identity.py
import logging
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class AgentIdentity(BaseModel):
    """Represents the persistent identity and metadata of an agent."""

    agent_id: str = Field(..., description="Unique identifier for the agent.")
    role: str = Field(
        default="GenericAgent", description="Primary role or function of the agent."
    )
    version: int = Field(
        default=1, description="Version number, incremented on changes."
    )
    registered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the agent was first registered.",
    )
    last_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the identity was last updated.",
    )

    @validator("registered_at", "last_updated_at", pre=True, always=True)
    def ensure_datetime_obj(cls, v):
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                logger.error(
                    f"Invalid datetime format for AgentIdentity: {v}. Using current UTC time."  # noqa: E501
                )
                return datetime.utcnow()
        elif isinstance(v, (int, float)):  # Handle potential timestamp floats/ints
            return datetime.utcfromtimestamp(v)
        elif isinstance(v, datetime):
            # Ensure timezone-aware (naive assumed UTC) - Pydantic v2 might handle this better  # noqa: E501
            if v.tzinfo is None:
                # This is a simplification; proper tz handling might be needed if non-UTC is possible  # noqa: E501
                return v  # Assuming UTC if naive
            return v
        logger.warning(
            f"Unexpected type for datetime field: {type(v)}. Using current UTC time."
        )
        return datetime.utcnow()  # Fallback

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
            self.last_updated_at = datetime.utcnow()
            logger.info(
                f"Agent identity {self.agent_id} updated to version {self.version}."
            )
        return updated

    class Config:
        validate_assignment = True  # Ensure validators run on attribute assignment
