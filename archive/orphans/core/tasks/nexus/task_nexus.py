"""Core task management system for Dream.OS.

Handles loading, saving, and managing tasks from a shared JSON file.
"""

import json
import logging
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError

# Assuming PROJECT_ROOT is defined elsewhere or calculated reliably
# For simplicity, calculate relative to this file if needed, but prefer central config
try:
    # Try to use the centrally defined project root if available
    from dreamos.utils.project_root import find_project_root

    PROJECT_ROOT = find_project_root()
except ImportError:
    logging.warning(
        "Could not import find_project_root from dreamos.utils.project_root, calculating PROJECT_ROOT relatively. This might be less robust."
    )
    PROJECT_ROOT = Path(__file__).resolve().parents[4]  # Adjust depth if needed

DEFAULT_TASK_FILE = (
    PROJECT_ROOT / "runtime" / "agent_comms" / "central_task_boards" / "task_list.json"
)  # Updated path based on config

logger = logging.getLogger(__name__)


# Define a basic Task model (consider moving to a shared tasks module)
class Task(BaseModel):
    task_id: str
    description: str
    status: str = "pending"  # Default status
    priority: str = "medium"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    claimed_by: Optional[str] = None
    result: Optional[Any] = None
    tags: List[str] = Field(default_factory=list)
    # Add other fields as needed


class TaskNexus:
    """Local task queue and state tracker reading/writing from JSON."""

    def __init__(self, task_file: Union[str, Path] = DEFAULT_TASK_FILE):
        self.task_file_path = Path(task_file)
        self._lock = threading.Lock()  # Basic locking for file access
        self.tasks: List[Task] = self._load()
        logger.info(
            f"TaskNexus initialized. Loaded {len(self.tasks)} tasks from {self.task_file_path}"
        )

    def _load(self) -> List[Task]:
        """Loads tasks from the JSON file."""
        with self._lock:
            if not self.task_file_path.exists():
                logger.warning(
                    f"Task file {self.task_file_path} not found, initializing empty list."
                )
                # Ensure directory exists
                self.task_file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.task_file_path, "w") as f:
                    json.dump([], f)
                return []
            try:
                with open(self.task_file_path, "r") as f:
                    tasks_data = json.load(f)
                # Validate data against Task model
                validated_tasks = [Task(**task_data) for task_data in tasks_data]
                return validated_tasks
            except (json.JSONDecodeError, ValidationError, FileNotFoundError) as e:
                logger.error(
                    f"Error loading tasks from {self.task_file_path}: {e}. Returning empty list."
                )
                # Consider backup/recovery mechanism here
                return []
            except Exception as e:
                logger.exception(f"Unexpected error loading tasks: {e}")
                return []

    def _save(self):
        """Saves the current task list to the JSON file."""
        with self._lock:
            try:
                # Ensure directory exists before saving
                self.task_file_path.parent.mkdir(parents=True, exist_ok=True)
                tasks_data = [task.model_dump() for task in self.tasks]
                with open(self.task_file_path, "w") as f:
                    json.dump(tasks_data, f, indent=2)
                logger.debug(f"Saved {len(self.tasks)} tasks to {self.task_file_path}")
            except Exception as e:
                logger.exception(f"Error saving tasks to {self.task_file_path}: {e}")

    def get_next_task(
        self, agent_id: Optional[str] = None, type_filter: Optional[str] = None
    ) -> Optional[Task]:
        """Return first pending task, mark as claimed, and save."""
        # Note: type_filter is not part of the basic spec, added for potential future use
        with self._lock:
            for task in self.tasks:
                if task.status == "pending":
                    # Basic type filtering (e.g., check tags)
                    if type_filter and type_filter not in task.tags:
                        continue

                    task.status = "claimed"
                    task.claimed_by = agent_id if agent_id else "unknown_agent"
                    task.updated_at = datetime.now(timezone.utc).isoformat()
                    self._save()  # Save immediately after claiming
                    logger.info(f"Task {task.task_id} claimed by {task.claimed_by}")
                    return task
            logger.debug("No pending tasks found.")
            return None

    def add_task(self, task_dict: Dict[str, Any]) -> Task:
        """Append new task (ensuring status is pending) and save."""
        with self._lock:
            try:
                # Ensure required fields are present (basic check)
                if "task_id" not in task_dict or "description" not in task_dict:
                    raise ValueError(
                        "Task dictionary must contain 'task_id' and 'description'"
                    )

                # Set defaults if not present
                task_dict.setdefault("status", "pending")
                task_dict.setdefault(
                    "created_at", datetime.now(timezone.utc).isoformat()
                )
                task_dict.setdefault(
                    "updated_at", datetime.now(timezone.utc).isoformat()
                )

                new_task = Task(**task_dict)
                self.tasks.append(new_task)
                self._save()
                logger.info(f"Added new task: {new_task.task_id}")
                return new_task
            except ValidationError as e:
                logger.error(f"Failed to validate and add task: {e}")
                raise
            except Exception as e:
                logger.exception(f"Failed to add task: {e}")
                raise

    def update_task_status(
        self, task_id: str, status: str, result: Optional[Any] = None
    ) -> bool:
        """Change status of given task and save."""
        with self._lock:
            for task in self.tasks:
                if task.task_id == task_id:
                    task.status = status
                    task.updated_at = datetime.now(timezone.utc).isoformat()
                    if result is not None:
                        task.result = result
                    # Unclaim if completed or failed?
                    if status in ["completed", "failed", "cancelled"]:
                        task.claimed_by = None

                    self._save()
                    logger.info(f"Updated task {task_id} status to {status}")
                    return True
            logger.warning(f"Task ID {task_id} not found for status update.")
            return False

    def get_all_tasks(self, status: Optional[str] = None) -> List[Task]:
        """Return all tasks or filter by status."""
        # Return a copy to prevent external modification of internal list
        with self._lock:
            tasks_copy = [task.model_copy() for task in self.tasks]

        if status:
            return [task for task in tasks_copy if task.status == status]
        return tasks_copy

    def stats(self) -> Counter:
        """Return a Counter of task statuses."""
        with self._lock:
            # Create stats from the internal list for consistency
            return Counter(task.status for task in self.tasks)

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Retrieves a specific task by its ID."""
        with self._lock:
            for task in self.tasks:
                if task.task_id == task_id:
                    return task.model_copy()
            return None
