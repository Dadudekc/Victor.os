"""SQLite-backed core task management system for Dream.OS."""

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

# Import the adapter
from dreamos.core.db.sqlite_adapter import SQLiteAdapter

logger = logging.getLogger(__name__)


# Define a basic Task model matching DB interactions
# Consider sharing this model definition
class TaskDict(TypedDict):  # Using TypedDict for clarity on adapter return types
    task_id: str
    description: str
    status: str
    priority: int
    created_at: str
    updated_at: Optional[str]
    completed_at: Optional[str]
    agent_id: Optional[str]
    result_summary: Optional[str]
    payload: Optional[Dict[str, Any]]
    tags: List[str]
    dependencies: List[str]


class DbTaskNexus:
    """Task management interface backed by SQLiteAdapter."""

    def __init__(self, adapter: SQLiteAdapter):
        self.adapter = adapter
        logger.info("DbTaskNexus initialized with SQLiteAdapter.")

    # --- Core Task Operations (using Adapter) --- #
    def get_next_task(self, agent_id: str) -> Optional[TaskDict]:
        """Atomically claims the highest priority pending task via the adapter."""
        try:
            task_dict = self.adapter.claim_next_pending_task(agent_id)
            if task_dict:
                logger.info(f"Task {task_dict.get('task_id')} claimed by {agent_id}")
                return task_dict  # Return dict directly
            else:
                logger.debug("No pending tasks found via adapter.")
                return None
        except Exception as e:
            logger.error(f"Error claiming next task for {agent_id}: {e}", exc_info=True)
            return None

    def add_task(self, task_data: Dict[str, Any]) -> Optional[TaskDict]:
        """Adds a new task dictionary via the adapter."""
        try:
            # Basic validation before sending to adapter
            if "task_id" not in task_data or "description" not in task_data:
                raise ValueError("Task must contain 'task_id' and 'description'")

            # Ensure essential fields have defaults if missing
            now_iso = datetime.now(timezone.utc).isoformat()
            task_data.setdefault("status", "pending")
            task_data.setdefault("priority", 5)
            task_data.setdefault("created_at", now_iso)
            task_data.setdefault("updated_at", now_iso)
            task_data.setdefault("tags", [])
            task_data.setdefault("dependencies", [])
            task_data.setdefault("payload", None)

            # Minimal validation here, rely on DB constraints / adapter logic mostly
            # Could add Pydantic validation if desired: Task(**task_data)

            self.adapter.add_task(task_data)
            logger.info(f"Added new task via adapter: {task_data['task_id']}")
            return task_data  # Return the dict added

        except ValueError as e:
            logger.error(f"Failed to prepare/validate task for DB add: {e}")
            return None
        except Exception as e:
            logger.exception(f"Failed to add task via adapter: {e}")
            return None

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Updates a task via the adapter."""
        try:
            # Ensure updated_at is set
            updates.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
            self.adapter.update_task(task_id, updates)
            logger.info(f"Updated task {task_id} via adapter.")
            return True
        except Exception as e:
            logger.error(
                f"Failed to update task {task_id} via adapter: {e}", exc_info=True
            )
            return False

    # --- Read Operations (using Adapter) --- #
    def get_all_tasks(self, status: Optional[str] = None) -> List[TaskDict]:
        """Return all tasks or filter by status using the adapter."""
        try:
            if status:
                return self.adapter.get_tasks_by_status(status)
            else:
                return self.adapter.get_all_tasks()
        except Exception as e:
            logger.error(f"Failed to get tasks (status: {status}): {e}", exc_info=True)
            return []

    def get_task_by_id(self, task_id: str) -> Optional[TaskDict]:
        """Retrieves a specific task by its ID using the adapter."""
        try:
            return self.adapter.get_task(task_id)
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
            return None

    def get_pending_tasks(self, limit: Optional[int] = None) -> List[TaskDict]:
        """Retrieves pending tasks via adapter."""
        try:
            return self.adapter.get_pending_tasks(limit=limit)
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}", exc_info=True)
            return []

    def get_tasks_by_tag(self, tag: str) -> List[TaskDict]:
        """Retrieves tasks by tag via adapter."""
        try:
            return self.adapter.get_tasks_by_tag(tag)
        except Exception as e:
            logger.error(f"Failed to get tasks by tag {tag}: {e}", exc_info=True)
            return []

    # --- Stats --- #
    def stats(self) -> Counter:
        """Return a Counter of task statuses by querying the adapter."""
        try:
            all_tasks = self.adapter.get_all_tasks()
            return Counter(task.get("status", "unknown") for task in all_tasks)
        except Exception as e:
            logger.error(f"Failed to generate task stats: {e}", exc_info=True)
            return Counter()
