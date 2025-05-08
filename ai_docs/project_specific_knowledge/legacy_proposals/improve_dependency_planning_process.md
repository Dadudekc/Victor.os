# Proposal: Improve Task Dependency Planning Process

**Version:** 1.0 **Status:** Proposed **Date:** 2025-04-29T20:36:20Z **Author:**
AgentGemini **Related Task:** PROCESS-IMPROVE-DEP-PLANNING-001

## Problem Statement

Multiple agents, including AgentGemini, have encountered situations where tasks
are claimed or assigned but cannot be executed due to missing, inaccessible, or
non-functional dependencies _other than prerequisite tasks_. Examples include
missing GUI image assets (`BSA-IMPL-BRIDGE-004`), non-functional or inaccessible
tools (`REFACTOR-BUS-IMPORTS-001` blocked by edit tool issues, AgentGemini
blocked by `ProjectBoardManager` issues), or potentially missing configuration
values.

The current task structure only allows specifying prerequisite _task IDs_ in the
`dependencies` field. This fails to capture critical non-task dependencies,
leading to:

- Agents claiming tasks they cannot start or complete.
- Increased frequency of tasks entering `BLOCKED` status.
- Wasted agent cycles attempting to execute unfulfillable tasks.
- Reactive problem-solving after a task is already claimed.

## Proposed Solution

To address this, we propose enhancements to both the task structure and
operational protocols:

**1. Enhanced Task Dependency Structure:**

Modify the task JSON schema to support a more detailed `dependencies` list. Each
item in the list should be an object specifying the dependency type and
identifier:

```json
"dependencies": [
  {
    "type": "TASK",
    "id": "TASK_ID_1",
    "notes": "(Optional) Specific requirement from this task"
  },
  {
    "type": "FILE",
    "path": "src/path/to/required/file.py",
    "check": "exists | executable | readable" // Optional check type
  },
  {
    "type": "ASSET",
    "path": "assets/gui_images/required_button_v1.png"
  },
  {
    "type": "TOOL",
    "name": "ProjectBoardManager.update_task_status", // Or script path
    "check": "available | functional" // Optional check type
  },
  {
    "type": "CONFIG",
    "key": "external_services.api_key", // Key path in AppConfig
    "check": "exists | non_empty" // Optional check type
  }
]
```

- **type:** TASK, FILE, ASSET, TOOL, CONFIG
- **id/path/name/key:** Specific identifier for the dependency.
- **check (Optional):** Basic verification expected (existence, readability,
  functionality - specifics TBD).
- **notes (Optional):** Clarification on the dependency.

**2. Mandatory Dependency Pre-Check Protocol:**

Update task management protocols (potentially in a new
`docs/process/task_management.md` or an update to
`project_board_interaction.md`) to include:

- **Requirement:** Before a task creator lists a task as `PENDING`, or before an
  agent claims a `PENDING` task, they **MUST** perform a reasonable verification
  that _all_ listed dependencies (both TASK and non-TASK) are met and accessible
  in the current environment.
- **Verification:** This might involve simple checks (file existence, tool
  availability via search/help command) or relying on cached system state
  information if available.
- **On Failure:** If _any_ dependency check fails:
  - The task **MUST NOT** be claimed or moved to `WORKING`.
  - If the missing dependency can be resolved by another task, a _new
    prerequisite task_ **MUST** be created and linked (either in the
    `dependencies` list of the original task or via notes).
  - The original task should remain `PENDING` or be explicitly marked `BLOCKED`
    with a note referencing the missing dependency and any prerequisite task
    created.

**3. Task Template Update:**

Any standard task creation templates should be updated to include the new
detailed `dependencies` structure as an example.

**4. Supervisor Review Update:**

Supervisor review protocols for new task proposals or `COMPLETED_PENDING_REVIEW`
tasks should include verifying that dependencies were adequately identified and
ideally pre-checked.

## Benefits

- **Reduced Blockers:** Fewer tasks will enter `BLOCKED` state due to missing
  prerequisites discovered mid-execution.
- **Improved Planning:** Encourages more thorough planning and identification of
  requirements upfront.
- **Increased Efficiency:** Agents spend less time attempting tasks they cannot
  complete.
- **Clearer Task Definitions:** Explicit dependencies improve understanding of
  task requirements.

## Next Steps

1.  Review and refine this proposal (Agent 8 / Supervisor).
2.  Update the canonical task JSON schema documentation.
3.  Create or update the relevant protocol document(s).
4.  Update any existing task templates.
5.  Communicate the new protocol to all agents.
