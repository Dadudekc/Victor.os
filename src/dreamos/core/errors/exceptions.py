"""Core exception types for the Dream.OS project."""


class DreamOSError(Exception):
    """Base class for all custom exceptions in Dream.OS."""

    def __init__(self, message: str, original_exception: Exception = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message

    def __str__(self):
        if self.original_exception:
            return f"{self.message}: {type(self.original_exception).__name__}: {self.original_exception}"  # noqa: E501
        return self.message


class ConfigurationError(DreamOSError):
    """Raised when there is an error related to configuration loading or validation."""

    pass


class AgentError(DreamOSError):
    """Base class for errors originating from agents."""

    pass


class TaskError(DreamOSError):
    """Base class for errors related to task processing."""

    pass


class ToolError(DreamOSError):
    """Base class for errors related to tool execution."""

    pass


class ProjectBoardError(DreamOSError):
    """Base class for errors related to Project Board Manager operations."""

    pass


class CoordinateError(DreamOSError):
    """Raised for errors related to coordinate handling or lookup."""

    pass


class TaskNotFoundError(ProjectBoardError):
    """Raised when a task ID is not found on the expected board."""

    pass


class TaskValidationError(ProjectBoardError):
    """Raised when task data fails validation."""

    pass


class BoardLockError(ProjectBoardError):
    """Raised when a file lock cannot be acquired."""

    pass


# --- Errors moved from core/errors.py during consolidation --- #

class CommunicationError(DreamOSError):
    """Indicates an error in inter-agent or system communication mechanisms."""
    pass

class MemoryError(DreamOSError):
    """Indicates an error related to an agent's memory component operations."""
    pass

# Note: BoardLockError above covers generic lock errors related to boards.
# If more general locking is needed, LockError/LockTimeoutError could be reinstated.
# class LockError(DreamOSError):
#     """Base class for errors related to file or resource locking mechanisms."""
#     pass
#
# class LockTimeoutError(LockError):
#     """Raised specifically when acquiring a resource lock times out."""
#     pass

class ValidationError(DreamOSError):
    """Indicates that data failed a validation check (general purpose)."""
    pass

class CursorOrchestratorError(DreamOSError):
    """Represents an error reported by the Cursor Orchestrator component."""
    pass

class ArchivingError(DreamOSError):
    """Indicates an error during archiving or unarchiving operations."""
    pass

# --- End moved errors --- #


# Add other common base exceptions as needed
