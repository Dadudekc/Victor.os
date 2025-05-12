"""Message patterns for agent communication."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    """Task status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskMessage(BaseModel):
    """Task message model."""
    task_id: str
    task_type: str
    status: TaskStatus
    input_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None 