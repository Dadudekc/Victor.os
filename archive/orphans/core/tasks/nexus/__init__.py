"""Implements the centralized Agent Capability Registry logic,
integrated within the Task Nexus."""

from . import asyncio
from . import capability_handler
from . import capability_registry
from . import collections
from . import comms.project_board
from . import datetime
from . import db_task_nexus
from . import dreamos.core.agents.capabilities.schema
from . import dreamos.core.coordination.agent_bus
from . import dreamos.core.coordination.event_payloads
from . import dreamos.core.coordination.event_types
from . import dreamos.core.db.sqlite_adapter
from . import dreamos.utils.project_root
from . import errors
from . import json
from . import logging
from . import pathlib
from . import pydantic
from . import threading
from . import time
from . import typing
from . import uuid


__all__ = [

    'AgentRegistryHandler',
    'CapabilityHandler',
    'CapabilityRegistry',
    'DbTaskNexus',
    'ShadowTaskNexus',
    'Task',
    'TaskDict',
    'TaskNexus',
    'TaskOperationsHandler',
    'add_task',
    'find_agents_for_capability',
    'find_capabilities',
    'get_agent_capabilities',
    'get_all_tasks',
    'get_capability',
    'get_next_task',
    'get_pending_tasks',
    'get_priority',
    'get_task_by_id',
    'get_tasks_by_tag',
    'list_tasks',
    'load_tasks',
    'register_capability',
    'stats',
    'unregister_capability',
    'update_capability_status',
    'update_task',
    'update_task_status',
    'validate_shadow_backlog',
]
