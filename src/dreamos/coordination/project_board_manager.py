#!/usr/bin/env python3
"""Centralized manager for interacting with project task boards."""

import argparse  # Add argparse import
import datetime
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

try:
    import filelock

    FILELOCK_AVAILABLE = True
except ImportError:
    filelock = None  # Indicate that filelock is not available
    FILELOCK_AVAILABLE = False

try:
    import jsonschema
except ImportError:
    jsonschema = None  # Indicate library not available

# EDIT START: Import AppConfig
from ..core.config import AppConfig

# EDIT END
# EDIT START: Import central error types
from ..core.errors import (
    BoardLockError,
    ProjectBoardError,
    TaskNotFoundError,
    TaskValidationError,
)

# EDIT END

logger = logging.getLogger(__name__)

# Default paths relative to project root (assuming PROJECT_ROOT is defined elsewhere or passed in)  # noqa: E501
# Need to resolve how PROJECT_ROOT is accessed here. For now, assume relative paths are handled.  # noqa: E501
# The proposal uses runtime/config/config.yaml structure which defines PROJECT_ROOT.
# This utility might need access to AppConfig or a similar mechanism.
DEFAULT_FUTURE_TASKS_FILENAME = "future_tasks.json"  # Define filenames
DEFAULT_WORKING_TASKS_FILENAME = "working_tasks.json"
DEFAULT_COMPLETED_TASKS_FILENAME = (
    "completed_tasks.json"  # Add completed tasks filename
)
DEFAULT_TASK_BACKLOG_FILENAME = "task_backlog.json"  # New
DEFAULT_TASK_READY_QUEUE_FILENAME = "task_ready_queue.json"  # New
DEFAULT_LOCK_TIMEOUT = 15  # seconds


