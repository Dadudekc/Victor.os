# Implementation Notes & Technical Debt

This document tracks outstanding implementation tasks, technical debt, known issues, and areas needing further development or refinement, primarily identified through `TODO`, `FIXME`, `NOTE`, and similar markers in the codebase.

## Areas with Outstanding Test TODOs

Numerous `TODO` comments indicate areas where test coverage could be improved. Key themes and locations include:

*   **Base Tooling (`tests/tools/test_base.py`):** Parameter validation, context handling.
*   **TODO/FIXME Discovery Tool (`tests/tools/discovery/test_find_todos.py`):** Testing the `scan_directory` function requires more setup.
*   **Cursor Bridge (`tests/tools/cursor_bridge/bridge_bootstrap_test.py`):** Needs tests for core bridge functions, timeout scenarios, image location success/failure, and potentially different OS platforms.
*   **Command Supervisor (`tests/supervisor_tools/test_command_supervisor.py`):** Testing large output and potential hangs.
*   **Project Board (`tests/core/comms/test_project_board.py`, `tests/core/coordination/tasks/test_project_board_manager.py`):** Error handling (validation, locking), edge cases (empty board), updating tasks on wrong boards, basic validation checks, global tasks, project-specific methods.
*   **Base Agent (`tests/core/coordination/test_base_agent.py`):** Testing core task processing loop (`_process_task_queue`, `_process_single_task`).
*   **Task Utilities (`tests/scripts/utils/test_simple_task_updater.py`):** Testing command-line arguments and potential mailbox interactions.
*   **UI (`tests/dashboard/test_dashboard_ui.py`):** Requires proper UI test setup or mocking.

*(This is not exhaustive. Refer to `grep` results for "TODO:" in the `tests/` directory for a full list.)*

## Code TODOs & FIXMEs

*   _(Scan of `src/` directory needed to identify non-test TODOs/FIXMEs. Initial `grep` focused heavily on tests)._

## Informational Notes & Context

Key `NOTE:` comments providing context were found in:

*   **Archived Scripts:** Various notes on assumptions, workarounds, and path dependencies (`_archive/scripts/...`).
*   **Command Supervisor Tests:** Notes on shell interaction, error reporting specifics, and test limitations (`tests/supervisor_tools/test_command_supervisor.py`).
*   **Template Engine Tests:** Note on Jinja loader redirection (`tests/rendering/test_template_engine.py`).
*   **Governance Memory Tests:** Note on log path redirection (`tests/memory/test_governance_memory_engine.py`).
*   **DB Manager Tests:** Note on SQLite boolean storage (`tests/memory/test_database_manager.py`).
*   **Project Board Tests:** Note regarding fixture renaming (`tests/coordination/test_project_board_manager.py`).
*   **Task Files (`TASKS.md`, `specs/PROJECT_PLAN.md`):** Notes regarding status updates and file locations.

## Planning & Structural TODOs

*   Several organizational and structural items marked `// TODO:` within the target structure definition in `specs/current_plan.md` have been converted into specific tasks (ORG-012 through ORG-025) on the main task list.

## Contributor Checklist

- [ ] ✅ Add notes on tricky implementations, non-obvious dependencies, or performance considerations.
- [ ] ✅ Document workarounds for bugs or limitations (internal or external).
- [ ] ✅ Record rationale for specific technical choices if not covered in ADRs.

## 📎 Linked Documents

- *(Link to relevant code files, PRs, or issue trackers)*
- *(Example: [Handling Rate Limits Notes](./implementation_notes/api_rate_limits.md))*

Specific notes related to the implementation details of certain modules, features, or integrations. 