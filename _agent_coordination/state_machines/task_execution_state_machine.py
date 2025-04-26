# _agent_coordination/state_machines/task_execution_state_machine.py

import logging
from enum import Enum, auto
from typing import Optional, Dict, Any

logger = logging.getLogger("TaskExecutionStateMachine")


class TaskState(Enum):
    """Enumerated task lifecycle states."""
    QUEUED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


class TaskExecutionStateMachine:
    """State machine to manage task lifecycle."""
    def __init__(self, task_id: str, metadata: Optional[Dict[str, Any]] = None):
        self.task_id = task_id
        self.state = TaskState.QUEUED
        self.metadata = metadata or {}
        logger.debug(f"[{task_id}] Initialized with state {self.state.name}")

    def can_advance(self, new_state: TaskState) -> bool:
        """Validate if the transition is allowed."""
        valid_transitions = {
            TaskState.QUEUED: [TaskState.IN_PROGRESS, TaskState.FAILED],
            TaskState.IN_PROGRESS: [TaskState.COMPLETED, TaskState.FAILED],
            TaskState.COMPLETED: [],
            TaskState.FAILED: [],
        }
        return new_state in valid_transitions[self.state]

    def advance_state(self, new_state: TaskState) -> bool:
        """Attempt to transition to a new state."""
        if self.can_advance(new_state):
            logger.info(f"[{self.task_id}] Transitioning {self.state.name} → {new_state.name}")
            self.state = new_state
            return True
        else:
            logger.warning(f"[{self.task_id}] Invalid transition: {self.state.name} → {new_state.name}")
            return False

    def is_terminal(self) -> bool:
        """Returns whether the task has reached a final state."""
        return self.state in [TaskState.COMPLETED, TaskState.FAILED]

    def as_dict(self) -> Dict[str, Any]:
        """Return serializable representation of current state."""
        return {
            "task_id": self.task_id,
            "state": self.state.name,
            "metadata": self.metadata,
        } 
