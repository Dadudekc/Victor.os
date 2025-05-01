# Makes the 'errors' directory a Python package

from .exceptions import (
    AgentError,
    BoardLockError,
    ConfigurationError,
    CoordinateError,
    DreamOSError,
    ProjectBoardError,
    TaskError,
    TaskNotFoundError,
    TaskValidationError,
    ToolError,
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
]
