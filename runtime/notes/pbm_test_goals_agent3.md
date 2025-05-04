# PBM Test Coverage Goals (Agent-3 for TEST-PBM-CORE-FUNCTIONS-001)

This document outlines the planned test coverage for `ProjectBoardManager`.

## Core CRUD Operations

- **Initialization:**
  - [x] `test_initialization`: Board initializes correctly with path, empty task list (mocked load).
- **Add Task:**
  - [x] `test_add_task_success`: Adds a valid task, verifies internal state and file dump.
  - [x] `test_add_task_duplicate_id_should_fail`: Raises appropriate error on duplicate ID, board state unchanged.
  - [ ] `test_add_task_invalid_schema`: Raises appropriate error if task schema is invalid (requires schema definition).
- **Get Task:**
  - [x] `test_get_task_success`: Retrieves existing task by ID.
  - [x] `test_get_task_not_found`: Raises `TaskNotFoundError` for non-existent ID.
- **Update Task Status:**
  - [x] `test_update_task_status_success`: Updates status of existing task, verifies internal state and file dump.
  - [x] `test_update_task_status_not_found`: Raises `TaskNotFoundError` for non-existent ID.
- **List Tasks:**
  - [x] `test_list_tasks_empty`: Returns empty list when board is empty.
  - [x] `test_list_tasks_with_data`: Returns correct list of tasks.

## Multi-Board Operations (Placeholders - Require PBM Logic Clarification)

- **Claim Future Task:**
  - [ ] `test_claim_future_task_success`: Moves task from future/ready board to working board.
  - [ ] `test_claim_future_task_not_found`: Fails correctly if task ID not in future/ready board.
  - [ ] `test_claim_future_task_already_working`: Fails if task ID already in working board.
- **Complete Task:**
  - [ ] `test_complete_task_success`: Moves task from working board to completed board (or updates status).
  - [ ] `test_complete_task_not_found`: Fails correctly if task ID not in working board.

## Error Handling & Edge Cases

- **Locking:**
  - [ ] `test_concurrent_access_contention`: Simulate lock contention (if possible with mocks) and verify behavior.
  - [ ] `test_operation_fails_if_lock_timeout`: Verify operations fail gracefully if lock cannot be acquired within timeout.
- **File I/O Errors:**
  - [ ] `test_load_board_file_not_found`: Handles missing board file on init/load.
  - [ ] `test_load_board_invalid_json`: Handles corrupted/invalid JSON during load.
  - [ ] `test_save_board_permission_error`: Handles errors during file write/replace (mock `os.replace` or `json.dump`).
- **Validation:**
  - [ ] Test cases for `TaskValidationError` on invalid status transitions, missing required fields, etc. (Requires PBM validation logic).
- **Empty Board:**
  - [x] Covered by `list_tasks_empty`, `get_task_not_found`, etc.

*This list will be updated as PBM implementation details (multi-board logic, specific error types, schema validation) are clarified.*
