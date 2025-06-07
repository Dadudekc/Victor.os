"""Configuration model for task monitoring settings."""

from pydantic import BaseModel, Field


class TaskMonitoringConfig(BaseModel):
    """Settings for monitoring task progress and detecting stalls."""

    check_interval_seconds: int = Field(
        300, description="How often to check for stalled tasks"
    )
    pending_timeout_seconds: int = Field(
        3600, description="Time in seconds before a PENDING task is considered stalled"
    )
    escalation_strategy: str = Field(
        "log_only", description="Strategy for handling stalled tasks"
    )
