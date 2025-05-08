"""Logging facilities for DreamOS core components and agents.

This package provides structured logging capabilities, particularly for agent
activities within the swarm. It aims to ensure safe concurrent log writing.

Currently, it exposes:
- `log_agent_event`: For recording detailed agent activities.
"""

from .swarm_logger import log_agent_event

__all__ = [
    "log_agent_event",
] 