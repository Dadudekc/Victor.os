# Proposal: Implement Centralized Project Board Manager

**Submitted by:** AgentGemini
**Date:** 2025-04-30

## Problem Statement

Current task management relies on direct manipulation of JSON files (`future_tasks.json`, `working_tasks.json`) or mandated tools (`ProjectBoardManager` utilities) that have proven inaccessible or unreliable. Direct JSON editing has led to file corruption, and the lack of functional, accessible tooling forces agents into workarounds (like mailbox communication for status updates) which lack central visibility and increase the risk of duplicated effort or missed tasks. This significantly hinders autonomous operation and swarm coordination.

Persistent issues encountered:
*   Inability to locate or access `future_tasks.json`.
*   Inability to use mandated `ProjectBoardManager` tools (location unknown or non-functional).
*   Risk of corruption with direct JSON file editing via tools.
*   Inability to reliably update task status on a central board.
*   Inaccessible agent mailboxes prevent receiving targeted directives or updates.

## Proposed Solution

Implement a robust, centralized `ProjectBoardManager` Python class within the core Dream.OS framework (`src/dreamos/coordination/`). This class will encapsulate all interactions with the task board JSON files, providing a stable and safe API for agents.

**Location:** `src/dreamos/coordination/project_board_manager.py`

**Key Features & Methods:**

*   **Class:** `ProjectBoardManager`
    *   `__init__(self, future_tasks_path="working_tasks.json", working_tasks_path="future_tasks.json")`: Initialize with paths to task files.
    *   `load_boards(self)`: Loads task data from JSON files into memory (e.g., pandas DataFrames or lists of dicts).
    *   `save_boards(self)`: Saves current in-memory task data back to JSON files, using file locking and atomic writes (write to temp file, then rename) to prevent corruption.
    *   `_acquire_lock(self)` / `_release_lock(self)`: Internal methods for file locking.
    *   `validate_task(self, task_data)`: Validates task data against the schema (`src/dreamos/coordination/tasks/task-schema.json`).
    *   `get_task(self, task_id)`: Retrieves a specific task by ID from either board.
    *   `list_future_tasks(self, status='unclaimed')`: Returns a list of tasks from `future_tasks.json` matching the status (e.g., 'unclaimed', 'pending').
    *   `list_working_tasks(self, agent_id=None)`: Returns tasks from `working_tasks.json`, optionally filtered by `agent_id`.
    *   `claim_task(self, task_id, agent_id)`: Moves a task from future to working board, assigning it to `agent_id`, updating status and history. Requires locking.
    *   `update_task(self, task_id, updates)`: Updates fields (status, description, history, etc.) of a task on the working board. Requires locking.
    *   `add_task(self, task_details, target_board='future')`: Adds a new task to the specified board after validation. Requires locking.
    *   `complete_task(self, task_id, summary, outputs)`: Marks a task as 'COMPLETED', adds final history entry. Optionally moves to an archive later.
    *   `archive_task(self, task_id)`: (Future enhancement) Moves a completed task from the working board to an archive.

**Technical Details:**
*   **Concurrency:** Use a file locking mechanism (e.g., `filelock` library or platform-specific modules like `fcntl`/`msvcrt`) to ensure safe concurrent access by multiple agents.
*   **Atomicity:** Implement atomic writes (write to temporary file, then rename/replace) to prevent data loss if an error occurs during saving.
*   **Schema Validation:** Integrate with the existing task schema (`task-schema.json`) for validation.
*   **Error Handling:** Implement robust error handling for file I/O, locking timeouts, and validation errors.
*   **Logging:** Add comprehensive logging for all board operations.

## Benefits

*   **Reliability:** Eliminates risks associated with direct JSON editing.
*   **Centralization:** Provides a single, consistent interface for task management.
*   **Concurrency Safe:** Prevents race conditions and data corruption.
*   **Visibility:** Enables accurate tracking of task status across the swarm.
*   **Autonomy:** Unblocks agents previously hindered by lack of task management tools.
*   **Maintainability:** Encapsulates task board logic in one place.

## Implementation Plan

1.  Define `ProjectBoardManager` class structure and methods.
2.  Implement file loading/saving with locking and atomic writes.
3.  Integrate schema validation.
4.  Implement core methods (`claim`, `update`, `add`, `list`, `get`).
5.  Add robust error handling and logging.
6.  Write unit tests.
7.  Document usage in `docs/tools/` or similar.

**Request:** Seeking approval to create and undertake the task `FEAT-IMPLEMENT-PROJECT-BOARD-MANAGER-001` to implement this proposal.
