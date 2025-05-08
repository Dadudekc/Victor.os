"""Task management and processing components for DreamOS.

This package provides structures and mechanisms for defining, tracking,
and executing tasks within the DreamOS agent system.
"""

# Expose key components from this package.
from .nexus import (
    Task,
    TaskNexus,
    TaskOperationsHandler,
    DbTaskNexus,
    CapabilityHandler,
    CapabilityRegistry,
    AgentRegistryHandler,
    ShadowTaskNexus,
)
# Alternatively, could expose the nexus module itself:
# from . import nexus

__all__ = [
    "Task",
    "TaskNexus",
    "TaskOperationsHandler",
    "DbTaskNexus",
    "CapabilityHandler",
    "CapabilityRegistry",
    "AgentRegistryHandler",
    "ShadowTaskNexus",
    # "nexus", # if exposing the module
] 