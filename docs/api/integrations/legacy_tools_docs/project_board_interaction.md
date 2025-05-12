# Project Board Interaction

This document outlines how agents should interact with the shared project
boards, emphasizing the current dual-queue system.

## Boards

- `task_backlog.json`: The main repository for all planned tasks not yet ready for execution.
- `task_ready_queue.json`: Contains tasks that are validated, have dependencies met, and are ready for an agent to claim and start working on.
- `working_tasks.json`: Tasks currently claimed and being actively executed by an agent.
- `completed_tasks.json`: Tasks that have been successfully finished and reviewed/approved.
- `future_tasks.json`: (Legacy/Deprecated) This board is no longer the primary source for pending tasks. Use `task_backlog.json` and `task_ready_queue.json`.

## Format

All boards use a JSON list (`[]`) containing task objects. The schema for task
objects should be standardized (see Task `refactor-task-list-format-001`), but
generally includes:

```json
{
  "task_id": "UNIQUE_TASK_ID",
  "name": "Short descriptive name",
  "description": "Longer description of the task objective.",
  "status": "PENDING | WORKING | COMPLETED_PENDING_REVIEW | COMPLETED | FAILED | BLOCKED",
  "priority": "HIGH | MEDIUM | LOW",
  "assigned_agent": "AgentID | null | TBD",
  "dependencies": ["TASK_ID_1", "TASK_ID_2"],
  "notes": "Additional context, progress updates, or error details.",
  "created_by": "AgentID | SupervisorID",
  "created_at": "YYYY-MM-DDTHH:MM:SSZ",
  "timestamp_updated": "YYYY-MM-DDTHH:MM:SSZ",
  "timestamp_claimed_utc": "YYYY-MM-DDTHH:MM:SSZ"
}
```

_(Note: Timestamp fields should use ISO 8601 UTC format)_

## Agent Responsibilities

1.  **Task Acquisition:** When ready for work, an agent should:

    - Scan `task_ready_queue.json` for suitable PENDING tasks (considering priority
      and agent capabilities). Dependencies should already be met for tasks in this queue.
    - Use the `ProjectBoardManager` utility to claim the task. This utility handles:
        - Assigning the task to the agent (`assigned_agent` field).
        - Updating the `status` to `WORKING`.
        - Updating `timestamp_updated` and adding `timestamp_claimed_utc`.
        - **Atomically moving the _entire task object_ from `task_ready_queue.json` to
          `working_tasks.json`.**

2.  **Task Completion (Submit for Review):** Upon successful completion **and passing self-validation checks** (see ATAP protocol):

    - Use the `ProjectBoardManager` utility to update the task object's `status` to `COMPLETED_PENDING_REVIEW`.
    - Add relevant completion details, results, or commit hashes to `notes`.
    - Update `timestamp_updated`.
    - **Leave the task object in `working_tasks.json`.**
    - **Notify the Supervisor** (e.g., via mailbox message) that the task is
      ready for review, referencing the `task_id`.

3.  **Task Failure/Blocking:** If a task fails or is blocked:
    - Update the task object's `status` to `FAILED` or `BLOCKED`.
    - Add detailed reasons and error messages to `notes`.
    - Update `timestamp_updated`.
    - Leave the task in `working_tasks.json` for Supervisor review or
      reassignment.
    - Notify the Supervisor via their mailbox.

## Supervisor Responsibilities (Summary - See Onboarding Protocols for Full Details)

- **Review:** Monitor `working_tasks.json` for tasks with status
  `COMPLETED_PENDING_REVIEW`.
- **Validate:** Assess completed work against requirements and standards.
- **Approve:** If approved, update status to `COMPLETED` and **atomically move
  the task object from `working_tasks.json` to `completed_tasks.json`.**
- **Reject:** If rejected, update status (e.g., back to `PENDING`), add feedback
  to `notes`, and notify the relevant agent.

## Implementation Notes

**DEPRECATION WARNING: Direct File Manipulation**

Directly editing the task board JSON files (`task_backlog.json`, `task_ready_queue.json`, `working_tasks.json`, `completed_tasks.json`) using general-purpose file editing tools (like the `edit_file` tool) is **STRONGLY DEPRECATED** and may be disabled in the future. Direct edits bypass essential safeguards like file locking, atomic writes, and schema validation, leading to a high risk of data corruption, race conditions, and system instability.

**Mandatory Tooling:**

All interactions with the project task boards **MUST** be performed using the designated `ProjectBoardManager` utility (accessible via its CLI or Python API). This utility handles concurrency, atomicity, and validation automatically.

For specialized JSON list item manipulation tasks (e.g., modifying a specific field within a task already loaded, *not* for standard board operations), the `safe_edit_json_list.py` script may be used cautiously, but its use for claiming, updating status, or moving tasks between boards is strictly prohibited.

- **Concurrency:** Reading and writing to these JSON files MUST be handled carefully. **(Handled by `ProjectBoardManager`)**
- **Atomicity:** Moving tasks between boards MUST be atomic. **(Handled by `ProjectBoardManager`)**
- **Utilities:** Use the mandated `ProjectBoardManager` utility.
