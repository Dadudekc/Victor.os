# EDIT START: Restored from archive/orphans/src/dreamos/core/errors.py to resolve config.py import error
class ConfigurationError(Exception):
    """Raised when there is a problem with required configuration."""
    pass

# Optional alias for legacy imports
CoreConfigurationError = ConfigurationError

# EDIT START: Add DreamOSError and ToolError for tool execution error handling, as required by orchestrator and project context
class DreamOSError(Exception):
    """Base class for Dream.OS-related errors."""
    pass

class ToolError(DreamOSError):
    """Base class for errors related to tool execution."""
    pass
# EDIT END 