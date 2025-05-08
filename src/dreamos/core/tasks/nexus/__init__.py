"""Core task nexus functionalities for DreamOS.

This sub-package contains the central logic for task distribution,
capability management, and agent coordination related to tasks.
"""

# Expose key components from this package.
from .agent_registry_handler import AgentRegistryHandler
from .capability_handler import CapabilityHandler
from .capability_registry import CapabilityRegistry
from .db_task_nexus import DbTaskNexus
from .shadow_task_nexus import ShadowTaskNexus
from .task_nexus import Task, TaskNexus
from .task_operations import TaskOperationsHandler

__all__ = [
    "Task",
    "TaskNexus",
    "TaskOperationsHandler",
    "DbTaskNexus",
    "CapabilityHandler",
    "CapabilityRegistry",
    "AgentRegistryHandler",
    "ShadowTaskNexus",
]
