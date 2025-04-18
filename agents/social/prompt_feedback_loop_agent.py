"""
Agent responsible for monitoring task failures via events and injecting new diagnostic tasks.
"""
import logging
import os
# Removed sys path manipulation
# import sys
import json
import time
import threading
import uuid # For generating unique task IDs
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# Canonical imports
from core.coordination.agent_bus import AgentBus
from core.coordination.dispatcher import Event, EventType
# Removed AgentStatus import
# from core.coordination.bus_types import AgentStatus

# TaskStatus constants might still be useful for interpreting event data, but EventType is primary
# Keep this import for now, but may become redundant
try:
    from agents.task_executor_agent import TaskStatus # Defines standard status strings
except ImportError:
     logger.warning("Could not import TaskStatus constants.")
     class TaskStatus:
        FAILED = "FAILED"; ERROR = "ERROR"; PENDING = "PENDING"; COMPLETED = "COMPLETED"

logger = logging.getLogger(__name__)

AGENT_NAME = "PromptFeedbackLoopAgent"
# Removed TASK_LIST_PATH constant, agent no longer directly accesses the list
# DEFAULT_TASK_LIST_PATH = "task_list.json"
MAX_REPAIR_ATTEMPTS = 1 # Keep configuration for repair logic

# Define the ID of the agent responsible for task execution
TASK_EXECUTOR_AGENT_ID = "TaskExecutorAgent" # Make this configurable or import from constants?

