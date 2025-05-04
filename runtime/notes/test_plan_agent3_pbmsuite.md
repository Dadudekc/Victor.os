# Project Board Manager Test Plan (Agent-3)

**Task:** TEST-PBM-CORE-FUNCTIONS-001

This plan outlines the testing strategy for `dreamos.core.coordination.project_board_manager.ProjectBoardManager`.

## Core Methods & Test Strategy

### 1. `__init__(self, board_file_path)`
- **Purpose:** Initializes the PBM instance, loads the board from file.
- **Test Case:** `test_initialization`
  - **Required Mocks:** `os.path.exists`, `open`, `json.load`, `FileLock`.
  - **Edge Cases:** File doesn't exist (handled?), invalid JSON in file, empty file.
  - **Failure Modes:** `FileNotFoundError`, `json.JSONDecodeError`, `PermissionError`.
  - **State Transitions:** `self._tasks` populated, `self.board_file_path` set.
  - **Test Goal:** Verify correct initialization with mocked empty board.

### 2. `add_task(self, task_data)`
- **Purpose:** Adds a new task to the board, validating ID uniqueness and saving.
- **Test Cases:**
  - `test_add_task_success`
    - **Required Mocks:** `open`, `json.dump`, `os.replace`, `FileLock`.
    - **Edge Cases:** Adding to empty board.
    - **Failure Modes:** Lock acquisition failure, dump/replace failure (`IOError`, `PermissionError`).
    - **State Transitions:** Task added to `self._tasks`, file saved.
    - **Test Goal:** Verify task added internally, lock used, dump called correctly.
  - `test_add_task_duplicate_id_should_fail`
    - **Required Mocks:** `open`, `json.load`, `FileLock` (for initial load).
    - **Edge Cases:** N/A.
    - **Failure Modes:** Should raise `ValueError` (or `TaskValidationError`).
    - **State Transitions:** `self._tasks` remains unchanged, no save attempted.
    - **Test Goal:** Verify correct error raised, board unchanged, no dump call.
  - `test_add_task_invalid_schema` (TODO)
    - **Required Mocks:** TBD (depends on schema validation implementation).
    - **Edge Cases:** Missing required fields, incorrect data types.
    - **Failure Modes:** Should raise `TaskValidationError`.
    - **State Transitions:** `self._tasks` unchanged, no save.
    - **Test Goal:** Verify schema validation failure raises correct error.

### 3. `get_task(self, task_id)`
- **Purpose:** Retrieves a specific task by its ID.
- **Test Cases:**
  - `test_get_task_success`
    - **Required Mocks:** `open`, `json.load`, `FileLock` (for load).
    - **Edge Cases:** N/A.
    - **Failure Modes:** Lock acquisition failure.
    - **State Transitions:** None (read-only).
    - **Test Goal:** Verify correct task data is returned.
  - `test_get_task_not_found`
    - **Required Mocks:** `open`, `json.load`, `FileLock` (for load).
    - **Edge Cases:** Empty board.
    - **Failure Modes:** Should raise `TaskNotFoundError`.
    - **State Transitions:** None.
    - **Test Goal:** Verify correct error raised for non-existent ID.

### 4. `update_task_status(self, task_id, new_status)`
- **Purpose:** Updates the status of an existing task and saves the board.
- **Test Cases:**
  - `test_update_task_status_success`
    - **Required Mocks:** `open`, `json.load`, `json.dump`, `os.replace`, `FileLock`.
    - **Edge Cases:** Updating to same status.
    - **Failure Modes:** `TaskNotFoundError`, Lock failure, Dump/replace failure.
    - **State Transitions:** Task status updated in `self._tasks`, file saved.
    - **Test Goal:** Verify status updated internally, lock used, dump called correctly.
  - `test_update_task_status_not_found`
    - **Required Mocks:** `open`, `json.load`, `FileLock` (for load).
    - **Edge Cases:** Empty board.
    - **Failure Modes:** Should raise `TaskNotFoundError`.
    - **State Transitions:** `self._tasks` unchanged, no save.
    - **Test Goal:** Verify correct error raised, board unchanged, no dump call.
  - `test_update_task_status_invalid_transition` (TODO)
    - **Required Mocks:** (As above, depends on validation logic).
    - **Edge Cases:** Attempting invalid transitions (e.g., COMPLETED -> WORKING).
    - **Failure Modes:** Should raise `TaskValidationError`.
    - **State Transitions:** `self._tasks` unchanged, no save.
    - **Test Goal:** Verify validation prevents invalid status changes.

