"""Defines standardized Pydantic models for AgentBus event payloads."""

import uuid  # Added for alert_id default
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums import AgentStatus
from .message_patterns import (  # Assuming TaskStatus is defined here or importable
    TaskStatus,
)

# Keep BaseEvent simple for now, focus on specific payload data classes


class ErrorEventPayload(BaseModel):
    """Unified payload for system or agent-specific error events. Replaces SystemAgentErrorPayload and AgentErrorPayload."""  # noqa: E501

    error_message: str
    agent_id: Optional[str] = (
        None  # Agent reporting or involved in the error, if applicable
    )
    task_id: Optional[str] = None  # Task associated with the error, if applicable
    exception_type: Optional[str] = None  # e.g., 'ValueError', 'FileNotFoundError'
    traceback: Optional[str] = None
    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict
    )  # Combined context/details


class AgentStatusEventPayload(BaseModel):
    """Unified payload for various agent status update events. Replaces AgentStatusChangePayload and AgentStatusPayload."""  # noqa: E501

    agent_id: str
    status: AgentStatus
    task_id: Optional[str] = (
        None  # Relevant if status change is task-related (e.g., BUSY, BLOCKED by task)
    )
    details: Optional[str] = None  # General details about the status change
    error_message: Optional[str] = None  # Specifically if status is ERROR
    capabilities: Optional[List[str]] = (
        None  # Relevant for STARTED, potentially UPDATE events
    )

    class Config:
        use_enum_values = True


class AgentRegistrationPayload(BaseModel):
    """Payload for SYSTEM_AGENT_REGISTERED / UNREGISTERED events."""

    agent_id: str
    capabilities: Optional[List[str]] = None  # Only for REGISTERED


class TaskEventPayload(BaseModel):
    """Base payload for Task Lifecycle events. Contains only common fields."""

    task_id: str
    status: TaskStatus  # Use TaskStatus Enum
    # REMOVED: details, result, error, progress - Defined in subclasses

    class Config:
        use_enum_values = True


class TaskProgressPayload(TaskEventPayload):
    """Payload for TASK_PROGRESS events."""

    progress: float = Field(
        ..., ge=0.0, le=1.0, description="Task progress percentage (0.0 to 1.0)"
    )
    details: Optional[str] = Field(
        None, description="Optional details about the progress"
    )


class TaskCompletionPayload(TaskEventPayload):
    """Payload for TASK_COMPLETED events."""

    result: Optional[Dict[str, Any]] = Field(default_factory=dict)
    details: Optional[str] = Field(
        None, description="Optional completion summary/details"
    )  # Add details here if needed


class TaskFailurePayload(TaskEventPayload):
    """Payload for TASK_FAILED events."""

    error: str
    is_final: bool = False  # Indicates if this is a final failure state for the task
    details: Optional[str] = Field(
        None, description="Optional details about the failure"
    )  # Add details here if needed


# Example Tool Payloads (can be expanded)
class ToolCallPayload(BaseModel):
    """Payload for TOOL_CALL events."""

    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str  # Agent making the call
    correlation_id: Optional[str] = None  # Link to originating task/request


class ToolResultPayload(BaseModel):
    """Payload for TOOL_RESULT events."""

    tool_name: str
    status: str  # e.g., "SUCCESS", "FAILURE", "ERROR"
    result: Optional[Any] = None  # Can be complex, JSON-serializable recommended
    error_message: Optional[str] = None
    agent_id: str  # Agent that made the call
    correlation_id: Optional[str] = None  # Link back to ToolCall or originating task


# REMOVED TODO about moving MemoryEventData
# MemoryEventData definition remains here as it's part of the event contract.


# Moved from agent_bus.py
class MemoryEventData(BaseModel):
    agent_id: str  # Agent performing the operation
    operation: str  # e.g., 'set', 'get', 'delete', 'query'
    key_or_query: str  # The key accessed or the query performed
    status: str  # 'SUCCESS' or 'FAILURE'
    message: Optional[str] = None  # Optional details or error message
    # Avoid including the actual 'value' by default to keep events light
    # value: Optional[Any] = None


# Add more specific payloads as needed, e.g., for Cursor events
class CursorInjectRequestPayload(BaseModel):
    """Payload for when a prompt injection is requested for a specific agent."""

    agent_id: str = Field(..., description="The target agent ID for the injection.")
    prompt: str = Field(..., description="The prompt text to be injected.")
    # Optionally include correlation_id if it should be part of the core payload
    # correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # Simple dict conversion, handle potential Pydantic v1/v2 differences
        if hasattr(self, "model_dump"):
            return self.model_dump(mode="json")  # Pydantic v2
        else:
            return self.dict()  # Pydantic v1


