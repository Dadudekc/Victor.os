"""Shadow task management system for Agent-1 fallback."""

import json
import logging
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError

# Assuming PROJECT_ROOT is defined elsewhere or calculated reliably
# For simplicity, calculate relative to this file if needed, but prefer central config
# This might need adjustment based on actual usage context
try:
    # Attempt to import from standard location first
    from dreamos.core.config import PROJECT_ROOT
except ImportError:
    try:
        # Fallback if running standalone or structure differs
        from core.config import PROJECT_ROOT
    except ImportError:
        logging.warning(
            "Could not import PROJECT_ROOT from core config, calculating relatively for ShadowTaskNexus.",
            exc_info=True,
        )
        # Calculate relative to this file: Agent-1 -> agents -> dreamos -> src -> PROJECT_ROOT
        PROJECT_ROOT = Path(__file__).resolve().parents[3]


# Define the shadow backlog path relative to PROJECT_ROOT
# IMPORTANT: Ensure this path is accessible even if runtime/ is problematic
SHADOW_BACKLOG_FILE = (
    PROJECT_ROOT / "runtime" / "agent_comms" / "Agent-1" / "shadow_backlog.json"
)

logger = logging.getLogger(__name__)


# Define a basic Task model (Copied from TaskNexus - consider moving to a shared location)
# If the original Task model is accessible via import, prefer that.
try:
    # Attempt to import the canonical Task model
    from dreamos.core.tasks.nexus.task_nexus import Task

    logger.debug("Imported Task model from dreamos.core.tasks.nexus.task_nexus")
except ImportError:
    logger.warning(
        "Could not import Task model from core nexus, defining locally for ShadowTaskNexus."
    )

    class Task(BaseModel):
        task_id: str
        description: str
        status: str = "pending"  # Default status
        priority: str = "medium"
        created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
        updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
        claimed_by: Optional[str] = None
        result: Optional[Any] = None
        tags: List[str] = Field(default_factory=list)
        # Add other relevant fields from the canonical Task model if needed


