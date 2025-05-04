"""Placeholder implementation for EventType enum."""

import logging
from enum import Enum

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Placeholder for core system event types."""
    # Add known/observed event types here
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed" # Example addition
    TASK_STARTED = "task.started" # Example addition
    AGENT_STATUS_CHANGE = "agent.status.change" # Example addition
    CURSOR_INJECT_REQUEST = "cursor.inject.request" # From agent 2 usage
    CURSOR_RETRIEVE_SUCCESS = "cursor.retrieve.success" # From agent 2 usage
    CURSOR_RETRIEVE_FAILURE = "cursor.retrieve.failure" # From agent 2 usage

    # Add others as discovered

    def __str__(self):
        return self.value

logger.warning("Using placeholder implementation for EventType.")
