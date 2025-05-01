"""Standardized message patterns for agent coordination."""

from dataclasses import dataclass, field
from datetime import datetime, timezone  # Ensure timezone awareness
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (  # Import necessary Pydantic components
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

# REMOVED addressed TODO


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    CLAIMED = "claimed"  # Optional: If tasks need explicit claiming
    WORKING = "working"  # Agent actively processing
    COMPLETED = "completed"
    COMPLETED_VERIFIED = (
        "completed_verified"  # Handler finished, self-validation passed
    )
    VALIDATION_FAILED = "validation_failed"  # Handler finished, self-validation failed
    FAILED = "failed"
    CANCELLED = "cancelled"
    PERMANENTLY_FAILED = "permanently_failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    BACKGROUND = "background"


# @dataclass <-- Remove dataclass decorator
class TaskMessage(BaseModel):  # <-- Inherit from BaseModel
    """Standard task message format, used as the 'data' field in AgentBus messages."""

    task_id: str
    agent_id: str  # Target agent ID
    task_type: str  # The specific action/command requested
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    source_agent_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    score: Optional[Dict[str, Any]] = None
    retry_count: int = 0

    # --- Add Pydantic model configuration if needed (e.g., for enum serialization) ---
    class Config:
        use_enum_values = True  # Serialize enums to their values
        # Add other config options if necessary, e.g., arbitrary_types_allowed=True


def create_task_message(
    task_type: str,
    agent_id: str,  # Target agent
    input_data: Dict[str, Any],
    source_agent_id: Optional[str] = None,  # Source agent
    priority: TaskPriority = TaskPriority.NORMAL,
    parent_task_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TaskMessage:
    """Helper function to create a new TaskMessage instance with defaults."""
    from uuid import uuid4

    # Generate default correlation ID if not provided
    effective_correlation_id = correlation_id or f"corr_{uuid4().hex[:8]}"

    return TaskMessage(
        task_id=f"task_{uuid4().hex}",  # Generate a unique task ID
        agent_id=agent_id,
        task_type=task_type,
        priority=priority,
        status=TaskStatus.PENDING,
        input_data=input_data,
        correlation_id=effective_correlation_id,
        source_agent_id=source_agent_id,
        parent_task_id=parent_task_id,
        subtasks=[],
        metadata=metadata or {},
        started_at=None,
        completed_at=None,
        score=None,
        retry_count=0,
    )


def update_task_status(
    task: TaskMessage,
    new_status: TaskStatus,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    subtasks: Optional[List[str]] = None,
) -> TaskMessage:
    """Update task status and related fields, returning the modified task."""
    if not isinstance(task, TaskMessage):
        raise TypeError("Input 'task' must be a TaskMessage instance")

    task.status = new_status
    task.updated_at = datetime.now(timezone.utc)  # Use timezone aware now

    if result is not None:
        task.result = result
        task.error = None  # Clear error if setting result
    if error is not None:
        task.error = error
        task.result = None  # Clear result if setting error
    if subtasks is not None:
        task.subtasks = subtasks

    return task