### 5. `list_tasks(self)`
- **Purpose:** Returns a list of all tasks currently on the board.
- **Test Cases:**
  - `test_list_tasks_empty`
    - **Required Mocks:** `open`, `json.load`, `FileLock` (for load).
    - **Edge Cases:** N/A.
    - **Failure Modes:** Lock failure, Load failure.
    - **State Transitions:** None.
    - **Test Goal:** Verify returns empty list for empty board.
  - `test_list_tasks_with_data`
    - **Required Mocks:** `open`, `json.load`, `FileLock` (for load).
    - **Edge Cases:** N/A.
    - **Failure Modes:** Lock failure, Load failure.
    - **State Transitions:** None.
    - **Test Goal:** Verify returns correct list of tasks.

### 6. `claim_future_task(self, task_id, agent_id)` (Placeholder)
- **Purpose:** Moves a task from a future/ready state to a working state (potentially involves multiple board files).
- **Test Cases:**
  - `test_claim_future_task_success`
    - **Required Mocks:** `open`, `json.load`, `json.dump`, `os.replace`, `FileLock` (potentially for multiple board files).
    - **Edge Cases:** Claiming last task from future/ready.
    - **Failure Modes:** `TaskNotFoundError` (if not in future/ready), `TaskValidationError` (if already claimed/working), Lock failure, I/O errors.
    - **State Transitions:** Task removed from future/ready board, task added/updated in working board.
    - **Test Goal:** Verify task moves correctly between (mocked) boards, state updated, files saved.
  - `test_claim_future_task_not_found`
    - **Required Mocks:** `open`, `json.load`, `FileLock`.
    - **Edge Cases:** Empty future/ready board.
    - **Failure Modes:** Should raise `TaskNotFoundError`.
    - **State Transitions:** No change.
    - **Test Goal:** Verify correct error raised, no state change, no saves.
  - `test_claim_future_task_already_working` (TODO)
    - **Required Mocks:** `open`, `json.load`, `FileLock`.
    - **Edge Cases:** N/A.
    - **Failure Modes:** Should raise `TaskValidationError` or similar.
    - **State Transitions:** No change.
    - **Test Goal:** Verify attempting to claim an already working task fails correctly.

### 7. `complete_task(self, task_id, result_summary)` (Placeholder)
- **Purpose:** Moves a task from a working state to a completed state (potentially involves multiple board files).
- **Test Cases:**
  - `test_complete_task_success`
    - **Required Mocks:** `open`, `json.load`, `json.dump`, `os.replace`, `FileLock`.
    - **Edge Cases:** Completing the only working task.
    - **Failure Modes:** `TaskNotFoundError`, Lock failure, I/O errors.
    - **State Transitions:** Task removed from working board, task added/updated in completed board.
    - **Test Goal:** Verify task moves correctly, state updated, files saved.
  - `test_complete_task_not_found`
    - **Required Mocks:** `open`, `json.load`, `FileLock`.
    - **Edge Cases:** Empty working board.
    - **Failure Modes:** Should raise `TaskNotFoundError`.
    - **State Transitions:** No change.
    - **Test Goal:** Verify correct error raised, no state change, no saves.

## General Error Handling / Edge Cases (To be detailed)
- Locking errors
- File I/O errors (read/write)
- Validation errors (status transitions, etc.)
