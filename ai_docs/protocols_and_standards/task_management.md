# Task Management Standards

**Version:** 1.1
**Status:** ACTIVE
**Date:** [NOW_UTC_ISO]
**Related Tasks:** PROCESS-IMPROVE-DEP-PLANNING-001, FINALIZE-TASK-MGMT-STANDARD-001

## Overview

This document outlines the standard practices for creating, defining, and managing
tasks within the Dream.OS project to ensure clarity, traceability, and
efficient execution.

## Core Principle: Explicit Dependency Planning

To prevent blocked work and improve swarm velocity, thorough dependency planning
**before** task implementation begins is mandatory.

## Task Definition Requirements

**Note on Proposed Fields:** The additional dependency fields (`code_dependencies`, `asset_dependencies`, `config_dependencies`) proposed in the draft version are NOT being formally adopted at this time. While detailed dependency tracking is valuable, the overhead of maintaining these structured fields across all tasks is deemed too high currently. Use the `notes` field for critical non-task dependencies and focus on accurately populating the mandatory `dependencies` list.

When creating or defining a task (e.g., in `future_tasks.json` or via Supervisor
direction), the following dependency fields **MUST** be considered and populated accurately:

1.  **`dependencies` (List[str]):**
    - Lists the `task_id`s of other Dream.OS tasks that **MUST** be completed
      before this task can start.
    - This field is enforced by the `ProjectBoardManager.claim_future_task` mechanism.
    - Example: `"dependencies": ["IMPL-CORE-API-001", "TEST-CORE-API-001"]`

## Dependency Resolution Process

- **Identification:** During task planning or creation, the responsible agent or
  Supervisor **MUST** explicitly identify all dependencies across the categories
  above.
- **Prerequisite Tasks:** If a required dependency (e.g., a missing utility function,
  an uncaptured GUI image asset, another blocking task) does not exist or is
  not complete, a prerequisite task **MUST** be created and added to the primary
  task's `dependencies` list.
- **Verification:** Before claiming a task, agents should review all listed
  dependencies (including non-task dependencies noted in fields or `notes`)
  to assess readiness.

## Task Template (Current)

```json
{
  "task_id": "[UNIQUE_ID]",
  "name": "[Concise Task Name]",
  "description": "[Clear description of the objective and expected outcome]",
  "priority": "[CRITICAL | HIGH | MEDIUM | LOW]",
  "status": "PENDING", // Initial status (See Lifecycle below)
  "assigned_agent": null,
  "task_type": "[FEATURE | BUG | REFACTOR | CHORE | TESTING | DOCS | ANALYSIS | PROCESS | ONBOARDING | ...]", // Use appropriate type
  "dependencies": [], // List of prerequisite Task IDs
  "notes": "[Any additional context, justification, potential issues, or critical non-task dependencies]",
  "created_by": "[AgentID or Supervisor]",
  "created_at": "[AUTO_TIMESTAMP]"
  // Timestamps for claimed, started, updated, completed added dynamically by PBM/Agent
}
```

## Enforcement

- Supervisor reviews of new task definitions should check for completeness of
  dependency fields.
- Agents encountering blockers due to unlisted dependencies should update the
  task definition accordingly and report the issue.

## Task Lifecycle and Statuses

Tasks progress through a defined lifecycle, reflected by their `status` field.

- **`PENDING`**: The initial state of a task waiting to be claimed.
- **`CLAIMED`**: An agent has indicated intent to work on the task, but work has not necessarily begun.
- **`WORKING` / `EXECUTING` / `RUNNING`**: The agent is actively performing the task. (Note: Usage should be standardized, prefer `WORKING`).
- **`BLOCKED`**: The task cannot proceed due to an unmet dependency (listed in `dependencies`) or an external factor noted in `notes`. The blocking task/reason should be identified.
- **`COMPLETED_PENDING_REVIEW`**: The agent has finished the work and believes the task objectives are met. Awaiting validation or peer review.
- **`COMPLETED`**: The task has been successfully completed and validated/reviewed.
- **`FAILED`**: The task could not be completed successfully after attempts. Requires analysis, potential re-scoping, or abandonment.
- **`REOPENED`**: A previously completed task needs further work (e.g., due to review feedback, regression).

Agents MUST update the task status accurately via the ProjectBoardManager (or designated mechanism) as they progress through the lifecycle.

## Related Documents

- Asset management guidelines: `docs/guides/asset_management.md` (Placeholder - requires creation)
