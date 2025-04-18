import json
import logging
import os
# Removed portalocker as file fallback is removed
# import portalocker
import time
from typing import Optional, Dict, Any, Literal

# Canonical imports
from ..coordination.agent_bus import AgentBus # Assuming AgentBus is in core.coordination
from ..coordination.dispatcher import Event, EventType # Assuming dispatcher is in core.coordination
# Removed Message import
# from ..agent_bus import AgentBus, Message

logger = logging.getLogger(__name__)

# Target agent responsible for processing final task status updates
DEFAULT_UPDATE_TARGET = "TaskExecutorAgent"
# Removed MSG_TYPE_TASK_UPDATE constant

class TaskStatusUpdater:
    """Handles dispatching task status update events (TASK_COMPLETED, TASK_FAILED) via AgentBus."""

    def __init__(self, agent_bus: AgentBus):
        """
        Initializes the updater.

        Args:
            agent_bus: The AgentBus instance. Required for dispatching events.
        """
        if agent_bus is None:
            # In this refactored version, the bus is essential.
            raise ValueError("AgentBus instance is required for TaskStatusUpdater.")

        self.agent_bus = agent_bus
        # Removed task_list_path and lock as file writing is removed
        # self.task_list_path = task_list_path
        # self.lock = lock
        self.agent_name = "TaskStatusUpdaterUtil" # Name for logging/attribution if needed

    def update_task_status(
        self,
        task_id: str,
        status: Literal["COMPLETED", "FAILED"], # Status determines EventType
        result_summary: Optional[str] = None,
        error_details: Optional[str] = None,
        originating_agent: Optional[str] = None # Agent reporting the status
    ) -> bool:
        """
        Dispatches a TASK_COMPLETED or TASK_FAILED event via the AgentBus.

        Args:
            task_id: The ID of the task being updated (used as correlation_id).
            status: The final status ('COMPLETED' or 'FAILED').
            result_summary: A brief summary of the result (for COMPLETED).
            error_details: Details about the failure (for FAILED).
            originating_agent: The name of the agent reporting this status update.

        Returns:
            True if the event was successfully dispatched, False otherwise.
        """
        logger.info(f"Dispatching status update for task {task_id} to {status}")

        if status not in ["COMPLETED", "FAILED"]:
            logger.error(f"Invalid status '{status}' provided to update_task_status. Must be 'COMPLETED' or 'FAILED'.")
            return False

        # Determine EventType based on status
        event_type = EventType.TASK_COMPLETED if status == "COMPLETED" else EventType.TASK_FAILED

        # Construct event data payload
        event_data = {
            "correlation_id": task_id, # Link back to the original task
            "status": status, # Include status string for clarity
            "reporting_agent": originating_agent or "UnknownAgent" # Identify who reported
        }
        if event_type == EventType.TASK_COMPLETED and result_summary is not None:
            event_data["results"] = result_summary # Use 'results' key consistent with handlers
        elif event_type == EventType.TASK_FAILED and error_details is not None:
            event_data["error"] = error_details # Use 'error' key consistent with handlers

        # Create the event
        status_event = Event(
            type=event_type,
            source_id=originating_agent or self.agent_name, # Source is the agent reporting
            target_id=DEFAULT_UPDATE_TARGET, # Target the agent processing updates
            data=event_data
        )

        # Attempt to dispatch via AgentBus
        try:
            self.agent_bus.dispatch(status_event)
            logger.info(f"Dispatched {event_type.name} event for task {task_id} to {DEFAULT_UPDATE_TARGET}.")
            return True # Dispatch successful
        except Exception as e:
            logger.error(f"Failed to dispatch {event_type.name} event for task {task_id}: {e}", exc_info=True)
            return False # Dispatch failed

    # --- REMOVED File Writing Fallback Logic --- 

# --- REMOVED Example Usage Block --- 
# (Requires more complex setup with a running bus and executor agent now) 