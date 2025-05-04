from enum import Enum


class AgentStatus(Enum):
    """Represents the possible operational statuses of an Agent."""

    UNKNOWN = "UNKNOWN"  # Status hasn't been determined yet
    STARTING = "STARTING"  # Agent is initializing
    IDLE = "IDLE"  # Agent is initialized and waiting for tasks
    BUSY = "BUSY"  # Agent is actively working on a task (can be refined later, e.g., WORKING, THINKING)  # noqa: E501
    BLOCKED = "BLOCKED"  # Agent is unable to proceed (e.g., waiting for external resource, dependency)  # noqa: E501
    ERROR = "ERROR"  # Agent encountered an unrecoverable error
    STOPPING = "STOPPING"  # Agent is shutting down gracefully
    SHUTDOWN_READY = (
        "SHUTDOWN_READY"  # Agent has finished shutdown tasks and is ready to terminate
    )
    TERMINATED = "TERMINATED"  # Agent process has ended


# Add other core coordination enums here as needed
