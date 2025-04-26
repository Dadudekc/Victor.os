import json
import time
import os
import uuid
from pathlib import Path
import logging
from typing import Tuple, Any

from .config import TaskDispatcherConfig
from .mailbox_service import MailboxService

# Import shared task utilities
# Assuming task_utils.py is in the parent directory (_agent_coordination)
try:
    from ..task_utils import read_tasks, write_tasks, update_task_status
except ImportError:
    # Fallback for direct execution or different structure
    try:
        import sys
        # Add parent's parent to path (_agent_coordination)
        sys.path.append(str(Path(__file__).parent.parent))
        from task_utils import read_tasks, write_tasks, update_task_status
    except ImportError as e:
        print(f"FATAL: Could not import task utilities. TaskDispatcher cannot function. Error: {e}")
        # In a real scenario, might raise the error or exit
        # For this example, define dummies to allow structure check
        def read_tasks(*args, **kwargs): print("ERROR: read_tasks dummy"); return []
        def write_tasks(*args, **kwargs): print("ERROR: write_tasks dummy") 
        def update_task_status(*args, **kwargs): print("ERROR: update_task_status dummy"); return False

# Configure logging
if not logging.getLogger("TaskDispatcher").hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TaskDispatcher")

class TaskDispatcher:
    def __init__(self, config: TaskDispatcherConfig, mailbox_service: MailboxService):
        """Initializes the TaskDispatcher with DI config and mailbox service."""
        self.config = config
        # Task list path and scheduling
        self.task_list_path = config.task_list_path.resolve()
        self.check_interval = config.check_interval
        # Mailbox service for dispatching messages
        self.mailbox_service = mailbox_service
        logger.info(
            f"TaskDispatcher initialized. Monitoring: {self.task_list_path}."
            f" Mailbox Root: {self.mailbox_service.mailbox_root}"
        )

    def _dispatch_message_to_agent(
        self, target_agent: str, message_payload: dict
    ) -> bool:
        """Dispatches a message via the MailboxService to the agent's inbox."""
        message_payload["sender_agent"] = "TaskDispatcher"
        return self.mailbox_service.dispatch_message(target_agent, message_payload)

    def handle_task(self, task):
        """Handles a single task by dispatching a message to the target agent's mailbox."""
        task_id = task.get("task_id", "unknown_task")
        task_type = task.get("task_type", "unknown_type")
        params = task.get("params", {})
        target_agent = task.get("target_agent") 
        action_keyword = task.get("action") 

        if not target_agent:
            logger.error(f"Task {task_id} missing 'target_agent'. Cannot dispatch. Marking as FAILED.")
            # Use imported utility to update status
            update_task_status(self.task_list_path, task_id, "FAILED", error_message="Missing target_agent")
            return False, "Missing target_agent"

        logger.info(f"Handling task {task_id} (Type: {task_type}, Target: {target_agent}) Params: {params}")

        # Create a generic TASK event message payload
        message_payload = {
            "event_type": "TASK",
            "task_id": task_id,
            "task_type": task_type,
            "params": params,
            "action_keyword": action_keyword
        }
        logger.info(f"Dispatching TASK event for task {task_id} to agent '{target_agent}'")
        dispatch_successful = self._dispatch_message_to_agent(target_agent, message_payload)

        if dispatch_successful:
            logger.info(f"Successfully dispatched TASK event for task {task_id} to {target_agent}.")
            # Mark task as COMPLETED after successful dispatch
            update_task_status(
                self.task_list_path,
                task_id,
                "COMPLETED",
                result_summary=f"TASK event dispatched to {target_agent}"
            )
            return True, None
        else:
            logger.error(f"Failed to dispatch TASK event for task {task_id} to {target_agent}. Marking as FAILED.")
            update_task_status(
                self.task_list_path,
                task_id,
                "FAILED",
                error_message=f"Failed to dispatch TASK event to {target_agent}"
            )
            return False, f"Failed to dispatch TASK event to {target_agent}"

    def process_pending_tasks(self):
        """Reads the task list, processes pending tasks, and updates statuses."""
        logger.debug("Checking for pending tasks...")
        # Use imported utility
        tasks = read_tasks(self.task_list_path)
        if tasks is None or not tasks:
            return

        processed_ids = set()
        tasks_to_process = [task for task in tasks if task.get("status") == "PENDING"]

        if not tasks_to_process:
            return
            
        logger.info(f"Found {len(tasks_to_process)} pending task(s).")

        for task in tasks_to_process:
            task_id = task.get("task_id")
            if not task_id or task_id in processed_ids:
                 continue

            logger.info(f"Attempting to process task: {task_id}")
            
            # Re-read tasks and check status just before processing 
            # Use imported utility
            current_tasks_state = read_tasks(self.task_list_path)
            current_task = next((t for t in current_tasks_state if t.get("task_id") == task_id), None)

            if not current_task or current_task.get("status") != "PENDING":
                logger.info(f"Task {task_id} status changed or disappeared before processing. Skipping.")
                continue

            # Update status to PROCESSING immediately
            # Use imported utility
            if not update_task_status(self.task_list_path, task_id, "PROCESSING"):
                 logger.warning(f"Failed to update task {task_id} status to PROCESSING. Skipping.")
                 continue 

            try:
                # Call handle_task which now also updates to COMPLETED/FAILED on its own
                self.handle_task(current_task) 
                processed_ids.add(task_id)
            except Exception as e:
                logger.error(f"Critical error handling task {task_id}: {e}", exc_info=True)
                # Attempt to mark as FAILED using imported utility
                update_task_status(self.task_list_path, task_id, "FAILED", error_message=f"Critical error: {e}")
                processed_ids.add(task_id) 

        if processed_ids:
             logger.info(f"Finished processing batch. {len(processed_ids)} task(s) attempted.")
        
    def run(self):
        """Main loop to periodically check and process tasks."""
        logger.info("TaskDispatcher starting run loop.")
        try:
            while True:
                self.process_pending_tasks()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("TaskDispatcher stopped by user.")
        except Exception as e:
            logger.error(f"TaskDispatcher encountered critical error in run loop: {e}", exc_info=True)

# Example instantiation (if run directly)
if __name__ == "__main__":
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent 
    task_list_file = project_root / "task_list.json"
    mailbox_dir = project_root / "mailboxes"
    
    print(f"Project Root detected as: {project_root}")
    print(f"Task List Path: {task_list_file}")
    print(f"Mailbox Root Dir: {mailbox_dir}")

    if not task_list_file.is_file():
        print(f"WARNING: Task list {task_list_file} not found. Creating empty file.")
        task_list_file.parent.mkdir(parents=True, exist_ok=True)
        task_list_file.write_text("[]", encoding="utf-8")
        
    dispatcher = TaskDispatcher(task_list_path=str(task_list_file), mailbox_root_dir=str(mailbox_dir))
    dispatcher.run() 
