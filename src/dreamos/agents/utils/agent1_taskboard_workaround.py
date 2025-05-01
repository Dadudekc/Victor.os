# src/dreamos/agents/utils/agent1_taskboard_workaround.py
import datetime  # Need datetime import
import json
import logging
import os
import tempfile  # Need tempfile import
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

# Placeholder for filelock if the real library isn't in Agent 1's context
# A robust implementation would try to import the actual library first
try:
    import filelock

    FILELOCK_AVAILABLE = True
    print("INFO: filelock library found and will be used.")
except ImportError:
    filelock = None
    FILELOCK_AVAILABLE = False
    print(
        "WARNING: filelock library not found. Using dummy lock (NOT concurrency-safe)."
    )

# Basic logger setup
logger = logging.getLogger("Agent1Workaround")
# Configure logging if needed (e.g., logging.basicConfig(level=logging.DEBUG))

# --- Configuration ---
# Define paths relative to a known root or use absolute paths if necessary
# Assuming execution context allows resolving relative paths from project root
try:
    # Try to determine project root based on this file's location
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
except NameError:
    # Fallback if __file__ is not defined (e.g., interactive environment)
    PROJECT_ROOT = Path(".").resolve()
    logger.warning(
        f"__file__ not defined, assuming project root is current dir: {PROJECT_ROOT}"
    )

WORKING_TASKS_PATH = (
    PROJECT_ROOT / "runtime/agent_comms/project_boards/working_tasks.json"
)
LOCK_TIMEOUT = 15  # seconds


# --- Dummy Lock (if filelock not available) ---
class _DummyLock:
    def __init__(self, path, timeout):
        self.path = path
        self.timeout = timeout

    def __enter__(self):
        logger.debug(f"DummyLock: Entering context for {self.path}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug(f"DummyLock: Exiting context for {self.path}")

    def acquire(self, timeout=None):
        logger.debug(f"DummyLock: Pretending to acquire lock for {self.path}")
        # Simulate potential timeout for testing
        # if random.random() < 0.1: raise Timeout(self.path)
        pass

    def release(self):
        logger.debug(f"DummyLock: Pretending to release lock for {self.path}")
        pass

    @property
    def is_locked(self):
        return False  # Dummy lock is never truly locked


# --- Locking Function ---
def _acquire_lock_local(lock_path_str: str, timeout: int = LOCK_TIMEOUT):
    """Acquires a file lock using filelock library if available, else uses dummy."""
    if FILELOCK_AVAILABLE:
        logger.debug(f"Attempting to acquire real filelock: {lock_path_str}")
        # Ensure lock directory exists
        lock_dir = Path(lock_path_str).parent
        try:
            lock_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Failed to create directory for lock file {lock_path_str}: {e}"
            )
            # Decide how to handle this - raise an error?
            raise IOError(f"Failed to create lock directory {lock_dir}") from e
        return filelock.FileLock(lock_path_str, timeout=timeout)
    else:
        logger.warning(f"Using dummy lock for {lock_path_str}")
        return _DummyLock(lock_path_str, timeout=timeout)


# --- Board Reading Function ---
def _read_board_local(board_path: Path) -> List[Dict[str, Any]]:
    """Reads the specified task board JSON file."""
    if not board_path.exists():
        logger.warning(f"Board file not found: {board_path}. Returning empty list.")
        return []
    try:
        with open(board_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return data
            else:
                logger.error(
                    f"Invalid format in {board_path}: Expected a list, got {type(data)}."
                )
                return []  # Or raise error? Return empty for now.
    except json.JSONDecodeError:
        logger.exception(
            f"Failed to decode JSON from {board_path}. Returning empty list."
        )
        return []
    except IOError:
        logger.exception(
            f"Failed to read board file {board_path}. Returning empty list."
        )
        return []
    except Exception:
        logger.exception(
            f"Unexpected error reading board file {board_path}. Returning empty list."
        )
        return []


# --- Board Writing Function (Simplified, focuses on update logic) ---
def _rewrite_memory_safely_local(
    board_path: Path, updated_tasks: List[Dict[str, Any]]
) -> bool:
    """
    Writes the updated list of tasks back to the specified board file.
    Assumes lock is ALREADY HELD by the caller. Uses atomic write.
    """
    temp_file_path = None
    try:
        # Write to a temporary file first
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=board_path.parent,
            delete=False,
            suffix=".tmp",
        ) as tf:
            temp_file_path = Path(tf.name)
            json.dump(updated_tasks, tf, indent=2)
            tf.flush()
            os.fsync(tf.fileno())  # Ensure data is written to disk

        # Atomically replace the original file
        os.replace(temp_file_path, board_path)
        logger.debug(
            f"Successfully wrote {len(updated_tasks)} tasks to {board_path} atomically."
        )
        return True
    except Exception:
        logger.exception(
            f"Failed during atomic write to {board_path} (temp: {temp_file_path})"
        )
        # Cleanup temp file if it exists after failure
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
                logger.debug(
                    f"Cleaned up temporary file {temp_file_path} after write failure."
                )
            except OSError:
                logger.exception(f"Failed to clean up temporary file {temp_file_path}")
        return False