class ProjectBoardManager:
    """
    Manages loading, saving, and modifying tasks on JSON-based project boards.
    Ensures safe concurrent access via file locking.

    Supports Backlog, Ready Queue, Working, and Completed boards.
    """

    def __init__(
        self,
        config: AppConfig,  # Pass the full AppConfig object
        # Remove boards_base_dir and project_root as they are now derived from config
        # boards_base_dir: str | Path, # Deprecated
        # project_root: str | Path = ".", # Deprecated
        lock_timeout: int = DEFAULT_LOCK_TIMEOUT,
    ):
        """Initialize the board manager with paths and configuration from AppConfig."""
        self.config = config
        self.lock_timeout = lock_timeout

        # Derive paths from AppConfig
        self.project_root = (
            self.config.paths.project_root.resolve()
        )  # Still useful internally maybe
        self.boards_base_dir = self.config.paths.central_task_boards.resolve()

        # Define board paths using config
        self.backlog_path = self.boards_base_dir / DEFAULT_TASK_BACKLOG_FILENAME
        self.ready_queue_path = self.boards_base_dir / DEFAULT_TASK_READY_QUEUE_FILENAME
        self.working_tasks_path = self.boards_base_dir / DEFAULT_WORKING_TASKS_FILENAME
        self.completed_tasks_path = (
            self.boards_base_dir / DEFAULT_COMPLETED_TASKS_FILENAME
        )

        # Define lock paths (remain derived from board paths)
        self.backlog_lock_path = self.backlog_path.with_suffix(
            self.backlog_path.suffix + ".lock"
        )
        self.ready_queue_lock_path = self.ready_queue_path.with_suffix(
            self.ready_queue_path.suffix + ".lock"
        )
        self.working_lock_path = self.working_tasks_path.with_suffix(
            self.working_tasks_path.suffix + ".lock"
        )
        self.completed_lock_path = self.completed_tasks_path.with_suffix(
            self.completed_tasks_path.suffix + ".lock"
        )
        # EDIT END

        logger.info("ProjectBoardManager initialized.")
        logger.info(f"  Using Configured Task Boards Dir: {self.boards_base_dir}")
        logger.info(f"  Backlog: {self.backlog_path.name}")
        logger.info(f"  Ready Queue: {self.ready_queue_path.name}")
        logger.info(f"  Working Tasks: {self.working_tasks_path}")
        logger.info(f"  Completed Tasks: {self.completed_tasks_path}")
        if not FILELOCK_AVAILABLE:
            logger.warning(
                "Filelock library not found. Board operations will not be fully concurrency-safe."  # noqa: E501
            )

        # Load the schema during initialization
        self._task_schema: Optional[Dict[str, Any]] = self._load_schema()

    def _resolve_path(self, path: str | Path) -> Path:
        """Resolves a path relative to the project root if not absolute."""
        p = Path(path)
        if p.is_absolute():
            return p
        else:
            # This assumes project_root is set correctly.
            # Consider using the pattern from config.py if AppConfig is accessible.
            return (self.project_root / p).resolve()

    def _get_lock(self, file_path: Path) -> filelock.FileLock | None:
        """Gets a file lock object for the given path, if available."""
        if not FILELOCK_AVAILABLE:
            return None

        # Determine lock path based on file path
        if file_path == self.backlog_path:
            lock_path = self.backlog_lock_path
        elif file_path == self.ready_queue_path:
            lock_path = self.ready_queue_lock_path
        elif file_path == self.working_tasks_path:
            lock_path = self.working_lock_path
        elif file_path == self.completed_tasks_path:
            lock_path = self.completed_lock_path
        else:
            # Fallback for other files, though primarily board files expected
            lock_path = file_path.with_suffix(file_path.suffix + ".lock")
            logger.warning(
                f"Generating fallback lock path for non-standard board file: {file_path}"  # noqa: E501
            )

        try:
            return filelock.FileLock(lock_path, timeout=self.lock_timeout)
        except Exception as e:
            logger.error(
                f"Failed to create FileLock object for {lock_path}: {e}", exc_info=True
            )
            # EDIT: Use imported central error
            raise ProjectBoardError(f"Failed to initialize lock for {lock_path}") from e

    def _load_file(self, file_path: Path) -> list[dict]:
        """Loads JSON data from a file, handling locking and errors."""
        lock = self._get_lock(file_path)
        loaded_data = []
        lock_acquired_by_us = False  # Track if we acquired the lock

        try:
            if lock:
                logger.debug(f"Acquiring lock for reading {file_path}...")
                lock.acquire()
                lock_acquired_by_us = True
                logger.debug(f"Lock acquired for {file_path}.")

            # Use _read_board_file helper inside the lock
            loaded_data = self._read_board_file(file_path)
            logger.debug(
                f"Loaded {len(loaded_data)} tasks from {file_path.name} using helper (within lock)."  # noqa: E501
                if lock_acquired_by_us
                else f"Loaded {len(loaded_data)} tasks from {file_path.name} using helper (no lock)."  # noqa: E501
            )

        except filelock.Timeout as e:  # Specifically catch lock timeout
            logger.error(f"Timeout acquiring lock for {file_path}: {e}")
            # EDIT: Use imported central error
            raise BoardLockError(f"Timeout acquiring lock for {file_path}") from e
        except Exception as e:  # Catch other potential errors during lock or read
            logger.error(f"Error during locked read of {file_path}: {e}", exc_info=True)
            # EDIT: Use imported central error
            raise ProjectBoardError(f"Failed during locked read of {file_path}") from e
        finally:
            # Only release the lock if we acquired it in this call
            if lock_acquired_by_us and lock.is_locked:
                try:
                    lock.release()
                    logger.debug(f"Lock released for {file_path}.")
                except Exception as e:
                    logger.error(
                        f"Failed to release lock for {file_path}: {e}", exc_info=True
                    )

        # Ensure return type consistency (though _read_board_file should already ensure it)  # noqa: E501
        return loaded_data if isinstance(loaded_data, list) else []

    # {{ EDIT START: Add helper for reading board files gracefully from core/comms version }}  # noqa: E501
    def _read_board_file(self, file_path: Path) -> list:
        """Reads a board file (JSON list), handling empty or corrupt files gracefully."""  # noqa: E501
        if not file_path.exists():
            logger.debug(
                f"Board file not found: {file_path.name}, returning empty list."
            )
            return []

        try:
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():  # Check if file is empty or only whitespace
                logger.warning(
                    f"Board file is empty: {file_path.name}, returning empty list."
                )
                # Optionally, attempt to write back `[]` here to self-heal
                return []
            # Ensure loaded content is a list
            loaded_data = json.loads(content)
            if not isinstance(loaded_data, list):
                logger.error(
                    f"Invalid task file format: Expected a JSON list in {file_path.name}, got {type(loaded_data)}."  # noqa: E501
                )
                # Consider self-healing by overwriting with []?
                return []
            return loaded_data
        except json.JSONDecodeError as e:
            logger.error(
                f"Error decoding JSON from {file_path.name}: {e}. Treating as empty list."  # noqa: E501
            )
            # TODO: Consider attempting to overwrite with `[]` to self-heal?
            return []
        except IOError as e:
            logger.error(
                f"IOError reading board file {file_path.name}: {e}. Returning empty list."  # noqa: E501
            )
            return []
        except Exception as e:
            logger.exception(
                f"Unexpected error reading board file {file_path.name}: {e}. Returning empty list."  # noqa: E501
            )
            return []

    # {{ EDIT END }}

    # --- Specific Load Methods (using _load_file) ---
    def _load_backlog(self) -> list[dict]:
        return self._load_file(self.backlog_path)

    def _load_ready_queue(self) -> list[dict]:
        return self._load_file(self.ready_queue_path)

    def _load_working_tasks(self) -> list[dict]:
        return self._load_file(self.working_tasks_path)

    def _load_completed_tasks(self) -> list[dict]:
        return self._load_file(self.completed_tasks_path)

    # --- Specific Save Methods (using _save_file) ---
    def _save_backlog(self, data: list[dict]):
        self._save_file(self.backlog_path, data)

    def _save_ready_queue(self, data: list[dict]):
        self._save_file(self.ready_queue_path, data)

    def _save_working_tasks(self, data: list[dict]):
        self._save_file(self.working_tasks_path, data)

    def _save_completed_tasks(self, data: list[dict]):
        self._save_file(self.completed_tasks_path, data)

    # Deprecate load_boards() as tasks are loaded on demand within methods
    # def load_boards(self):
    #     ...

    def _load_schema(self) -> Optional[Dict[str, Any]]:
        """Loads the task JSON schema file using path from AppConfig."""
        # EDIT START: Use AppConfig for schema path
        if (
            not self.config
            or not self.config.paths
            or not self.config.paths.task_schema
        ):
            logger.error(
                "Cannot load task schema: AppConfig or task_schema path not configured."
            )
            return None

        schema_path = self.config.paths.task_schema.resolve()
        # EDIT END

        try:
            # Determine schema path relative to this file or project root - REMOVED HARDCODED LOGIC  # noqa: E501
            # schema_path = Path(__file__).parent / "tasks" / "task-schema.json" # OLD

            if not schema_path.exists():
                # Fallback using project root (if available and different) - REMOVED FALLBACK  # noqa: E501
                # alt_path = ( ... ) # OLD
                # if alt_path.exists(): # OLD
                #    schema_path = alt_path # OLD
                # else: # OLD
                logger.error(
                    f"Task schema file not found at configured location: {schema_path}"
                )
                return None

            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
                logger.info(f"Task schema loaded successfully from {schema_path}.")
                return schema
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode task schema JSON from {schema_path}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Error loading task schema: {e}")
            return None

    def _validate_task(self, task_data: Dict[str, Any]) -> bool:
        """Validates task data against the loaded JSON schema."""
        if jsonschema is None:
            logger.warning("jsonschema library not found. Skipping task validation.")
            return True  # Skip validation if library is missing
        if self._task_schema is None:
            logger.warning("Task schema not loaded. Skipping task validation.")
            return True  # Skip validation if schema failed to load

        try:
            jsonschema.validate(instance=task_data, schema=self._task_schema)
            logger.debug(
                f"Task validation successful for task_id: {task_data.get('task_id', 'UNKNOWN')}"  # noqa: E501
            )
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.error(
                f"Task validation failed for task_id: {task_data.get('task_id', 'UNKNOWN')}: {e.message}"  # noqa: E501
            )
            # EDIT: Use imported central error
            raise TaskValidationError(
                f"Task {task_data.get('task_id', 'UNKNOWN')} failed schema validation: {e.message}"  # noqa: E501
            ) from e
        except Exception as e:
            logger.exception(f"Unexpected error during task validation: {e}")
            return False

    def _find_task_index(
        self, tasks: List[Dict[str, Any]], task_id: str
    ) -> Optional[int]:
        """Finds the index of a task by ID in a list of tasks."""
        for i, task in enumerate(tasks):
            if isinstance(task, dict) and task.get("task_id") == task_id:
                return i
        return None

    def _atomic_write(self, file_path: Path, data: list[dict]):
        """Writes data to a file atomically using a temporary file and rename."""
        # Create a temporary file in the same directory
        temp_file_path = file_path.with_suffix(f".tmp_{uuid.uuid4().hex}")
        try:
            with open(temp_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)  # Use indent for readability
            # Attempt to replace the original file with the temporary file
            os.replace(temp_file_path, file_path)
            logger.debug(f"Atomically wrote to {file_path}")
        except OSError as e:
            # EDIT: Use imported central error
            raise ProjectBoardError(
                f"Failed to create parent directory {file_path.parent}: {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error during atomic write to {file_path} (temp: {temp_file_path}): {e}",  # noqa: E501
                exc_info=True,
            )
            # Clean up temp file on any other error
            if temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except OSError as unlink_e:
                    logger.error(
                        f"Failed to remove temporary file {temp_file_path}: {unlink_e}"
                    )
            # EDIT: Use imported central error
            raise ProjectBoardError(
                f"Unexpected atomic write failure for {file_path}: {e}"
            ) from e

    def _save_file(self, file_path: Path, data: list[dict]):
        """Saves JSON data to a file, handling locking and atomic writes."""
        # Basic type check before attempting to save
        if not isinstance(data, list):
            raise TypeError(f"Data to save must be a list, got {type(data)}")

        lock = self._get_lock(file_path)
        lock_acquired_by_us = False

        try:
            if lock:
                logger.debug(f"Acquiring lock for writing {file_path}...")
                lock.acquire()
                lock_acquired_by_us = True
                logger.debug(f"Lock acquired for {file_path}.")

            # Use atomic write helper inside the lock
            self._atomic_write(file_path, data)
            logger.debug(
                f"Saved {len(data)} tasks to {file_path.name} using atomic write (within lock)."  # noqa: E501
                if lock_acquired_by_us
                else f"Saved {len(data)} tasks to {file_path.name} using atomic write (no lock)."  # noqa: E501
            )

        except filelock.Timeout as e:
            logger.error(f"Timeout acquiring lock for {file_path}: {e}")
            # EDIT: Use imported central error
            raise BoardLockError(f"Timeout acquiring lock for {file_path}") from e
        except TaskValidationError as e:  # Catch specific validation errors
            # Already logged in _validate_task, just re-raise
            raise e
        except Exception as e:
            logger.error(
                f"Error during locked write to {file_path}: {e}", exc_info=True
            )
            # EDIT: Use imported central error
            raise ProjectBoardError(f"Failed during locked write to {file_path}") from e
        finally:
            if lock_acquired_by_us and lock.is_locked:
                try:
                    lock.release()
                    logger.debug(f"Lock released for {file_path}.")
                except Exception as e:
                    logger.error(
                        f"Failed to release lock for {file_path}: {e}", exc_info=True
                    )

    # Deprecate save_boards() as tasks are saved individually by methods
    # def save_boards(self):
    #    ...

    # ... (_dummy_lock context manager might be useful for multi-file ops later) ...

    def get_task(
        self,
        task_id: str,
        board: Literal["backlog", "ready", "working", "completed", "any"] = "any",
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a single task by ID from specified or any board."""
        # Load boards dynamically if not already in memory (or always load)
        # For simplicity, load each board required based on the 'board' parameter
        logger.debug(f"Searching for task {task_id} on board(s): {board}")

        task = None
        if board in ["backlog", "any"]:
            backlog = self._load_backlog()
            task = next((t for t in backlog if t.get("task_id") == task_id), None)
            if task:
                logger.debug(f"Found task {task_id} in backlog.")
                return task

        if board in ["ready", "any"]:
            ready_queue = self._load_ready_queue()
            task = next((t for t in ready_queue if t.get("task_id") == task_id), None)
            if task:
                logger.debug(f"Found task {task_id} in ready queue.")
                return task

        if board in ["working", "any"]:
            working = self._load_working_tasks()
            task = next((t for t in working if t.get("task_id") == task_id), None)
            if task:
                logger.debug(f"Found task {task_id} in working tasks.")
                return task

        if board in ["completed", "any"]:
            completed = self._load_completed_tasks()
            task = next((t for t in completed if t.get("task_id") == task_id), None)
            if task:
                logger.debug(f"Found task {task_id} in completed tasks.")
                return task

        logger.debug(f"Task {task_id} not found on specified board(s): {board}")
        # EDIT: Use imported central error
        raise TaskNotFoundError(
            f"Task ID '{task_id}' not found on any board checked ({board})."
        )
        return None

    # Remove list_future_tasks
    # def list_future_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
    #     ...

    def list_backlog_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists tasks on the backlog, optionally filtering by status."""
        backlog = self._load_backlog()
        if status:
            return [t for t in backlog if t.get("status", "").upper() == status.upper()]
        else:
            return backlog

    def list_ready_queue_tasks(
        self, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists tasks on the ready queue, optionally filtering by status."""
        ready_queue = self._load_ready_queue()
        if status:
            return [
                t for t in ready_queue if t.get("status", "").upper() == status.upper()
            ]
        else:
            return ready_queue

    def list_working_tasks(
        self, agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists tasks on the working board, optionally filtering by agent ID."""
        working = self._load_working_tasks()
        if agent_id:
            # Check both assigned_agent and claimed_by for flexibility
            return [
                t
                for t in working
                if t.get("assigned_agent") == agent_id
                or t.get("claimed_by") == agent_id
            ]
        else:
            return working

    # ... (_add_history remains the same) ...
    # ... (_find_task_index remains the same) ...

    # Update add_task to add to backlog by default
    def add_task(self, task_details: dict[str, Any], agent_id: str) -> bool:
        """Adds a new task to the Task Backlog board."""
        return self.add_task_to_backlog(task_details, agent_id)

    # New method to specifically add to backlog
    def add_task_to_backlog(self, task_details: dict[str, Any], agent_id: str) -> bool:
        """Adds a new task specifically to the Task Backlog board."""
        # Validate the incoming task details first
        if not self._validate_task(task_details):
            # Validation error already logged by _validate_task
            return False

        # Add standard metadata
        task_id = task_details.get("task_id", self._generate_task_id())
        now = self._get_utc_timestamp()  # Use consistent timestamp helper

        new_task = {
            "task_id": task_id,
            "name": task_details.get("name", "Untitled Task"),
            "description": task_details.get("description", ""),
            "priority": task_details.get("priority", "MEDIUM"),
            "status": task_details.get(
                "status", "PENDING"
            ),  # Default PENDING for backlog
            "assigned_agent": task_details.get("assigned_agent"),  # Can be pre-assigned
            "task_type": task_details.get("task_type"),
            "dependencies": task_details.get("dependencies", []),
            "notes": task_details.get("notes", ""),
            "created_by": agent_id,
            "created_at": now,
            "timestamp_updated": now,
            # Include any other fields passed in task_details not explicitly handled
            **{
                k: v
                for k, v in task_details.items()
                if k
                not in [
                    "task_id",
                    "name",
                    "description",
                    "priority",
                    "status",
                    "assigned_agent",
                    "task_type",
                    "dependencies",
                    "notes",
                    "created_by",
                    "created_at",
                    "timestamp_updated",
                ]
            },
        }

        # Double-check validation after adding metadata (optional but safer)
        if not self._validate_task(new_task):
            logger.warning(
                f"Task {task_id} failed validation *after* adding metadata. Aborting add."  # noqa: E501
            )
            return False

        try:
            backlog = self._load_backlog()

            # Check for duplicate ID before adding
            if any(t.get("task_id") == task_id for t in backlog):
                logger.error(
                    f"Task ID {task_id} already exists in the backlog. Cannot add duplicate."  # noqa: E501
                )
                # EDIT: Use imported central error
                raise ProjectBoardError(f"Duplicate Task ID {task_id} in backlog.")

            backlog.append(new_task)
            self._save_backlog(backlog)
            logger.info(f"Task {task_id} added to backlog by {agent_id}.")
            return True
        except (BoardLockError, TaskValidationError, ProjectBoardError) as e:
            logger.error(f"Failed to add task {task_id} to backlog: {e}")
            raise e  # Re-raise instead of returning False
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred adding task to backlog: {e}"
            )
            # EDIT: Wrap unexpected exceptions in PBM error
            raise ProjectBoardError(f"Failed to add task to backlog: {e}") from e

    def _get_utc_timestamp(self) -> str:
        """Returns the current UTC time as an ISO 8601 string."""
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _generate_task_id(self) -> str:
        """Generates a unique task ID."""
        # Simple UUID for now, could customize prefix/format later
        return str(uuid.uuid4())

    # update_task should probably be renamed update_working_task for clarity
    def update_working_task(self, task_id: str, updates: dict[str, Any]) -> bool:
        """Updates fields of a task on the working board."""
        if not updates:
            logger.warning("No updates provided for update_working_task.")
            return False

        try:
            working_tasks = self._load_working_tasks()
            task_index = self._find_task_index(working_tasks, task_id)

            if task_index is None:
                logger.error(
                    f"Task ID {task_id} not found in working tasks for update."
                )
                # EDIT: Use imported central error
                raise TaskNotFoundError(f"Task {task_id} not found in working board.")

            original_task = working_tasks[task_index].copy()

            # Ensure timestamp_updated is always set
            updates["timestamp_updated"] = self._get_utc_timestamp()

            # Apply updates
            updated_task = original_task.copy()
            updated_task.update(updates)

            # Validate the updated task structure (optional but recommended)
            if not self._validate_task(updated_task):
                logger.error(
                    f"Updated task {task_id} failed validation. Aborting update."
                )
                # Optionally rollback or log details of validation failure
                return False

            # Update the list in place
            working_tasks[task_index] = updated_task

            # Save the entire updated list back
            self._save_working_tasks(working_tasks)
            logger.info(f"Task {task_id} updated in working tasks.")
            # logger.debug(f"Task {task_id} updated with: {updates}")
            return True

        except (BoardLockError, TaskNotFoundError, TaskValidationError) as e:
            logger.error(f"Failed to update task {task_id} in working tasks: {e}")
            raise e  # Re-raise instead of returning False
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred updating working task {task_id}: {e}"
            )
            # EDIT: Wrap unexpected exceptions in PBM error
            raise ProjectBoardError(
                f"Failed to update working task {task_id}: {e}"
            ) from e

    # delete_task needs updating for new boards
    def delete_task(
        self, task_id: str, agent_id: str, board: Literal["backlog", "ready", "working"]
    ) -> bool:
        """Deletes a task by ID from the specified board (backlog, ready, or working)."""  # noqa: E501
        target_path = None
        load_func = None
        save_func = None
        board_name = board

        if board == "backlog":
            target_path = self.backlog_path
            load_func = self._load_backlog
            save_func = self._save_backlog
        elif board == "ready":
            target_path = self.ready_queue_path
            load_func = self._load_ready_queue
            save_func = self._save_ready_queue
        elif board == "working":
            target_path = self.working_tasks_path  # noqa: F841
            load_func = self._load_working_tasks
            save_func = self._save_working_tasks
        else:
            logger.error(
                f"Invalid board specified for deletion: {board}. Must be 'backlog', 'ready', or 'working'."  # noqa: E501
            )
            # EDIT: Use imported central error
            raise ValueError("Invalid board for deletion")

        try:
            tasks = load_func()
            original_length = len(tasks)  # noqa: F841
            task_index = self._find_task_index(tasks, task_id)

            if task_index is None:
                logger.warning(
                    f"Task {task_id} not found on {board_name} board for deletion by {agent_id}."  # noqa: E501
                )
                # Return True as the task is already gone?
                # Or False because the delete action wasn't performed?
                # Let's return False to indicate the task wasn't found *to be* deleted.
                return False

            deleted_task = tasks.pop(task_index)  # noqa: F841
            logger.info(
                f"Task {task_id} removed from {board_name} board by {agent_id}."
            )
            # logger.debug(f"Deleted task details: {deleted_task}")

            # Save the modified list back
            save_func(tasks)
            return True

        except BoardLockError as e:
            logger.error(f"Failed to delete task {task_id} from {board_name}: {e}")
            raise e  # Re-raise instead of returning False
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred deleting task {task_id} from {board_name}."  # noqa: E501
            )
            # EDIT: Wrap unexpected exceptions in PBM error
            raise ProjectBoardError(
                f"Failed to delete task {task_id} from {board_name}: {e}"
            ) from e

    def move_task_to_completed(
        self, task_id: str, final_updates: dict[str, Any]
    ) -> bool:
        """Atomically moves a task from working to completed, applying final updates."""
        # Acquire locks for both working and completed boards
        working_lock = self._get_lock(self.working_tasks_path)
        completed_lock = self._get_lock(self.completed_tasks_path)
        working_lock_acquired = False
        completed_lock_acquired = False

        try:
            if working_lock:
                logger.debug(f"Acquiring lock for {self.working_tasks_path}...")
                working_lock.acquire()
                working_lock_acquired = True
                logger.debug(f"Lock acquired for {self.working_tasks_path}.")

            if completed_lock:
                logger.debug(f"Acquiring lock for {self.completed_tasks_path}...")
                # Use a shorter timeout for the second lock acquisition to avoid deadlock?  # noqa: E501
                # For now, use the standard timeout.
                completed_lock.acquire()
                completed_lock_acquired = True
                logger.debug(f"Lock acquired for {self.completed_tasks_path}.")

            # --- Critical Section (Both Locks Held) ---
            working_tasks = self._read_board_file(self.working_tasks_path)
            task_index = self._find_task_index(working_tasks, task_id)

            if task_index is None:
                logger.error(
                    f"Task {task_id} not found in working tasks to move to completed."
                )
                # EDIT: Use imported central error
                raise TaskNotFoundError(f"Task {task_id} not found in working tasks.")

            # Remove from working list
            task_to_move = working_tasks.pop(task_index)
            logger.debug(f"Task {task_id} removed from working list in memory.")

            # Apply final updates before adding to completed
            task_to_move.update(final_updates)
            # Ensure standard fields exist
            task_to_move["status"] = final_updates.get("status", "COMPLETED").upper()
            task_to_move["timestamp_completed_utc"] = final_updates.get(
                "timestamp_completed_utc", self._get_utc_timestamp()
            )
            task_to_move["timestamp_updated"] = (
                self._get_utc_timestamp()
            )  # Always update this
            if "completed_by" not in task_to_move and "agent_id" in final_updates:
                task_to_move["completed_by"] = final_updates["agent_id"]

            # Validate final task structure (optional)
            if not self._validate_task(task_to_move):
                logger.error(
                    f"Task {task_id} failed validation before moving to completed. Aborting move."  # noqa: E501
                )
                # How to handle rollback? Need careful thought.
                # For now, log and raise error.
                # EDIT: Use imported central error
                raise TaskValidationError(
                    f"Task {task_id} failed validation before completion."
                )

            # Add to completed list
            completed_tasks = self._read_board_file(self.completed_tasks_path)
            # Check for duplicates in completed? Generally okay to overwrite?
            # For simplicity, just append. Could add logic to update existing if preferred.  # noqa: E501
            completed_tasks.append(task_to_move)
            logger.debug(f"Task {task_id} added to completed list in memory.")

            # Save both files (atomicity handled by _atomic_write internally)
            self._atomic_write(self.working_tasks_path, working_tasks)
            logger.debug(
                f"Saved updated working tasks file ({self.working_tasks_path.name})."
            )
            self._atomic_write(self.completed_tasks_path, completed_tasks)
            logger.debug(
                f"Saved updated completed tasks file ({self.completed_tasks_path.name})."  # noqa: E501
            )
            # --- End Critical Section ---

            logger.info(f"Task {task_id} successfully moved to completed board.")
            return True

        except (BoardLockError, TaskNotFoundError, TaskValidationError) as e:
            logger.error(f"Failed to move task {task_id} to completed: {e}")
            # Rollback is complex here. Did we modify lists in memory?
            # Best effort: Log the failure. The state might be inconsistent if one save failed.  # noqa: E501
            raise e  # Re-raise instead of returning False
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred moving task {task_id} to completed."
            )
            # State might be inconsistent.
            # Attempt release
            if working_lock_acquired and working_lock.is_locked:
                try:
                    working_lock.release()
                except Exception:
                    pass
            if completed_lock_acquired and completed_lock.is_locked:
                try:
                    completed_lock.release()
                except Exception:
                    pass
            # EDIT: Wrap unexpected exceptions in PBM error
            raise ProjectBoardError(
                f"Failed to move task {task_id} to completed: {e}"
            ) from e

    # --- New Dual-Queue Methods ---
    def claim_ready_task(self, task_id: str, agent_id: str) -> bool:
        """Atomically claims a task from the ready queue and moves it to the working board."""  # noqa: E501
        logger.info(
            f"Agent {agent_id} attempting to claim task {task_id} from ready queue..."
        )
        ready_lock = self._get_lock(self.ready_queue_path)
        working_lock = self._get_lock(self.working_tasks_path)
        ready_lock_acquired = False
        working_lock_acquired = False
        task_to_move = None

        try:
            # Acquire locks (Ready Queue first, then Working)
            if ready_lock:
                logger.debug(f"Acquiring lock for {self.ready_queue_path}...")
                ready_lock.acquire()
                ready_lock_acquired = True
                logger.debug(f"Lock acquired for {self.ready_queue_path}.")
            else:
                # EDIT: Use imported central error
                raise BoardLockError("Ready queue lock unavailable.")

            if working_lock:
                logger.debug(f"Acquiring lock for {self.working_tasks_path}...")
                working_lock.acquire()
                working_lock_acquired = True
                logger.debug(f"Lock acquired for {self.working_tasks_path}.")
            else:
                # EDIT: Use imported central error
                raise BoardLockError("Working tasks lock unavailable.")

            # --- Critical Section (Both Locks Held) ---
            ready_queue = self._read_board_file(self.ready_queue_path)
            task_index = self._find_task_index(ready_queue, task_id)

            if task_index is None:
                logger.warning(
                    f"Task {task_id} not found in ready queue for claim by {agent_id}."
                )
                # Check if already working
                working_tasks_check = self._read_board_file(self.working_tasks_path)
                if self._find_task_index(working_tasks_check, task_id) is not None:
                    logger.info(
                        f"Task {task_id} is already in the working tasks board."
                    )
                    return False  # Or True depending on desired idempotency semantics?
                # EDIT: Use imported central error
                raise TaskNotFoundError(f"Task {task_id} not found in ready queue.")

            task_to_move = ready_queue.pop(task_index)
            logger.debug(f"Task {task_id} removed from ready queue list in memory.")

            # Check if task status is appropriate (e.g., PENDING)
            claimable_statuses = {"PENDING"}  # Define which statuses can be claimed
            # EDIT: Handle case-insensitivity
            current_status = task_to_move.get("status", "PENDING")
            if (
                current_status.upper() not in claimable_statuses
            ):  # Check uppercase status
                logger.warning(
                    f"Attempted to claim task {task_id} from ready queue with non-claimable status: {current_status}"  # noqa: E501
                )
                # Should we put it back? For now, log and fail.
                # EDIT: Use imported central error
                raise ProjectBoardError(
                    f"Task {task_id} has non-claimable status {current_status} in ready queue."  # noqa: E501
                )

            # Update task details for working board
            now = self._get_utc_timestamp()
            task_to_move["status"] = "WORKING"
            task_to_move["claimed_by"] = agent_id
            task_to_move["timestamp_claimed_utc"] = now
            task_to_move["timestamp_updated"] = now
            # Optionally add history entry
            # self._add_history(task_to_move, agent_id, "CLAIMED_FROM_READY") # EDIT: Commented out due to AttributeError  # noqa: E501

            # Validate before adding to working
            if not self._validate_task(task_to_move):
                logger.error(
                    f"Task {task_id} failed validation before adding to working tasks. Aborting claim."  # noqa: E501
                )
                # Need rollback strategy
                # EDIT: Use imported central error
                raise TaskValidationError(
                    f"Task {task_id} failed validation during claim."
                )

            # Add to working list
            working_tasks = self._read_board_file(self.working_tasks_path)
            working_tasks.append(task_to_move)
            logger.debug(f"Task {task_id} added to working tasks list in memory.")

            # Save both files (atomicity handled by _atomic_write internally)
            self._atomic_write(self.ready_queue_path, ready_queue)
            logger.debug(
                f"Saved updated ready queue file ({self.ready_queue_path.name})."
            )
            self._atomic_write(self.working_tasks_path, working_tasks)
            logger.debug(
                f"Saved updated working tasks file ({self.working_tasks_path.name})."
            )
            # --- End Critical Section ---

            logger.info(
                f"Task {task_id} successfully claimed by {agent_id} from ready queue."
            )
            return True

        except (BoardLockError, TaskNotFoundError, TaskValidationError) as e:
            logger.error(f"Failed to claim task {task_id} from ready queue: {e}")
            # TODO: Implement rollback if task_to_move is not None?
            # (e.g., add task_to_move back to ready_queue list and save only ready_queue)  # noqa: E501
            # Requires careful state management.
            raise e  # Re-raise instead of returning False
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred claiming task {task_id} from ready queue."  # noqa: E501
            )
            # TODO: Rollback?
            raise ProjectBoardError(f"Failed to claim ready task {task_id}: {e}") from e
        finally:
            # Release locks in reverse order
            if working_lock_acquired and working_lock.is_locked:
                try:
                    working_lock.release()
                    logger.debug(f"Lock released for {self.working_tasks_path}.")
                except Exception as e_rl:
                    logger.error(
                        f"Failed to release lock {self.working_lock_path}: {e_rl}"
                    )
            if ready_lock_acquired and ready_lock.is_locked:
                try:
                    ready_lock.release()
                    logger.debug(f"Lock released for {self.ready_queue_path}.")
                except Exception as e_rl:
                    logger.error(
                        f"Failed to release lock {self.ready_queue_lock_path}: {e_rl}"
                    )

    def promote_task_to_ready(self, task_id: str) -> bool:
        """Atomically moves a task from the backlog to the ready queue."""
        logger.info(
            f"Attempting to promote task {task_id} from backlog to ready queue..."
        )
        backlog_lock = self._get_lock(self.backlog_path)
        ready_lock = self._get_lock(self.ready_queue_path)
        backlog_lock_acquired = False
        ready_lock_acquired = False
        task_to_move = None

        try:
            # Acquire locks (Backlog first, then Ready Queue)
            if backlog_lock:
                logger.debug(f"Acquiring lock for {self.backlog_path}...")
                backlog_lock.acquire()
                backlog_lock_acquired = True
                logger.debug(f"Lock acquired for {self.backlog_path}.")
            else:
                # EDIT: Use imported central error
                raise BoardLockError("Backlog lock unavailable.")

            if ready_lock:
                logger.debug(f"Acquiring lock for {self.ready_queue_path}...")
                ready_lock.acquire()
                ready_lock_acquired = True
                logger.debug(f"Lock acquired for {self.ready_queue_path}.")
            else:
                # EDIT: Use imported central error
                raise BoardLockError("Ready queue lock unavailable.")

            # --- Critical Section (Both Locks Held) ---
            backlog = self._read_board_file(self.backlog_path)
            task_index = self._find_task_index(backlog, task_id)

            if task_index is None:
                logger.warning(f"Task {task_id} not found in backlog for promotion.")
                # EDIT: Use imported central error
                raise TaskNotFoundError(f"Task {task_id} not found in backlog.")

            task_to_move = backlog.pop(task_index)
            logger.debug(f"Task {task_id} removed from backlog list in memory.")

            # Check if task status is appropriate (e.g., PENDING)
            promotable_statuses = {"PENDING"}  # Define which statuses can be promoted
            # EDIT: Handle case-insensitivity
            current_status = task_to_move.get("status", "PENDING")
            if (
                current_status.upper() not in promotable_statuses
            ):  # Check uppercase status
                logger.warning(
                    f"Attempted to promote task {task_id} from backlog with non-promotable status: {current_status}"  # noqa: E501
                )
                # Put it back? Log and fail.
                # EDIT: Use imported central error
                raise ProjectBoardError(
                    f"Task {task_id} has non-promotable status {current_status} in backlog."  # noqa: E501
                )

            # Update task timestamp (optional, indicates promotion time)
            now = self._get_utc_timestamp()
            task_to_move["timestamp_updated"] = now
            task_to_move["notes"] = (
                task_to_move.get("notes", "") + f"\n[PROMOTED_TO_READY@{now}]"
            )  # Add note

            # Validate before adding to ready queue
            if not self._validate_task(task_to_move):
                logger.error(
                    f"Task {task_id} failed validation before adding to ready queue. Aborting promotion."  # noqa: E501
                )
                # Need rollback strategy
                # EDIT: Use imported central error
                raise TaskValidationError(
                    f"Task {task_id} failed validation during promotion."
                )

            # Add to ready queue list
            ready_queue = self._read_board_file(self.ready_queue_path)
            # Check for duplicates in ready queue?
            if any(t.get("task_id") == task_id for t in ready_queue):
                logger.error(
                    f"Task {task_id} already exists in the ready queue. Cannot promote duplicate."  # noqa: E501
                )
                # Need rollback strategy
                # EDIT: Use imported central error
                raise ProjectBoardError(f"Duplicate Task ID {task_id} in ready queue.")

            ready_queue.append(task_to_move)
            logger.debug(f"Task {task_id} added to ready queue list in memory.")

            # Save both files (atomicity handled by _atomic_write internally)
            self._atomic_write(self.backlog_path, backlog)
            logger.debug(f"Saved updated backlog file ({self.backlog_path.name}).")
            self._atomic_write(self.ready_queue_path, ready_queue)
            logger.debug(
                f"Saved updated ready queue file ({self.ready_queue_path.name})."
            )
            # --- End Critical Section ---

            logger.info(
                f"Task {task_id} successfully promoted from backlog to ready queue."
            )
            return True

        except (
            BoardLockError,
            TaskNotFoundError,
            TaskValidationError,
            ProjectBoardError,
        ) as e:
            logger.error(f"Failed to promote task {task_id}: {e}")
            # EDIT START: Implement Rollback
            if task_to_move is not None:
                logger.warning(
                    f"Attempting rollback for task {task_id} during promotion failure..."  # noqa: E501
                )
                try:
                    # Ensure backlog lock is still held if possible (should be if we got here)  # noqa: E501
                    if backlog_lock_acquired and backlog_lock.is_locked:
                        backlog = self._read_board_file(
                            self.backlog_path
                        )  # Re-read just in case
                        # Check if task was somehow already put back (unlikely but safe)
                        if not any(t.get("task_id") == task_id for t in backlog):
                            backlog.append(task_to_move)
                            logger.info(
                                f"Rollback: Re-added task {task_id} to backlog list."
                            )
                            # Save ONLY the backlog during rollback
                            self._atomic_write(self.backlog_path, backlog)
                            logger.info(
                                f"Rollback: Saved updated backlog ({self.backlog_path.name})."  # noqa: E501
                            )
                        else:
                            logger.warning(
                                f"Rollback skipped: Task {task_id} already found in backlog."  # noqa: E501
                            )
                    else:
                        logger.error("Rollback failed: Backlog lock not held.")
                except Exception as rb_err:
                    logger.error(
                        f"Error during promotion rollback for task {task_id}: {rb_err}",
                        exc_info=True,
                    )
            # EDIT END
            raise e  # Re-raise original exception
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred during task promotion for {task_id}."
            )
            # EDIT START: Implement Rollback for unexpected errors too
            if task_to_move is not None:
                logger.warning(
                    f"Attempting rollback for task {task_id} due to unexpected error..."
                )
                try:
                    if backlog_lock_acquired and backlog_lock.is_locked:
                        backlog = self._read_board_file(self.backlog_path)
                        if not any(t.get("task_id") == task_id for t in backlog):
                            backlog.append(task_to_move)
                            logger.info(
                                f"Rollback: Re-added task {task_id} to backlog list (unexpected error path)."  # noqa: E501
                            )
                            self._atomic_write(self.backlog_path, backlog)
                            logger.info(
                                "Rollback: Saved updated backlog (unexpected error path)."  # noqa: E501
                            )
                        else:
                            logger.warning(
                                f"Rollback skipped: Task {task_id} already found in backlog (unexpected error path)."  # noqa: E501
                            )
                    else:
                        logger.error(
                            "Rollback failed: Backlog lock not held (unexpected error path)."  # noqa: E501
                        )
                except Exception as rb_err:
                    logger.error(
                        f"Error during promotion rollback for task {task_id} (unexpected error path): {rb_err}",  # noqa: E501
                        exc_info=True,
                    )
            # EDIT END
            # Wrap unexpected exceptions in PBM error
            raise ProjectBoardError(
                f"Promotion failed unexpectedly for task {task_id}: {e}"
            ) from e
        finally:
            # Release locks in reverse order
            if ready_lock_acquired and ready_lock.is_locked:
                try:
                    ready_lock.release()
                    logger.debug(f"Lock released for {self.ready_queue_path}.")
                except Exception as e_rl:
                    logger.error(
                        f"Failed to release lock {self.ready_queue_lock_path}: {e_rl}"
                    )
            if backlog_lock_acquired and backlog_lock.is_locked:
                try:
                    backlog_lock.release()
                    logger.debug(f"Lock released for {self.backlog_path}.")
                except Exception as e_rl:
                    logger.error(
                        f"Failed to release lock {self.backlog_lock_path}: {e_rl}"
                    )

    # EDIT START: Update CLI section to load config
    @classmethod
    def _create_from_cli_args(cls, args):
        """Helper to create an instance using AppConfig for CLI."""
        try:
            config = AppConfig.load()  # Load default config
            # Override board dir if provided via CLI? For now, use config's value.
            # boards_dir = args.boards_dir if args.boards_dir else config.paths.central_task_boards  # noqa: E501
            return cls(config=config, lock_timeout=args.lock_timeout)
        except Exception as e:
            logger.error(
                f"Failed to initialize ProjectBoardManager via AppConfig for CLI: {e}",
                exc_info=True,
            )
            sys.exit(1)  # Exit if config fails for CLI

    # EDIT END