class PromptFeedbackLoopAgent:
    """Monitors for TASK_FAILED events via AgentBus and injects diagnostic tasks."""

    def __init__(self, agent_bus: AgentBus):
        """
        Initializes the feedback loop agent.

        Args:
            agent_bus: The central AgentBus instance.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        # Removed task list path and lock, agent uses events now
        # self.task_list_path = os.path.abspath(task_list_path)
        # self._lock = task_list_lock if task_list_lock else threading.Lock()
        self._processed_failures: Dict[str, int] = {} # Keep track of repair attempts {task_id: count}
        self._processed_lock = threading.Lock() # Lock for accessing _processed_failures

        # Register agent
        self.bus.register_agent(self.agent_name, capabilities=["feedback_loop", "task_injection"])

        # Register handler specifically for TASK_FAILED events
        try:
            self.bus.register_handler(EventType.TASK_FAILED, self.handle_event)
            logger.info(f"Registered handler for EventType: {EventType.TASK_FAILED.name}")
        except Exception as e:
            logger.error(f"Failed to register handler for {EventType.TASK_FAILED.name}: {e}")
            # Agent might not function correctly

        logger.info(f"{self.agent_name} initialized. Listening for {EventType.TASK_FAILED.name} events.")

    # --- REMOVED Task List Load/Save/Update Logic ---
    # def _load_tasks(self) -> List[Dict[str, Any]]: ...
    # def _save_tasks(self, tasks: List[Dict[str, Any]]) -> bool: ...
    # def _mark_repair_triggered(self, tasks: List[Dict[str, Any]], task_id: str) -> bool: ...

    def _check_and_increment_repair_attempts(self, task_id: str) -> bool:
        """Checks if max repair attempts reached for a task ID and increments count. Thread-safe."""
        with self._processed_lock:
            attempts = self._processed_failures.get(task_id, 0)
            if attempts >= MAX_REPAIR_ATTEMPTS:
                logger.warning(f"Max repair attempts ({MAX_REPAIR_ATTEMPTS}) reached for failed task {task_id}. Skipping injection.")
                return False # Max attempts reached
            else:
                self._processed_failures[task_id] = attempts + 1
                logger.info(f"Incrementing repair attempt count for task {task_id} to {attempts + 1}.")
                return True # Ok to proceed

    def _create_diagnostic_task_data(self, failed_event: Event) -> Optional[Dict[str, Any]]:
        """Generates the data payload for a diagnostic task event based on the failed event."""
        failed_data = failed_event.data
        # Extract details about the original task from the failed event data
        # The structure of failed_data depends on what TaskExecutorAgent puts in TASK_FAILED events
        original_task_id = failed_data.get("task_id") or failed_data.get("correlation_id") # Prefer task_id if present
        if not original_task_id:
             logger.error(f"Cannot create diagnostic task: Missing 'task_id' or 'correlation_id' in TASK_FAILED event data (Event ID: {failed_event.id}). Data: {failed_data}")
             return None

        # Use details likely provided by TaskExecutorAgent in the TASK_FAILED event data payload
        original_action = failed_data.get("original_action", "unknown_action")
        original_params = failed_data.get("original_params", {})
        failure_reason = failed_data.get("error", "Unknown error")

        # Check repair attempts for the original task ID
        if not self._check_and_increment_repair_attempts(original_task_id):
            return None # Max attempts reached or other issue

        new_task_id = f"diag_{original_task_id}_{uuid.uuid4().hex[:6]}"
        diag_commands = [
            f"echo \"[Agent Repair] Task {original_task_id} (Action: {original_action}) failed. Diagnosing...\"",
            f"echo \"Failure Reason: {str(failure_reason)[:150]}...\"" # Ensure reason is string
        ]
        target_agent = "CursorControlAgent" # Default target for diagnostics
        diag_action = "RUN_TERMINAL_COMMAND" # Default diagnostic action

        # --- Context-Specific Diagnostics (logic remains similar, using extracted data) ---
        if original_action == "RUN_TERMINAL_COMMAND":
            diag_commands.extend(["pwd", "ls -alh"])
            original_command = original_params.get("command", "")
            if "build" in original_command or ".py" in original_command:
                 diag_commands.extend(["echo \"Attempting to check recent logs...\"", "ls -lt *.log | head -n 5"])

        elif original_action == "OPEN_FILE":
            file_path = original_params.get("file_path")
            if file_path:
                diag_commands.extend([f"echo \"Checking file status for: {file_path}\"", f"ls -ld \"{file_path}\"" ])
            else:
                 diag_commands.extend(["echo \"Original OPEN_FILE task missing file_path parameter.\"", "pwd", "ls -alh"])

        elif original_action in ["GET_EDITOR_CONTENT", "SET_EDITOR_CONTENT", "INSERT_EDITOR_TEXT", "FIND_ELEMENT", "ENSURE_CURSOR_FOCUSED"]:
             diag_commands.append("echo \"Checking Cursor process status...\"")
             check_cmd = "tasklist | findstr Cursor" if os.name == 'nt' else "ps aux | grep -i [C]ursor"
             diag_commands.append(check_cmd)

        else:
             diag_commands.extend(["echo \"Running default diagnostics (pwd, ls)...\"", "pwd", "ls -alh"])

        # --- End Context-Specific Diagnostics ---

        full_diag_command = " && ".join(diag_commands)

        # Construct the data payload for the new TASK_QUEUED event
        new_task_data = {
            "task_id": new_task_id,
            "status": TaskStatus.PENDING, # TaskExecutor expects status
            "task_type": f"diagnose_{original_action}_failure",
            "action": diag_action,
            "params": {
                "command": full_diag_command,
                "related_task_id": original_task_id,
                "failure_reason": str(failure_reason), # Ensure string
                "original_task_action": original_action,
                "original_task_params": original_params
            },
            # 'depends_on' might be handled by TaskExecutor based on related_task_id?
            # "depends_on": [original_task_id], # Or maybe not needed if repair runs independently
            "priority": 1, # Higher priority for diagnostics?
            "retry_count": 0,
            "target_agent": target_agent
            # Add any other fields TaskExecutorAgent expects for new tasks
        }
        logger.info(f"Generated diagnostic task data for {new_task_id} (related to failed task {original_task_id}) Action: {diag_action}")
        return new_task_data

    def _dispatch_diagnostic_task(self, diagnostic_task_data: Dict[str, Any]):
         """Dispatches a TASK_QUEUED event to add the diagnostic task."""
         new_task_id = diagnostic_task_data.get("task_id", "unknown_new_task")
         failed_task_id = diagnostic_task_data.get("params", {}).get("related_task_id", "unknown_original")

         event = Event(
             type=EventType.TASK_QUEUED, # Event type to request task execution
             source_id=self.agent_name,
             target_id=TASK_EXECUTOR_AGENT_ID, # Target the agent managing the queue
             data=diagnostic_task_data,
             priority=diagnostic_task_data.get("priority", 1) # Use priority from task data
         )
         try:
            self.bus.dispatch(event)
            logger.info(f"Dispatched {EventType.TASK_QUEUED.name} event for diagnostic task {new_task_id} (failed task: {failed_task_id}) to {TASK_EXECUTOR_AGENT_ID}.")
            # Log this injection event to the monitor agent
            self._log_injection_event(failed_task_id, new_task_id)
         except Exception as e:
             logger.error(f"Failed to dispatch diagnostic task event for {new_task_id}: {e}", exc_info=True)

    def _log_injection_event(self, failed_task_id: str, new_task_id: str):
         """Dispatches a SYSTEM_EVENT to the AgentMonitorAgent."""
         log_data = {
             "event_description": "Diagnostic task created in response to failure",
             "failed_task_id": failed_task_id,
             "diagnostic_task_id": new_task_id,
             "trigger_agent": self.agent_name
         }
         # Use a specific EventType if defined, otherwise use a generic one
         log_event_type = EventType.SYSTEM # Or a more specific MONITOR_LOG type

         event = Event(
             type=log_event_type,
             source_id=self.agent_name,
             target_id="AgentMonitorAgent", # Target the monitor agent
             data=log_data
             # No specific priority needed for log events usually
         )
         try:
            self.bus.dispatch(event)
            logger.debug(f"Dispatched logging event to AgentMonitorAgent for task injection ({new_task_id}).")
         except Exception as e:
             logger.warning(f"Could not dispatch logging event for task injection: {e}")

    # --- Event Handler --- 
    def handle_event(self, event: Event):
        """Handles TASK_FAILED events."""
        if event.type != EventType.TASK_FAILED:
             logger.warning(f"Received unexpected event type: {event.type.name}. Expected {EventType.TASK_FAILED.name}. Ignoring.")
             return

        logger.info(f"Received {EventType.TASK_FAILED.name} event (ID: {event.id}, Source: {event.source_id}). Checking for repair action.")

        # Create the data for the diagnostic task based on the failed event
        diagnostic_task_data = self._create_diagnostic_task_data(failed_event=event)

        if diagnostic_task_data:
            # Dispatch the event to queue the new diagnostic task
            self._dispatch_diagnostic_task(diagnostic_task_data)
        else:
            # Reason for not creating data (e.g., max attempts) already logged in _create_diagnostic_task_data
             logger.debug(f"No diagnostic task generated for failed event {event.id}.")

    # --- REMOVED trigger_repair_task_injection (logic moved into handle_event/create/dispatch) ---
    # def trigger_repair_task_injection(self, failed_task_id: str): ...

    def shutdown(self):
        """Perform any cleanup needed for the feedback loop agent."""
        logger.info(f"Shutting down {self.agent_name}...")
        # Persist processed failures? Might be useful across restarts
        # with self._processed_lock:
        #     try: # Example persistence
        #         with open("run/state/feedback_loop_processed.json", "w") as f:
        #             json.dump(self._processed_failures, f)
        #     except Exception as e:
        #         logger.error(f"Failed to save processed failures state: {e}")

        # Unregister? (Optional, depends on bus lifecycle)
        # try:
        #     self.bus.unregister_agent(self.agent_name)
        # except Exception as e:
        #     logger.error(f"Error unregistering agent {self.agent_name}: {e}")

        logger.info(f"{self.agent_name} shutdown complete.")

# --- REMOVED Main execution block --- 