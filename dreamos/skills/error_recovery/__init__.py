"""
Dream.OS Error Recovery Utilities

This module provides utilities for error classification, recovery, and handling
to support resilient agent operations.
"""

# Placeholder imports for structures we expect Agent-6 to implement
# These will be implemented by Agent-6 but providing the interface now
# allows us to begin working on the integration

from .errors import ErrorType, classify_error
from .recovery import recover_from_error
from .logging import log_error

__all__ = [
    'ErrorType',
    'classify_error',
    'recover_from_error',
    'log_error',
] 