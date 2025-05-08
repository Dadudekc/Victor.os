"""Custom error types for the DreamOS system.

This package defines and exposes custom exception classes used throughout DreamOS
to provide more specific error handling.
"""

# Makes the 'errors' directory a Python package

from .exceptions import (
    AgentError,
    ArchivingError,
    BoardLockError,
    CommunicationError,
    ConfigurationError,
    CoordinateError,
    CursorOrchestratorError,
    DreamOSError,
    MemoryError,
    ProjectBoardError,
    TaskError,
    TaskNotFoundError,
    TaskValidationError,
    ToolError,
    ValidationError,
)

__all__ = [
    "DreamOSError",
    "ConfigurationError",
    "AgentError",
    "TaskError",
    "ToolError",
    "ProjectBoardError",
    "CoordinateError",
    "TaskNotFoundError",
    "TaskValidationError",
    "BoardLockError",
    "CommunicationError",
    "MemoryError",
    "ValidationError",
    "CursorOrchestratorError",
    "ArchivingError",
]