class CursorRetrieveRequestPayload(BaseModel):
    target_file: Optional[str] = None  # If retrieving from file context
    retrieval_type: str = "clipboard"  # or "selection", "file_context"
    correlation_id: str


class CursorResultPayload(BaseModel):  # For SUCCESS/FAILURE of inject/retrieve
    operation: str  # "inject" or "retrieve"
    status: str  # "SUCCESS" or "FAILURE"
    message: Optional[str] = None  # Error message on failure
    retrieved_content: Optional[str] = None  # On retrieve success
    correlation_id: str


class AgentContractStatusPayload(BaseModel):
    """Payload for AGENT_CONTRACT_STATUS event (response to query)."""

    agent_id: str
    version: str  # Agent version
    operational_status: str  # Could use AgentStatus enum later if appropriate
    compliance_status: str  # e.g., Compliant, NonCompliant, Unknown
    capabilities: List[str]
    last_checked_utc: str  # ISO format timestamp
    # Add other relevant contract fields as needed
    # e.g., resource_usage: Optional[Dict] = None
    # e.g., active_policies: Optional[List[str]] = None


class RouteInjectPayload(BaseModel):
    """Payload for ROUTE_INJECTION_REQUEST event."""

    correlation_id: str
    original_source_id: str
    prompt_text: str
    context_metadata: Dict[str, Any] = Field(default_factory=dict)


class CursorEventPayload(BaseModel):
    """Standard payload for Cursor Interaction events (CURSOR_*)."""

    target_agent_id: str
    reason: Optional[str] = None
    response_length: Optional[int] = None
    prompt_text: Optional[str] = None
    correlation_id: Optional[str] = None


class ScrapedDataPayload(BaseModel):
    """Payload for CHATGPT_RESPONSE_SCRAPED event."""

    correlation_id: str
    content: str
    source_url: Optional[str] = None
    context_metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovalRequestPayload(BaseModel):
    """Payload for SUPERVISOR_APPROVAL_REQUESTED event."""

    request_id: str
    agent_id: str
    command: str
    explanation: str


class ApprovalResponsePayload(BaseModel):
    """Payload for SUPERVISOR_APPROVAL_RESPONSE event."""

    request_id: str
    approved: bool
    reason: Optional[str] = None
    modified_command: Optional[str] = None


# Added Supervisor Alert Payload
class SupervisorAlertPayload(BaseModel):
    alert_id: str = Field(default_factory=lambda: f"alert_{uuid.uuid4().hex[:12]}")
    severity: str = Field(
        "INFO", description="Severity level (e.g., INFO, WARNING, ERROR, CRITICAL)"
    )
    source_agent_id: str
    blocking_task_id: Optional[str] = (
        None  # ID of the specific task blocked, if applicable
    )
    blocker_summary: str  # Max ~100 chars recommended. E.g., "Missing core file: X", "Tool Y failed: Z"  # noqa: E501
    details_reference: Optional[str] = (
        None  # Relative path to detailed log/message file, if available
    )
    status: str = "NEW"  # Status values: NEW, ACKNOWLEDGED, RESOLVING, RESOLVED
    # Timestamp is part of the parent BaseEvent


# Keep __all__ minimal for now, let users import directly
# __all__ = [
#    "SystemAgentErrorPayload",
#    "AgentStatusChangePayload",
#    # ... etc
# ]


# {{ EDIT START: Add payload for validation failure }}
class TaskValidationFailedPayload(TaskEventPayload):
    details: Optional[str] = Field(
        None, description="Details about why validation failed"
    )
    # Consider adding fields like: validation_results: Dict[str, Any] = None


# {{ EDIT END }}


# EDIT START: Add Payloads for Capability Registry Events
class CapabilityRegisteredPayload(BaseModel):
    """Payload for SYSTEM_CAPABILITY_REGISTERED event."""

    capability_data: Dict[str, Any]  # Serialized AgentCapability.to_dict()


class CapabilityUnregisteredPayload(BaseModel):
    """Payload for SYSTEM_CAPABILITY_UNREGISTERED event."""

    agent_id: str
    capability_id: str


# EDIT END
