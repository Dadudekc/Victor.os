"""THEA Response Schema
====================

Defines the contract for THEA (ChatGPT) responses in the bridge system.
Provides validation and type checking for response objects.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union


class ResponseType(Enum):
    """Types of responses that THEA can return."""

    TASK_COMPLETE = "task_complete"
    TASK_ERROR = "task_error"
    TASK_IN_PROGRESS = "task_in_progress"
    ESCALATION_NEEDED = "escalation_needed"
    INVALID_INPUT = "invalid_input"


class ResponseStatus(Enum):
    """Status codes for THEA responses."""

    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    ESCALATED = "escalated"


@dataclass
class TheaResponse:
    """Schema for THEA responses."""

    type: ResponseType
    task_id: str
    status: ResponseStatus
    response: str
    next_steps: Optional[List[str]] = None
    source_chat_id: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    metadata: Optional[Dict[str, Union[str, int, float, bool]]] = None

    def to_dict(self) -> dict:
        """Convert response to dictionary format."""
        return {
            "type": self.type.value,
            "task_id": self.task_id,
            "status": self.status.value,
            "response": self.response,
            "next_steps": self.next_steps,
            "source_chat_id": self.source_chat_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert response to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "TheaResponse":
        """Create response from dictionary."""
        return cls(
            type=ResponseType(data["type"]),
            task_id=data["task_id"],
            status=ResponseStatus(data["status"]),
            response=data["response"],
            next_steps=data.get("next_steps"),
            source_chat_id=data.get("source_chat_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TheaResponse":
        """Create response from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def validate(self) -> bool:
        """Validate the response object."""
        try:
            # Check required fields
            if not all([self.type, self.task_id, self.status, self.response]):
                return False

            # Validate enums
            if not isinstance(self.type, ResponseType):
                return False
            if not isinstance(self.status, ResponseStatus):
                return False

            # Validate optional fields if present
            if self.next_steps and not isinstance(self.next_steps, list):
                return False
            if self.source_chat_id and not isinstance(self.source_chat_id, str):
                return False
            if self.metadata and not isinstance(self.metadata, dict):
                return False

            return True
        except Exception:
            return False


def load_schema() -> dict:
    """Load the JSON schema for validation."""
    schema_path = Path(__file__).parent / "thea_response_schema.json"
    if not schema_path.exists():
        # Create default schema if it doesn't exist
        schema = {
            "type": "object",
            "required": ["type", "task_id", "status", "response"],
            "properties": {
                "type": {"type": "string", "enum": [t.value for t in ResponseType]},
                "task_id": {"type": "string"},
                "status": {"type": "string", "enum": [s.value for s in ResponseStatus]},
                "response": {"type": "string"},
                "next_steps": {"type": "array", "items": {"type": "string"}},
                "source_chat_id": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "metadata": {"type": "object"},
            },
        }
        schema_path.write_text(json.dumps(schema, indent=2))
    return json.loads(schema_path.read_text())
