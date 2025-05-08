# Project Board Manager API & Usage (v1.0)

**Component:** `src.dreamos.core.coordination.project_board_manager.ProjectBoardManager`
**Version:** 1.0
**Status:** Active

## 1. Purpose

The `ProjectBoardManager` provides a centralized mechanism for managing project tasks within the Dream.OS system. It persists tasks to a JSON Lines (JSONL) file and uses file locking (`filelock` library) to ensure safe concurrent read/write access by multiple agents or processes, preventing data corruption.

## 2. Initialization

Import the class and instantiate it. The board automatically loads existing tasks from its configured file upon initialization.

```python
from dreamos.core.coordination.project_board_manager import ProjectBoardManager
from dreamos.core.config import AppConfig

# Option 1: Using global AppConfig (Recommended)
# Assumes AppConfig is loaded and contains necessary paths
board_manager = ProjectBoardManager()

# Option 2: Providing an explicit AppConfig instance
# app_config = AppConfig(...) # Load specific config
# board_manager = ProjectBoardManager(config=app_config)

# Option 3: Specifying the task file path directly (Bypasses config for path)
# task_file = "/path/to/custom_task_board.jsonl"
# board_manager = ProjectBoardManager(task_file_path=task_file)
# Note: Lock file path will still be derived from config or default if using this option.
```

## 3. Configuration

The board manager relies on `AppConfig` for its file paths. Ensure the following keys are set (defaults are used if keys are missing):

*   **`coordination.project_board.task_board_file`**: 
    *   Description: Path to the JSONL file where tasks are stored.
    *   Default: `"runtime/coordination/central_task_board.jsonl"`
*   **`coordination.project_board.task_board_lock_file`**: 
    *   Description: Path to the file used for locking to ensure safe concurrent access.
    *   Default: `"runtime/coordination/central_task_board.lock"`

Relative paths are typically resolved relative to the `paths.runtime` directory specified in `AppConfig`.

## 4. Core Methods

### `add_task(task_data: Dict[str, Any]) -> Dict[str, Any]`

*   **Description:** Adds a new task to the board.
*   **Arguments:**
    *   `task_data`: A dictionary representing the new task.
*   **Behavior:**
    *   Assigns a unique `task_id` (e.g., `"task_<uuid>"`) if one is not provided in `task_data`.
    *   Adds `created_at` and `updated_at` ISO timestamps (UTC).
    *   Sets default `status` to `"TODO"` if not provided.
    *   Acquires a file lock, adds the task to the in-memory dictionary, and saves the entire board state back to the JSONL file.
    *   Includes a check for race conditions (re-checks if ID exists after acquiring lock).
*   **Returns:** The complete task dictionary as added to the board (including generated ID/timestamps).
*   **Raises:** `ValueError` (if `task_data` is not a dict or `task_id` is invalid), `ProjectBoardManagerError` (if task ID already exists).

### `get_task(task_id: str) -> Optional[Dict[str, Any]]`

*   **Description:** Retrieves a single task by its ID.
*   **Arguments:**
    *   `task_id`: The unique ID of the task to retrieve.
*   **Behavior:** Reads directly from the in-memory dictionary (no lock acquired for reads).
*   **Returns:** The task dictionary if found, otherwise `None`.
*   **Note:** Logs a warning if the task ID is not found.

### `get_all_tasks() -> List[Dict[str, Any]]`

*   **Description:** Retrieves a list of all tasks currently on the board.
*   **Behavior:** Returns a *copy* of the list of task dictionaries from memory (no lock acquired).
*   **Returns:** A list containing all task dictionaries.

### `update_task(task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]`

*   **Description:** Updates specific fields of an existing task.
*   **Arguments:**
    *   `task_id`: The ID of the task to update.
    *   `updates`: A dictionary where keys are the field names to update and values are the new values.
*   **Behavior:**
    *   Acquires a file lock.
    *   Finds the task by ID.
    *   Merges the `updates` into the existing task data (attempting to update `task_id` is ignored with a warning).
    *   Sets the `updated_at` timestamp to the current time (UTC).
    *   Saves the entire board state back to the JSONL file.
