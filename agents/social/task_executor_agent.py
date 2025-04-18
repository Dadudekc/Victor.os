"""
Agent responsible for receiving TASK_QUEUED events, dispatching corresponding
command events to target agents via the AgentBus, and processing status events
(TASK_COMPLETED, TASK_FAILED) to update task status via TaskStatusUpdater.
"""
import logging
import os
# Removed sys path manipulation
# import sys
# Removed json/os imports related to direct file access
# import json
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

# Canonical imports
from core.coordination.agent_bus import AgentBus
from core.coordination.dispatcher import Event, EventType

# Status Updater Utility (ensure its path/import is correct)
try:
    from utils.task_status_updater import TaskStatusUpdater
except ImportError as e:
     # Fallback path if utils is not directly under core
     try:
         from task_status_updater import TaskStatusUpdater
     except ImportError:
         logger.critical(f"CRITICAL: Could not import TaskStatusUpdater utility: {e}. TaskExecutorAgent will not function.")
         # Define dummy for basic loading, but agent will fail
         class TaskStatusUpdater:
             def __init__(self, *args, **kwargs): pass
             def update_task_status(self, *args, **kwargs): logger.error("Dummy TaskStatusUpdater called!"); return False

# TaskStatus constants might still be needed by TaskStatusUpdater or for interpreting data
try:
    from agents.task_executor_agent import TaskStatus # Defines standard status strings
except ImportError:
     logger.warning("Could not import TaskStatus constants definition.")
     class TaskStatus:
        PENDING = "PENDING"; INVALID = "INVALID"; DISPATCHED = "DISPATCHED"; DISPATCH_FAILED = "DISPATCH_FAILED"
        RUNNING = "RUNNING"; COMPLETED = "COMPLETED"; FAILED = "FAILED"; ERROR = "ERROR"; UNKNOWN = "UNKNOWN"

logger = logging.getLogger(__name__)

AGENT_NAME = "TaskExecutorAgent"
# Removed DEFAULT_TASK_LIST_PATH