class ShadowTaskNexus:
    """Fallback task queue for Agent-1, mirroring TaskNexus but using shadow_backlog.json."""

    def __init__(self, task_file: Union[str, Path] = SHADOW_BACKLOG_FILE):
        self.task_file_path = Path(task_file)
        self._lock = threading.Lock()  # Basic locking for file access
        self.tasks: List[Task] = self._load()
        logger.info(
            f"ShadowTaskNexus initialized. Loaded {len(self.tasks)} tasks from {self.task_file_path}"
        )

    def _load(self) -> List[Task]:
        """Loads tasks from the shadow JSON file."""
        with self._lock:
            if not self.task_file_path.exists():
                logger.warning(
                    f"Shadow task file {self.task_file_path} not found, initializing empty list.",
                    exc_info=True,  # Add stack trace for debugging path issues
                )
                # Ensure directory exists
                try:
                    self.task_file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.task_file_path, "w", encoding="utf-8") as f:
                        json.dump([], f)
                    logger.info(
                        f"Created empty shadow backlog file: {self.task_file_path}"
                    )
                except OSError as e:
                    logger.error(
                        f"Failed to create shadow backlog directory/file {self.task_file_path}: {e}",
                        exc_info=True,
                    )
                    return []  # Critical failure if cannot create shadow file
                return []
            try:
                with open(self.task_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if not content.strip():  # Handle empty file case
                        logger.warning(
                            f"Shadow task file {self.task_file_path} is empty, returning empty list."
                        )
                        return []
                    tasks_data = json.loads(content)

                # Validate data against Task model
                validated_tasks: List[Task] = []
                validation_errors = 0
                for i, task_data in enumerate(tasks_data):
                    try:
                        validated_tasks.append(Task(**task_data))
                    except ValidationError as e:
                        validation_errors += 1
                        logger.error(
                            f"Validation error loading task #{i+1} from shadow backlog {self.task_file_path}: {e}"
                        )
                        # Optionally skip invalid tasks or halt? Skipping for resilience.

                if validation_errors > 0:
                    logger.warning(
                        f"Completed loading shadow tasks with {validation_errors} validation errors."
                    )

                return validated_tasks
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON decode error loading shadow tasks from {self.task_file_path}: {e}. File content might be corrupted. Returning empty list.",
                    exc_info=True,
                )
                return []
            except (
                FileNotFoundError
            ):  # Should be caught by exists() check, but belt-and-suspenders
                logger.error(
                    f"Shadow task file {self.task_file_path} disappeared between checks? Returning empty list.",
                    exc_info=True,
                )
                return []
            except Exception as e:
                logger.exception(
                    f"Unexpected error loading shadow tasks from {self.task_file_path}: {e}"
                )
                return []

    def _save(self):
        """Saves the current task list to the shadow JSON file."""
        with self._lock:
            try:
                # Ensure directory exists before saving
                self.task_file_path.parent.mkdir(parents=True, exist_ok=True)
                # Use model_dump for Pydantic v2+ compatibility
                tasks_data = [task.model_dump(mode="json") for task in self.tasks]
                with open(self.task_file_path, "w", encoding="utf-8") as f:
                    json.dump(tasks_data, f, indent=2)
                logger.debug(
                    f"Saved {len(self.tasks)} shadow tasks to {self.task_file_path}"
                )
            except OSError as e:
                logger.error(
                    f"OS error saving shadow tasks to {self.task_file_path}: {e}",
                    exc_info=True,
                )
            except Exception as e:
                logger.exception(
                    f"Unexpected error saving shadow tasks to {self.task_file_path}: {e}"
                )

    # --- Mirrored Public Methods from TaskNexus ---

    def get_next_task(
        self, agent_id: Optional[str] = None, type_filter: Optional[str] = None
    ) -> Optional[Task]:
        """Return first pending shadow task, mark as claimed, and save."""
        with self._lock:
            for task in self.tasks:
                if task.status == "pending":
                    # Basic type filtering (e.g., check tags)
                    if type_filter and type_filter not in task.tags:
                        continue

                    task.status = "claimed"
                    task.claimed_by = (
                        agent_id if agent_id else "unknown_shadow_agent"
                    )  # Identify shadow claim
                    task.updated_at = datetime.utcnow().isoformat()
                    self._save()  # Save immediately after claiming
                    logger.info(
                        f"Shadow task {task.task_id} claimed by {task.claimed_by}"
                    )
                    return task.model_copy(deep=True)  # Return copy
            logger.debug("No pending shadow tasks found.")
            return None

    def add_task(self, task_dict: Dict[str, Any]) -> Optional[Task]:
        """Append new task to shadow backlog (ensuring status is pending) and save."""
        with self._lock:
            try:
                # Ensure required fields are present (basic check)
                if "task_id" not in task_dict or "description" not in task_dict:
                    raise ValueError(
                        "Task dictionary must contain 'task_id' and 'description'"
                    )

                # Set defaults if not present
                task_dict.setdefault("status", "pending")
                task_dict.setdefault("created_at", datetime.utcnow().isoformat())
                task_dict.setdefault("updated_at", datetime.utcnow().isoformat())
                task_dict.setdefault("tags", [])
                task_dict.setdefault("priority", "medium")  # Ensure priority default

                new_task = Task(**task_dict)
                # Avoid adding duplicates if already present
                if any(t.task_id == new_task.task_id for t in self.tasks):
                    logger.warning(
                        f"Shadow task {new_task.task_id} already exists. Skipping add."
                    )
                    return next(
                        (
                            t.model_copy(deep=True)
                            for t in self.tasks
                            if t.task_id == new_task.task_id
                        ),
                        None,
                    )

                self.tasks.append(new_task)
                self._save()
                logger.info(f"Added new shadow task: {new_task.task_id}")
                return new_task.model_copy(deep=True)  # Return copy
            except ValidationError as e:
                logger.error(
                    f"Failed to validate and add shadow task: {e}", exc_info=True
                )
                # Optionally raise, but returning None might be more resilient for automated flow
                return None
            except Exception as e:
                logger.exception(f"Failed to add shadow task: {e}")
                # Optionally raise, but returning None might be more resilient for automated flow
                return None

    def update_task_status(
        self, task_id: str, status: str, result: Optional[Any] = None
    ) -> bool:
        """Change status of given shadow task and save."""
        with self._lock:
            task_found = False
            for task in self.tasks:
                if task.task_id == task_id:
                    task_found = True
                    task.status = status
                    task.updated_at = datetime.utcnow().isoformat()
                    if result is not None:
                        # Store result appropriately, ensuring it's serializable if needed
                        try:
                            # Attempt basic JSON serialization check if result is complex
                            if isinstance(result, (dict, list)):
                                json.dumps(result)
                            task.result = result
                        except (TypeError, OverflowError) as json_err:
                            logger.warning(
                                f"Result for shadow task {task_id} is not JSON serializable: {json_err}. Storing as string."
                            )
                            task.result = str(result)

                    # Unclaim if completed or failed? (Mirroring TaskNexus logic)
                    if status.lower() in ["completed", "failed", "cancelled"]:
                        task.claimed_by = None

                    self._save()
                    logger.info(f"Updated shadow task {task_id} status to {status}")
                    return True  # Exit loop and method once task is found and updated

            if not task_found:
                logger.warning(f"Shadow task ID {task_id} not found for status update.")
            return False

    def get_all_tasks(self, status: Optional[str] = None) -> List[Task]:
        """Return all shadow tasks or filter by status."""
        # Return a copy to prevent external modification of internal list
        with self._lock:
            tasks_copy = [task.model_copy(deep=True) for task in self.tasks]

        if status:
            return [
                task for task in tasks_copy if task.status.lower() == status.lower()
            ]
        return tasks_copy

    def stats(self) -> Counter:
        """Return a Counter of shadow task statuses."""
        with self._lock:
            # Create stats from the internal list for consistency
            return Counter(task.status for task in self.tasks)

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Retrieves a specific shadow task by its ID."""
        with self._lock:
            for task in self.tasks:
                if task.task_id == task_id:
                    return task.model_copy(deep=True)  # Return copy
            return None

    def remove_task(self, task_id: str) -> bool:
        """Removes a task from the shadow backlog."""
        with self._lock:
            initial_len = len(self.tasks)
            self.tasks = [task for task in self.tasks if task.task_id != task_id]
            if len(self.tasks) < initial_len:
                self._save()
                logger.info(f"Removed shadow task {task_id}.")
                return True
            else:
                logger.warning(f"Shadow task {task_id} not found for removal.")
                return False


# Example usage / test block (optional, maybe remove for production agent code)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing ShadowTaskNexus...")
    # Ensure the test runs from a directory where PROJECT_ROOT can be resolved
    # or adjust the relative path calculation if necessary.
    # Example: Create a dummy shadow file for testing if needed.
    # test_file = Path("./temp_shadow_backlog.json")
    # if test_file.exists():
    #     test_file.unlink()

    # nexus = ShadowTaskNexus(task_file=test_file)
    nexus = ShadowTaskNexus()  # Use default path relative to calculated PROJECT_ROOT

    # Test add
    task1_data = {"task_id": "shadow-test-001", "description": "First shadow test task"}
    added_task = nexus.add_task(task1_data)
    print(f"Added Task: {added_task}")

    # Test get next
    next_t = nexus.get_next_task(agent_id="Agent-Test")
    print(f"Claimed Task: {next_t}")

    # Test update status
    if next_t:
        updated = nexus.update_task_status(
            next_t.task_id, "completed", result={"output": "success"}
        )
        print(f"Update Status Success: {updated}")

    # Test get by ID
    retrieved_task = nexus.get_task_by_id("shadow-test-001")
    print(f"Retrieved Task: {retrieved_task}")
    print(
        f"Retrieved Task Status: {retrieved_task.status if retrieved_task else 'Not Found'}"
    )

    # Test stats
    print(f"Stats: {nexus.stats()}")

    # Test remove
    # removed = nexus.remove_task("shadow-test-001")
    # print(f"Remove Task Success: {removed}")
    # print(f"Stats after remove: {nexus.stats()}")

    # Clean up test file if created
    # if test_file.exists():
    #      test_file.unlink()
    #      print(f"Cleaned up {test_file}")

    logger.info("ShadowTaskNexus test complete.")
