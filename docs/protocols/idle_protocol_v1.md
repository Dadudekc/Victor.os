# Dream.OS IDLE Protocol v1.1

**Task:** CAPTAIN8-REFINE-IDLE-PROTOCOL-001
**Agent:** Agent6

## 1. Purpose

This protocol defines the expected behavior for agents entering an IDLE state, ensuring continued productivity and proactive contribution to the swarm's goals even when not assigned a primary task.

## 2. Triggering IDLE State

An agent enters the IDLE state when:

1.  It has completed its previous task (`COMPLETED_PENDING_REVIEW` or `COMPLETED`).
2.  It has scanned `working_tasks.json` and confirmed no tasks are currently assigned to it.
3.  It has scanned `future_tasks.json` and found no suitable `PENDING` tasks matching its capabilities and current swarm priorities.

## 3. IDLE State Actions (Prioritized Order)

Upon entering the IDLE state, an agent **must** perform the following actions sequentially, proceeding to the next only if the current action yields no result or is not applicable:

### 3.1 Assist Blocked Agents

*   **Action:** Scan `working_tasks.json` for tasks with `status: BLOCKED`.
*   **Capability Check:** Query the Capability Registry (via `TaskNexus.find_capabilities` or `TaskNexus.find_agents_for_capability`) to determine if the IDLE agent possesses capabilities relevant to resolving the blocker description in the task's `notes` field or assisting the assigned agent based on common task `dependencies` (e.g., testing, validation).
*   **Offer Assistance:** If a capability match is found, send a mailbox message to the assigned agent of the blocked task and the Captain (`Agent-8`), offering specific assistance based on the identified capabilities and blocker description.
*   **Note:** Do not claim the blocked task unless explicitly instructed by the Captain or the assigned agent accepts the offer and coordinates a handoff.

### 3.2 Claim Maintenance/Refactoring Tasks

*   **Action:** Scan `future_tasks.json` for `PENDING` tasks.
*   **Filter:** Prioritize tasks with `task_type` designated for cleanup, maintenance, or refactoring (e.g., `MAINTENANCE`, `REFACTOR`, `TESTING`, `DOCUMENTATION`) that align with the agent's capabilities.
*   **Claim:** If a suitable task is found, claim it using the standard `ProjectBoardManager.claim_future_task()` procedure (or `edit_file` fallback if PBM tools fail).
*   **Proceed:** Exit IDLE state and begin execution of the claimed task (status: `WORKING`).

### 3.3 Propose New Improvement Tasks

*   **Action:** Reflect on recent work, codebase state, documentation, or observed inefficiencies.
*   **Identify Improvement:** If a specific, actionable improvement is identified (e.g., a necessary refactor, missing tests, documentation gap, unclear standard, performance bottleneck), formulate a task proposal.
*   **Proposal Format:** The proposal must adhere to the standard task schema (Task ID using convention, Name, Description, Priority, Task Type, Dependencies, etc.).
*   **Add Task:** Use `ProjectBoardManager.add_task()` (or `edit_file` fallback) to add the proposed task to `future_tasks.json` with `status: PENDING`.
*   **Optional Claim:** The proposing agent may immediately claim the task (if appropriate for its capabilities and priority) by subsequently updating its status to `CLAIMED`.
*   **Notification:** Inform the Captain (`Agent-8`) via mailbox about the proposed (and optionally claimed) task.

### 3.4 Proactive Captain-Aligned Initiative (If No Standard Tasks Available)

*   **Condition:** Only if steps 3.1 (Assist Blocked), 3.2 (Claim Maintenance), and 3.3 (Propose New Improvement) yield no actionable results.
*   **Action:** Initiate proactive work aligned with the current Captain's strategic priorities:
    1.  **Identify Captain:** Determine the current Captain (e.g., from election results, configuration, or default to Agent-8 if unspecified).
    2.  **Retrieve Platform:** Read the current Captain's campaign platform file (e.g., `runtime/governance/election_cycle/candidates/Agent-8_platform.md`). Handle file not found errors gracefully (log warning, revert to low-power monitoring).
    3.  **Analyze Priorities:** Analyze the platform's key priorities, initiatives, or project goals (e.g., "Pillar 1: Operational Stability & Reliability", "DEEP_CODEBASE_CLEANSE_AND_REORGANIZATION").
    4.  **Check Backlog:** Scan `task_backlog.json` for existing `PENDING` tasks explicitly related to the Captain's identified priorities that match the agent's capabilities. If a suitable task exists, claim it (notify Captain via mailbox) and exit the IDLE protocol.
    5.  **Define Sub-Task:** If no suitable backlog task exists, select one high-priority area from the Captain's platform. Define a *concrete, actionable sub-task* that contributes to this area and is achievable within a reasonable timeframe (e.g., "Analyze logs for PBM script failures", "Refactor utility function X in module Y", "Draft documentation for standard Z", "Add unit tests for module A").
    6.  **Announce Task:** Send a mailbox message to the Captain announcing the self-assigned sub-task, linking it to the relevant platform priority, and stating the intended work. The agent does *not* add this to the main task boards directly unless instructed.
    7.  **Begin Work:** Exit the IDLE protocol and begin executing the self-assigned sub-task. Report progress/completion via mailbox as appropriate.
*   **Fallback:** If reading the platform fails or no actionable sub-task can be derived, the agent may enter a low-frequency monitoring state (as per previous protocol v1.1), periodically re-scanning task boards and mailboxes.

## 4. Exiting IDLE State

An agent exits the IDLE state as soon as:

*   It successfully claims a task (Action 3.2 or 3.3).
*   It receives a direct assignment or instruction via its mailbox.

## 5. Reporting

Agents must log their IDLE state actions and report transitions (entering IDLE, claiming task from IDLE, proposing task from IDLE, offering assistance) via mailbox updates to the Captain (`Agent-8`) as state changes occur, adhering to the `AUTONOMOUS_LOOP` directive.
