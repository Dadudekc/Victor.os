import json
from pathlib import Path
from typing import Dict, Any, List, TypedDict, Optional # Updated typing imports

# from filelock import FileLock, Timeout # Removed F401

# Basic logging setup (adjust as needed)
import logging
from dreamos.utils.project_root import find_project_root # Added import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine project root for path definitions
PROJECT_ROOT = find_project_root()

# Updated TaskDict to align with db_task_nexus.py
class TaskDict(TypedDict):
    task_id: str
    description: str
    status: str
    priority: int # Matches DbTaskNexus TaskDict
    created_at: str
    updated_at: Optional[str]
    completed_at: Optional[str]
    agent_id: Optional[str]
    result_summary: Optional[str]
    payload: Optional[Dict[str, Any]]
    tags: List[str]
    dependencies: List[str]

class ShadowTaskNexus:
    """
    A fallback task nexus operating on a local JSON file for redundancy.
    Handles basic task loading, validation, and manipulation if primary systems fail.
    """
    DEFAULT_BACKLOG_PATH = str(PROJECT_ROOT / "runtime" / "tasks" / "shadow_backlog.json") # Updated path

    def __init__(self, backlog_path: str = DEFAULT_BACKLOG_PATH):
        self.backlog_path = Path(backlog_path)
        self.tasks: List[TaskDict] = []
        self._ensure_backlog_exists() # Ensure file exists on init
        # self.load_tasks() # Optionally load tasks immediately

    def _ensure_backlog_exists(self):
        """Creates the shadow backlog file with an empty list if it doesn't exist."""
        if not self.backlog_path.exists():
            logger.warning(f"Shadow backlog file not found at {self.backlog_path}. Creating.")
            try:
                self.backlog_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.backlog_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2)
                logger.info(f"Created empty shadow backlog file: {self.backlog_path}")
            except IOError as e:
                logger.error(f"Failed to create shadow backlog file at {self.backlog_path}: {e}", exc_info=True)
                # Consider raising a more specific exception if creation is critical

    def load_tasks(self) -> bool:
        """Loads tasks from the shadow backlog file. Returns True on success, False on failure."""
        self._ensure_backlog_exists() # Double check existence before loading
        if not self.validate_shadow_backlog(self.backlog_path):
             logger.error(f"Shadow backlog file {self.backlog_path} failed validation. Cannot load tasks.")
             self.tasks = [] # Ensure task list is empty if validation fails
             return False
        try:
            with open(self.backlog_path, 'r', encoding='utf-8') as f:
                self.tasks = json.load(f)
            logger.info(f"Successfully loaded {len(self.tasks)} tasks from {self.backlog_path}")
            return True
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load tasks from {self.backlog_path}: {e}", exc_info=True)
            self.tasks = [] # Clear tasks on load failure
            return False

    def list_tasks(self) -> List[TaskDict]:
         """Returns the currently loaded list of tasks."""
         # In a real implementation, might filter by status etc.
         return self.tasks

    def add_task(self, task: TaskDict) -> bool:
        """Adds a single task to the shadow backlog file."""
        if not isinstance(task, dict) or 'task_id' not in task:
             logger.error("Invalid task format provided for addition.")
             return False

        current_tasks = []
        if self.backlog_path.exists():
            if not self.validate_shadow_backlog(self.backlog_path):
                logger.warning(f"Shadow backlog {self.backlog_path} is invalid. Attempting to overwrite with new task list.")
                current_tasks = [] # Start fresh if invalid
            else:
                 try:
                     with open(self.backlog_path, 'r', encoding='utf-8') as f:
                         current_tasks = json.load(f)
                     if not isinstance(current_tasks, list):
                          logger.warning(f"Shadow backlog {self.backlog_path} is not a list. Overwriting.")
                          current_tasks = []
                 except (IOError, json.JSONDecodeError) as e:
                     logger.error(f"Error reading shadow backlog before add: {e}. Attempting to overwrite.")
                     current_tasks = []


        # Prevent duplicates
        if any(t.get('task_id') == task['task_id'] for t in current_tasks):
            logger.warning(f"Task ID {task['task_id']} already exists in shadow backlog. Skipping addition.")
            # Optionally update existing task here
            return True # Consider returning true if exists but not added? Or false?

        current_tasks.append(task)

        try:
            with open(self.backlog_path, 'w', encoding='utf-8') as f:
                json.dump(current_tasks, f, indent=2)
            logger.info(f"Successfully added task {task['task_id']} to {self.backlog_path}")
            # Update in-memory list as well
            self.tasks = current_tasks
            return True
        except IOError as e:
            logger.error(f"Failed to write updated shadow backlog to {self.backlog_path}: {e}", exc_info=True)
            return False


    @staticmethod
    def validate_shadow_backlog(file_path: str = DEFAULT_BACKLOG_PATH) -> bool:
        """
        Validates the structure and content of the shadow backlog JSON file.
        Returns True if valid, False otherwise.
        """
        path = Path(file_path)
        if not path.exists():
             # File not existing is not strictly 'invalid' for this check,
             # as load_tasks handles creation. But log it.
             logger.warning(f"Shadow backlog file {path} does not exist for validation.")
             return False # Treat as invalid for loading purposes if it DNE when called directly

        if path.stat().st_size == 0:
            logger.warning(f"Shadow backlog file {path} is empty.")
            # An empty file is not valid JSON list. load_tasks handles creation/reset.
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.error(f"Shadow backlog validation failed: Root element is not a list in {path}.")
                return False
            # Optional: Add more specific task schema validation here if needed
            logger.info(f"JSON structure validation successful for {path}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Shadow backlog validation failed: JSONDecodeError in {path}: {e}")
            return False
        except IOError as e:
            logger.error(f"Shadow backlog validation failed: IOError reading {path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Shadow backlog validation failed: Unexpected error reading {path}: {e}", exc_info=True)
            return False

# Example usage (for dry run):
# if __name__ == "__main__":
#     nexus = ShadowTaskNexus()
#     loaded = nexus.load_tasks()
#     if loaded:
#         tasks = nexus.list_tasks()
#         print(f"Dry run: Found {len(tasks)} tasks.")
#         if not tasks:
#              print("Dry run: Shadow backlog is empty.")
#         else:
#              print("Dry run: Tasks listed.") # Print tasks if needed
#     else:
#         print("Dry run: Failed to load tasks (backlog might be invalid or empty).") 