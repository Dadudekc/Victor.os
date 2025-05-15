"""
Core coordination package for Dream.OS.

This package provides centralized coordination mechanisms for agent communication,
task management, and system-wide orchestration.
"""

__version__ = '1.0.0'

from .agent_bus import AgentBus
from .base_agent import BaseAgent
from .project_board_manager import ProjectBoardManager
from .event_types import EventType
from .event_payloads import EventPayload
from .message_patterns import MessagePattern
from .enums import *

__all__ = [
    'AgentBus',
    'BaseAgent', 
    'ProjectBoardManager',
    'EventType',
    'EventPayload',
    'MessagePattern'
] 