# --- Main Update Function --- #
def update_global_task_local(
    task_id: str,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    result_summary: Optional[str] = None,
) -> bool:
    """
    Updates a task entry in the working_tasks.json file using file locking.
    Only updates provided fields (status, notes, result_summary).

    Args:
        task_id: The ID of the task to update.
        status: The new status (if provided).
        notes: New notes to append or overwrite (if provided).
        result_summary: The result summary (if provided).

    Returns:
        True if the update was successful, False otherwise.
    """
    logger.info(
        f"Attempting local update for task '{task_id}'. Status={status}, Notes={'Provided' if notes else 'None'}, Summary={'Provided' if result_summary else 'None'}"
    )
    lock_file_path = str(WORKING_TASKS_PATH) + ".lock"
    lock = _acquire_lock_local(lock_file_path)
    updated = False

    try:
        logger.debug(f"Acquiring lock for {WORKING_TASKS_PATH}...")
        # Use try-finally or context manager for lock release
        # lock.acquire() # This might block indefinitely if timeout isn't handled
        if FILELOCK_AVAILABLE:
            lock.acquire()  # Use filelock's acquire
        else:
            lock.acquire()  # Dummy acquire

        logger.debug(f"Lock acquired for {WORKING_TASKS_PATH}.")

        # Read current board state
        tasks = _read_board_local(WORKING_TASKS_PATH)
        if not tasks:
            logger.error(
                f"Working tasks board is empty or could not be read. Cannot update task {task_id}."
            )
            # Release lock before returning
            if lock.is_locked:
                lock.release()
            return False

        task_found = False
        for task in tasks:
            if task.get("task_id") == task_id:
                logger.debug(f"Found task {task_id}. Applying updates.")
                task_found = True
                update_applied = False
                if status is not None:
                    task["status"] = status
                    update_applied = True
                if notes is not None:
                    # Append notes or overwrite? Let's append for now.
                    task["notes"] = (
                        task.get("notes", "") + "\n[UPDATE] " + notes
                    ).strip()
                    update_applied = True
                if result_summary is not None:
                    task["result_summary"] = result_summary
                    update_applied = True

                if update_applied:
                    # Always update the timestamp when changes are made
                    task["timestamp_updated"] = (
                        datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
                    )
                    logger.debug(f"Task {task_id} updated in memory.")
                else:
                    logger.debug(f"No actual updates provided for task {task_id}.")
                break  # Exit loop once task is found and updated

        if not task_found:
            logger.warning(
                f"Task {task_id} not found in {WORKING_TASKS_PATH}. Cannot update."
            )
            # Release lock before returning
            if lock.is_locked:
                lock.release()
            return False  # Task not found is considered failure

        # Write the modified tasks back to the file (atomically)
        if _rewrite_memory_safely_local(WORKING_TASKS_PATH, tasks):
            logger.info(f"Successfully updated task {task_id} in {WORKING_TASKS_PATH}.")
            updated = True
        else:
            logger.error(
                f"Failed to write updates for task {task_id} back to {WORKING_TASKS_PATH}."
            )
            updated = False  # Write failed

    except Exception as e:
        # Catch potential lock timeouts or other errors
        # Note: filelock.Timeout needs specific handling if using it directly
        if FILELOCK_AVAILABLE and isinstance(e, filelock.Timeout):
            logger.error(f"Timeout acquiring lock for task {task_id}: {e}")
        else:
            logger.exception(
                f"An error occurred during update operation for task {task_id}: {e}"
            )
        updated = False  # Ensure updated is false on error
    finally:
        if lock.is_locked:
            lock.release()
            logger.debug(f"Lock released for {WORKING_TASKS_PATH}.")

    return updated


# Example usage (can be commented out or removed)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    test_task_id = "LINT-FLAKE8-FIXES-001"  # Example task ID from working board
    print(f"Attempting to update task: {test_task_id}")
    success = update_global_task_local(
        task_id=test_task_id,
        notes="Testing local update function via script execution.",
    )
    if success:
        print(f"Update successful for {test_task_id}.")
    else:
        print(f"Update failed for {test_task_id}.")
