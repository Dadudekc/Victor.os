"""Core utility modules for Dream.os.

This package contains consolidated utilities used across the system.
All utility functions should be placed here to avoid duplication.
"""

from .file_utils import FileManager
from .logging_utils import setup_logging
from .validation_utils import ValidationLogger # Restored placeholder
from .task_utils import TaskCompletionDetector # Restored placeholder
from .common_utils import (
    get_utc_iso_timestamp,
    validate_iso_timestamp,
    parse_iso_timestamp
)
from .config_utils import ConfigManager
from .agent_utils import AgentMonitor, CommandSupervisor # Restored placeholder
# CacheProvider related imports are not typically in __init__.py unless re-exported for direct use
from .cache_provider import CacheProvider, InMemoryCacheProvider, CacheStats 

__all__ = [
    # File and logging
    "FileManager",
    "setup_logging",
    
    # Task and validation
    "ValidationLogger",
    "TaskCompletionDetector",
    
    # Common utilities
    "get_utc_iso_timestamp",
    "validate_iso_timestamp",
    "parse_iso_timestamp",
    
    # Configuration
    "ConfigManager",
    "CacheProvider", # Added as it's a core abstraction now
    "InMemoryCacheProvider", # Added as it's a concrete implementation
    "CacheStats", # Added as it's a related data structure
    
    # Agent utilities
    "AgentMonitor",
    "CommandSupervisor"
] 