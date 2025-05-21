"""
Dream.OS - An Intelligent Operating System Framework
"""

from .agents.base import Agent
from .tasks.manager import TaskManager
from .communication.message_bus import MessageBus

__version__ = "0.1.0"
__author__ = "Dream.OS Team"
__email__ = "team@dreamos.ai"

__all__ = [
    "Agent",
    "TaskManager",
    "MessageBus"
] 