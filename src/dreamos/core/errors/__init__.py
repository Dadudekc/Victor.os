# AUTO-GENERATED __init__.py
# DO NOT EDIT MANUALLY - changes may be overwritten

from . import (
    exceptions,  # Keep this if other modules expect to access dreamos.core.errors.exceptions directly
)

# Re-export key exceptions for easier access
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
    ToolError,
    TaskNotFoundError,
    TaskValidationError,
    TaskProcessingError,
    MessageHandlingError,
    ValidationError,
)

__all__ = [
    "exceptions",  # Keep if needed
    "DreamOSError",
    "ConfigurationError",
    "AgentError",
    "TaskError",
    "ToolError",
    "ProjectBoardError",
    "TaskNotFoundError",
    "TaskValidationError",
    "TaskProcessingError",
    "CoordinateError",
    "CommunicationError",
    "MemoryError",
    "MessageHandlingError",
    "ValidationError",
    "CursorOrchestratorError",
    "ArchivingError",
    "BoardLockError",
]
