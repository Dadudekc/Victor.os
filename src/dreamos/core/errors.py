"""Core exception hierarchy for the Dream.OS Swarm Intelligence Framework.

This module defines the base exception `DreamOSError` and various subclasses
representing specific error conditions encountered within the system.
Using a custom hierarchy allows for more specific error handling and reporting.
"""


class DreamOSError(Exception):
    """Base class for all custom exceptions raised within the Dream.OS framework.

    Catching this exception allows handling of any error originating specifically
    from Dream.OS components, distinguishing them from standard Python errors
    or errors from external libraries.
    """

    pass


class ConfigurationError(DreamOSError):
    """Indicates an error related to system configuration.

    This could involve issues loading configuration files, missing required
    settings, or invalid configuration values.
    """

    pass


class ToolError(DreamOSError):
    """Indicates an error during the execution or interaction with an external tool.

    This is used when a command-line tool, API call, or other external dependency
    fails or returns an unexpected result.
    """

    pass


class CommunicationError(DreamOSError):
    """Indicates an error in inter-agent or system communication mechanisms.

    Examples include issues with the Agent Mailbox system, the AgentBus,
    or other message passing components.
    """

    pass


class MemoryError(DreamOSError):
    """Indicates an error related to an agent's memory component operations.

    This could involve failures in reading from, writing to, or managing
    the agent's short-term or long-term memory stores.
    """

    pass


class TaskBoardError(DreamOSError):
    """Indicates a conceptual or data integrity issue with a Task Board.

    This is distinct from file I/O errors (covered by `ProjectBoardError`)
    and relates more to the structure, content, or state transitions of tasks
    on the board (e.g., invalid status update, missing required field).
    """

    pass


class LockError(DreamOSError):
    """Base class for errors related to file or resource locking mechanisms."""

    pass


class LockTimeoutError(LockError):
    """Raised specifically when acquiring a resource lock times out."""

    pass


class ValidationError(DreamOSError):
    """Indicates that data failed a validation check.

    Used when input data, configuration, or internal state does not conform
    to expected rules or constraints.
    """

    pass


class ProjectBoardError(DreamOSError):
    """Indicates an operational error within the ProjectBoardManager.

    This typically relates to file system operations like reading/writing
    board files, handling file locks specifically for the board manager,
    or JSON parsing errors related to board data.
    """

    pass


class CursorOrchestratorError(DreamOSError):
    """Represents an error reported by the Cursor Orchestrator component.

    Used to wrap or signify errors originating from interactions with the
    primary orchestrator controlling the agent's execution within the IDE.
    """

    pass


class CoordinateError(DreamOSError):
    """Indicates an error related to parsing or handling file coordinates.

    Used when coordinate strings are malformed, cannot be resolved to actual
    file locations, or are otherwise invalid.
    """

    pass


class ArchivingError(DreamOSError):
    """Indicates an error during archiving or unarchiving operations.

    Used for failures related to creating, reading, or managing archive files
    (e.g., zip, tar) used within the system.
    """

    pass


# Add other common base errors as needed
