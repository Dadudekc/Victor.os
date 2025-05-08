# AUTO-GENERATED __init__.py
# DO NOT EDIT MANUALLY - changes may be overwritten

from . import (
    exceptions,  # Keep this if other modules expect to access dreamos.core.errors.exceptions directly
)

# Re-export key exceptions for easier access
from .exceptions import (
    AgentError,
    ArchivingError,
    CommunicationError,
    ConfigurationError,
    CoordinateError,
    CursorOrchestratorError,
    DreamOSError,
    MemoryError,
    ProjectBoardError,
    TaskError,
    ToolError,
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
    "CoordinateError",
    "CommunicationError",
    "MemoryError",
    "ValidationError",
    "CursorOrchestratorError",
    "ArchivingError",
]
