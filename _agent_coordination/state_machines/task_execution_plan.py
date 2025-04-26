"""
Defines TaskExecutionPlan and TaskStep for agent coordination.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class TaskStep:
    """
    A single step in a TaskExecutionPlan.
    """
    action: str
    element: Optional[str] = None
    timeout: float = 0.0
    required: bool = False
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskExecutionPlan:
    """
    Represents a sequence of TaskStep objects to execute a CursorGoal.
    """
    task_id: str
    steps: List[TaskStep]