class TaskExecutorAgent:
    """Receives TASK_QUEUED events and orchestrates task execution via other agents."""

    def __init__(self, agent_bus: AgentBus, task_status_updater: TaskStatusUpdater):
        """
        Initializes the task executor.

        Args:
            agent_bus: The central AgentBus instance.
            task_status_updater: The utility for updating task statuses.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.status_updater = task_status_updater # Store the updater instance
        self._stop_event = threading.Event() # Kept if background monitoring/cleanup needed
        self._thread: Optional[threading.Thread] = None # Kept if background tasks added later

        # Register agent
        try:
            self.bus.register_agent(self.agent_name, capabilities=["task_execution", "task_dispatch"])
            logger.info(f"{self.agent_name} registered.")
        except Exception as e:
            logger.critical(f"Failed to register TaskExecutorAgent: {e}")
            raise

        # Register handlers for relevant EventTypes
        try:
            # Handle requests to queue and execute a task
            self.bus.register_handler(EventType.TASK_QUEUED, self.handle_event)
            # Handle responses indicating task completion/failure
            self.bus.register_handler(EventType.TASK_COMPLETED, self.handle_event)
            self.bus.register_handler(EventType.TASK_FAILED, self.handle_event)
            # Optionally handle progress updates
            # self.bus.register_handler(EventType.TASK_PROGRESS, self.handle_event)
            logger.info(f"Registered handlers for {EventType.TASK_QUEUED.name}, {EventType.TASK_COMPLETED.name}, {EventType.TASK_FAILED.name}")
        except Exception as e:
            logger.critical(f"Failed to register event handlers for TaskExecutorAgent: {e}")
            raise # Cannot function without handlers

        logger.info(f"{self.agent_name} initialized and listening for task events.")

    def _normalize_status(self, event_type: EventType, event_data: Dict[str, Any]) -> str:
        """Maps incoming event type/data to a standardized TaskStatus string."""
        if event_type == EventType.TASK_COMPLETED:
            return TaskStatus.COMPLETED
        elif event_type == EventType.TASK_FAILED:
            # Could potentially differentiate between FAILED and ERROR based on data
            return TaskStatus.FAILED # Or TaskStatus.ERROR if error details indicate exception
        # Add handling for TASK_PROGRESS if needed
        else:
            logger.warning(f"Attempted to normalize unhandled event type: {event_type.name}")
            return TaskStatus.UNKNOWN

    # --- REMOVED _load_tasks, _check_dependencies, run_cycle --- 

    def handle_event(self, event: Event):
        """Handles incoming TASK_QUEUED, TASK_COMPLETED, and TASK_FAILED events."""
        logger.debug(f"{self.agent_name} received event: Type={event.type.name}, Source={event.source_id}, EventID={event.id}")

        if event.type == EventType.TASK_QUEUED:
            self._dispatch_task(event)
        elif event.type in [EventType.TASK_COMPLETED, EventType.TASK_FAILED]:
            self._process_task_update(event)
        # Handle TASK_PROGRESS if subscribed
        # elif event.type == EventType.TASK_PROGRESS:
        #     self._process_task_update(event) # Might use same logic or dedicated one
        else:
            logger.warning(f"Received unexpected event type in handler: {event.type.name}. Ignoring.")

    def _dispatch_task(self, queue_event: Event):
        """Processes a TASK_QUEUED event and dispatches the actual command event."""
        task_data = queue_event.data
        task_id = task_data.get("task_id")

        if not task_id:
            logger.error(f"Received {EventType.TASK_QUEUED.name} event (ID: {queue_event.id}) without a 'task_id' in data. Cannot process.")
            # Optionally send a TASK_FAILED event back to source?
            return

        # Validate required fields (action, target_agent, params?)
        action = task_data.get("action")
        target_agent = task_data.get("target_agent")
        params = task_data.get("params", {})

        if not action or not target_agent:
            error_msg = f"Task {task_id} is invalid: Missing 'action' or 'target_agent' in data."
            logger.error(error_msg + f" (Event ID: {queue_event.id})")
            self.status_updater.update_task_status(task_id=task_id, status=TaskStatus.INVALID, error_details=error_msg)
            return

        # Determine the EventType for the command based on the action string
        # This requires a mapping or convention
        try:
            # Assuming action string matches EventType enum member name (e.g., action="POST_CONTENT")
            command_event_type = EventType[action.upper()] 
        except KeyError:
            error_msg = f"Task {task_id} has unknown action '{action}'. Cannot map to EventType."
            logger.error(error_msg + f" (Event ID: {queue_event.id})")
            self.status_updater.update_task_status(task_id=task_id, status=TaskStatus.INVALID, error_details=error_msg)
            return

        # Construct the command event payload (usually the 'params' dict)
        command_data = params
        # IMPORTANT: Ensure the original task_id is included for correlation in responses
        # The receiving agent should put this task_id into the correlation_id of its response event
        command_data["task_id"] = task_id # Let target agent know the task ID its working on
        command_data["queue_event_id"] = queue_event.id # Optionally pass queue event id too

        command_event = Event(
            type=command_event_type,
            source_id=self.agent_name,
            target_id=target_agent,
            data=command_data,
            priority=task_data.get("priority", 0) # Pass priority from queued task
            # The new event will get its own unique ID automatically
        )

        try:
            # Dispatch the actual command event to the target agent
            self.bus.dispatch(command_event)
            logger.info(f"Dispatched command event {command_event.id} ({command_event_type.name}) for task {task_id} to agent {target_agent}.")

            # Update task status to DISPATCHED
            # Store the dispatched command event ID for future reference/correlation?
            update_success = self.status_updater.update_task_status(
                task_id=task_id,
                status=TaskStatus.DISPATCHED,
                # Optionally store the dispatched command event ID
                # dispatched_event_id=command_event.id 
            )
            if not update_success:
                logger.error(f"Failed to update task {task_id} status to DISPATCHED after dispatching event {command_event.id}.")
                # This is problematic, task might run but status is wrong.

        except Exception as e:
            error_msg = f"Failed to dispatch command event {command_event.id} for task {task_id}: {e}"
            logger.error(error_msg, exc_info=True)
            # Update task status to DISPATCH_FAILED
            self.status_updater.update_task_status(task_id=task_id, status=TaskStatus.DISPATCH_FAILED, error_details=str(e))

    def _process_task_update(self, status_event: Event):
        """Processes TASK_COMPLETED/TASK_FAILED events using the TaskStatusUpdater."""
        event_data = status_event.data
        # Task ID should be in the correlation_id field of the response event data
        task_id = event_data.get("correlation_id")

        if not task_id:
            # Compatibility: Check if task_id is directly in payload (older agents might do this)
            task_id = event_data.get("task_id") 
            if task_id:
                 logger.warning(f"Received status event {status_event.id} ({status_event.type.name}) with 'task_id' in data instead of 'correlation_id'. Processing anyway.")
            else:
                logger.error(f"Received status event {status_event.id} ({status_event.type.name}) from {status_event.source_id} without 'correlation_id' in data. Cannot link to original task.")
                return

        # Normalize the status based on the event type
        final_task_status = self._normalize_status(status_event.type, event_data)

        # Extract result or error details from the event data
        result_summary = None
        error_details = None
        if final_task_status == TaskStatus.COMPLETED:
            result_summary = str(event_data.get('results', '')) # Adapt based on expected result structure
        elif final_task_status in [TaskStatus.FAILED, TaskStatus.ERROR]:
             error_details = str(event_data.get('error', '')) # Adapt based on expected error structure

        # Use the TaskStatusUpdater
        success = self.status_updater.update_task_status(
            task_id=task_id,
            status=final_task_status,
            result_summary=result_summary,
            error_details=error_details,
            originating_agent=status_event.source_id # Agent that completed/failed the task
        )

        if not success:
            logger.error(f"TaskStatusUpdater failed to update status for task '{task_id}' based on event {status_event.id} from agent {status_event.source_id}.")
        else:
             logger.info(f"TaskStatusUpdater successfully processed status update for task '{task_id}' to {final_task_status} based on event {status_event.id}.")

    # --- REMOVED handle_response (merged into handle_event/_process_task_update) --- 

    # --- Lifecycle methods (start/stop) --- 
    # Keep these if agent needs background tasks later, otherwise can be removed.
    def _run_loop(self):
        """Placeholder for potential background monitoring or cleanup loop."""
        while not self._stop_event.is_set():
            try:
                # Example: Check for stalled tasks?
                logger.debug(f"{self.agent_name} background loop running...")
                time.sleep(60) # Sleep for a minute
            except Exception as e:
                logger.error(f"Error in {self.agent_name} background loop: {e}", exc_info=True)
                time.sleep(10) # Prevent tight loop on error

    def start(self):
        """Starts the agent's background thread if implemented."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"{self.agent_name} start called but thread is already running.")
            return
        self._stop_event.clear()
        # Uncomment to enable background loop
        # self._thread = threading.Thread(target=self._run_loop, daemon=True)
        # self._thread.start()
        logger.info(f"{self.agent_name} started (background loop {'enabled' if self._thread else 'disabled'}).")

    def stop(self):
        """Stops the agent's background thread."""
        logger.info(f"Stopping {self.agent_name}...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=5.0) # Wait for the thread to finish
                if self._thread.is_alive():
                     logger.warning(f"{self.agent_name} background thread did not stop promptly.")
            except Exception as e:
                 logger.error(f"Error joining background thread for {self.agent_name}: {e}")
        self._thread = None
        # Unregister? Depends on system lifecycle management
        # try:
        #     self.bus.unregister_agent(self.agent_name)
        # except Exception as e:
        #     logger.error(f"Error unregistering TaskExecutorAgent: {e}")
        logger.info(f"{self.agent_name} stopped.")

# --- REMOVED Main execution block --- 