# Note: The __main__ block itself needs modification to use _create_from_cli_args
if __name__ == "__main__":
    # ... (Existing argparse setup)
    parser = argparse.ArgumentParser(description="Manage Project Boards")
    parser.add_argument(
        "--boards-dir",
        type=str,
        # default=".", # Default now comes from AppConfig
        help="Base directory for board JSON files (default taken from AppConfig)",
    )
    parser.add_argument(
        "--lock-timeout",
        type=int,
        default=DEFAULT_LOCK_TIMEOUT,
        help="Timeout in seconds for acquiring file locks",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    # Example: list command
    parser_list = subparsers.add_parser("list", help="List tasks from a board")
    parser_list.add_argument(
        "board",
        choices=["backlog", "ready", "working", "completed"],
        help="Which board to list",
    )
    parser_list.add_argument("--status", type=str, help="Filter by status")
    parser_list.add_argument(
        "--agent", type=str, help="Filter by agent_id (working board)"
    )

    # Add parsers for other commands (add, get, update, move, delete, claim, promote)
    # ... (Need to define parsers for all commands for CLI to be complete) ...

    args = parser.parse_args()

    # Configure logging simply for CLI
    logging.basicConfig(
        level=logging.INFO if not args.verbose else logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create instance using AppConfig via helper
    pbm = ProjectBoardManager._create_from_cli_args(args)

    # Execute command based on args.command
    if args.command == "list":
        tasks = []
        if args.board == "backlog":
            tasks = pbm.list_backlog_tasks(status=args.status)
        elif args.board == "ready":
            tasks = pbm.list_ready_queue_tasks(status=args.status)
        elif args.board == "working":
            tasks = pbm.list_working_tasks(agent_id=args.agent)
        # elif args.board == "completed": # Need list_completed_tasks method if desired
        #     tasks = pbm.list_completed_tasks() # Assuming method exists
        print(json.dumps(tasks, indent=2))
    # Add elif blocks for other commands (add, get, etc.)
    # elif args.command == 'add':
    #     # Requires defining parser_add and handling its arguments
    #     details = json.loads(args.task_details) # Assuming details passed as JSON string  # noqa: E501
    #     agent = args.agent_id
    #     if pbm.add_task_to_backlog(details, agent):
    #         print("Task added successfully.")
    #     else:
    #         print("Failed to add task.")
    #         sys.exit(1)
    else:
        print(f"Command '{args.command}' not fully implemented in CLI or unknown.")
        if not args.command:
            parser.print_help()
# EDIT END: Note changes needed in CLI __main__ block if used.
