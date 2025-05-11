"""Provides structured JSONL logging for swarm agent events.

This module defines `log_agent_event` for recording agent activities
to a configured log file (typically `agent_activity_log.jsonl`).
It uses file locking to ensure safe concurrent writes from multiple agents
or processes and relies on AppConfig for log path configuration."""

from . import dreamos.core.config
from . import dreamos.utils.common_utils
from . import dreamos.utils.file_locking
from . import json
from . import logging
from . import pathlib
from . import typing


__all__ = [

    'log_agent_event',
]