*   **Returns:** The fully updated task dictionary.
*   **Raises:** `TaskNotFoundError` (if `task_id` doesn't exist), `ValueError` (if `updates` is not a dict).

### `claim_task(task_id: str, agent_id: str) -> Dict[str, Any]`

*   **Description:** A convenience method to mark a task as claimed by an agent.
*   **Arguments:**
    *   `task_id`: The ID of the task to claim.
    *   `agent_id`: The ID of the agent claiming the task.
*   **Behavior:** Calls `update_task` with updates to set `status` to `"CLAIMED"`, `assignee` to `agent_id`, and adds a `claimed_at` timestamp.
*   **Returns:** The updated task dictionary.
*   **Raises:** `TaskNotFoundError`, `ValueError` (inherited from `update_task`).

### `complete_task(task_id: str, resolution_notes: Optional[str] = None) -> Dict[str, Any]`

*   **Description:** A convenience method to mark a task as completed.
*   **Arguments:**
    *   `task_id`: The ID of the task to complete.
    *   `resolution_notes`: Optional string containing notes about the task resolution.
*   **Behavior:** Calls `update_task` with updates to set `status` to `"DONE"`, adds a `completed_at` timestamp, and includes any `resolution_notes`.
*   **Returns:** The updated task dictionary.
*   **Raises:** `TaskNotFoundError`, `ValueError` (inherited from `update_task`).

## 5. Concurrency

The manager uses the `filelock` library to ensure that write operations (`add_task`, `update_task`, etc.) are atomic and prevent race conditions when multiple agents access the task board file simultaneously. A lock file (path configured via `coordination.project_board.task_board_lock_file`) is used for this purpose. Read operations (`get_task`, `get_all_tasks`) currently access the in-memory state and do not acquire the file lock, assuming that reads are safe against the locked write operations.

**Note:** If the `filelock` library is not installed, a warning will be logged upon initialization, and the board manager will operate without locking, making it unsafe for concurrent use.

## 6. Error Handling

The manager defines and raises custom exceptions:

*   `ProjectBoardManagerError`: Base class for board-related errors (e.g., lock timeout, save failure, duplicate task ID).
*   `TaskNotFoundError`: Raised by `update_task` (and thus `claim_task`, `complete_task`) if the specified `task_id` does not exist on the board.
*   `ValueError`: Raised by `add_task` or `update_task` if input arguments are invalid (e.g., not dictionaries).

## 7. Example Usage

```python
from dreamos.core.coordination.project_board_manager import ProjectBoardManager, TaskNotFoundError

# Assume board_manager is initialized (e.g., board_manager = ProjectBoardManager())

# Add a new task
new_task_data = {
    "title": "Refactor Swarm Sync Module",
    "description": "Move constants to AppConfig and align protocol.",
    "priority": "High",
    "assigned_to_capability": ["refactoring", "coordination"],
}
try:
    added_task = board_manager.add_task(new_task_data)
    task_id = added_task['task_id']
    print(f"Added task: {task_id}")

    # Get the task
    retrieved_task = board_manager.get_task(task_id)
    if retrieved_task:
        print(f"Retrieved task status: {retrieved_task.get('status')}")

    # Claim the task
    agent_id = "Agent_RefactorMaster"
    claimed_task = board_manager.claim_task(task_id, agent_id)
    print(f"Task {task_id} claimed by {claimed_task.get('assignee')}")

    # Update the task
    update_data = {"status": "IN_PROGRESS", "progress_notes": "Config refactoring done."}
    updated_task = board_manager.update_task(task_id, update_data)
    print(f"Task {task_id} updated. Status: {updated_task.get('status')}")

    # Complete the task
    completed_task = board_manager.complete_task(task_id, resolution_notes="Protocol aligned.")
    print(f"Task {task_id} completed at {completed_task.get('completed_at')}")

    # Get all tasks
    all_tasks = board_manager.get_all_tasks()
    print(f"\nTotal tasks on board: {len(all_tasks)}")

except ProjectBoardManagerError as e:
    print(f"Project Board Error: {e}")
except ValueError as e:
    print(f"Value Error: {e}") 