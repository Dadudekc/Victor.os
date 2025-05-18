# Dream.OS Agent Work Suspension and Resumption Protocol

**Version:** 1.0
**Date:** {{YYYY-MM-DD}} <!-- To be filled with current date -->
**Status:** DRAFT

## 1. Introduction & Purpose

This protocol defines the standardized procedure for all Dream.OS agents to temporarily suspend their current work activities in a controlled manner, ensuring that all progress and context are preserved for seamless resumption at a later time. 

The primary goals are:
*   To prevent loss of work or context during planned interruptions (e.g., system maintenance, developer absence, urgent high-priority overrides).
*   To enable agents to gracefully pause their operational loop upon directive.
*   To provide a clear method for agents to restore their working state and continue tasks efficiently.

This protocol is applicable to all Dream.OS swarm members.

## 2. Trigger Conditions for Work Suspension

Work suspension shall be initiated under the following conditions:

*   **Explicit Directive:** Receipt of a formal "SUSPEND_WORK" directive from THEA, a designated Supervisor agent, or via a high-priority system broadcast.
*   **Scheduled Maintenance Window:** Pre-communicated system maintenance periods where continued operation might be unstable or lead to data loss.
*   **(Future Consideration) Agent-Detected Critical Local Failure:** In future iterations, an agent might autonomously trigger suspension if it detects critical, unrecoverable failures in its local execution environment, provided it can do so safely without compromising system stability. This is currently not standard procedure and requires explicit approval if attempted.

## 3. Suspension Procedure (Agent Actions)

Upon receiving a valid trigger to suspend work, agents must perform the following steps sequentially:

1.  **3.1. Acknowledge Directive:** Log the receipt of the suspension directive in the agent's `devlog.md`, including timestamp and source of the directive.

2.  **3.2. Complete Immediate Micro-Task (If Safe):** If the agent is in the middle of a very short, atomic operation (e.g., writing a small file, a single API call) that is safer to complete than to interrupt, it should complete this micro-task. This should not involve starting new complex operations. Maximum time for this step: < 30 seconds.

3.  **3.3. Save Current Work State:**
    *   **Version Control:** Commit any validated, error-free code changes or document modifications to the relevant Git repository. The commit message **must** be prefixed with `chore(SUSPEND WORK): ` followed by a concise description of the work being saved (e.g., `chore(SUSPEND WORK): saving progress on checklist parser refinement`).
    *   **File System:** Ensure all open files, buffers, and temporary notes related to the current task are saved to disk.
    *   **Context Serialization:** Create or update a dedicated context file: `runtime/agent_comms/agent_mailboxes/agent-<AgentID>/state/current_task_context.json`. This JSON file must store:
        *   `task_id`: The ID of the currently active task.
        *   `task_title`: Title of the current task.
        *   `objectives_summary`: Brief summary of the task's main goals.
        *   `last_completed_step`: A clear description of the last significant step or action completed.
        *   `next_planned_step`: The immediate next step the agent intended to take.
        *   `key_variables_or_data`: A dictionary of any critical in-memory variables, data snippets, or partial results necessary for resumption. Keep this concise.
        *   `relevant_file_paths`: A list of absolute or repository-relative paths to files actively being worked on or essential for the task's continuation.
        *   `suspend_timestamp_utc`: `{{YYYY-MM-DDTHH:MM:SSZ}}`

4.  **3.4. Update Devlog:** Create a final entry in `devlog.md` before full suspension:
    *   Timestamp (UTC).
    *   Reason for suspension (e.g., "Received SUSPEND_WORK directive from THEA").
    *   Summary of work state saved (e.g., "Committed changes with ID `[commit_hash]`. Saved task context for `[task_id]` to `state/current_task_context.json`.").
    *   Confirmation message: `WORK SUSPENDED. Awaiting resumption signal.`

5.  **3.5. Update Agent Operational Status:**
    *   The agent should signal its suspended state. (Current mechanism: This protocol anticipates a new `AgentState.SUSPENDED` or a dedicated field in `runtime/agent_comms/agent_mailboxes/agent-<AgentID>/status.json`. Pending implementation in `AutonomyEngine`, agents should log this intent clearly.)

6.  **3.6. Halt Active Processes:** Terminate any self-initiated loops, non-essential background monitoring (if agent-managed), or other active processes related to its tasks. The primary agent operational loop is now considered paused.

## 4. Resumption Procedure (Agent Actions)

Upon receiving a valid "RESUME_WORK" directive:

1.  **4.1. Acknowledge Directive:** Log the receipt of the resumption directive in `devlog.md` with a timestamp.

2.  **4.2. Load Saved Work State:**
    *   **Version Control:** Perform a `git pull` on relevant repositories to ensure local work is synchronized with any changes that may have occurred during suspension.
    *   **Context Deserialization:** Read and parse the `runtime/agent_comms/agent_mailboxes/agent-<AgentID>/state/current_task_context.json` file.
    *   Load key variables and data back into the agent's working memory.
    *   Re-open files listed in `relevant_file_paths`.

3.  **4.3. Verify Environmental Readiness (Optional):** Perform basic checks to ensure the environment is conducive to resuming work (e.g., network connectivity, access to key services if applicable).

4.  **4.4. Update Devlog:** Create an entry in `devlog.md`:
    *   Timestamp (UTC).
    *   Confirmation message: `WORK RESUMED. Loaded previous context for task_id: [task_id] - [task_title]. Next step: [next_planned_step from context file].`

5.  **4.5. Update Agent Operational Status:**
    *   Set operational status back to `READY`, `RUNNING`, or as appropriate based on the resumed task and system state. (Mechanism pending `AutonomyEngine` update as noted in 3.5).

6.  **4.6. Continue Task:** Resume the assigned task from the `next_planned_step` identified in the loaded context.

## 5. THEA/Supervisor Responsibilities

*   Issue clear, unambiguous `SUSPEND_WORK` and `RESUME_WORK` directives, specifying target agents or all-swarm.
*   If suspension is for system-wide reasons, ensure all targeted agents have acknowledged suspension (via devlog or status update) before proceeding with system actions.
*   Monitor agents for successful resumption of work and address any anomalies.
*   Maintain a log of suspension/resumption events at the swarm coordination level.

## 6. Related Protocols

This protocol should be understood in conjunction with:

*   `docs/agents/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
*   `docs/agents/CORE_AGENT_IDENTITY_PROTOCOL.md`
*   `docs/agents/CONTINUOUS_OPERATION_AND_RESILIENCE_PROTOCOL.md`
*   `docs/agents/AGENT_ONBOARDING_CHECKLIST.md` (for understanding agent file structures)

## 7. Document Version History

*   **v1.0 ({{YYYY-MM-DD}}):** Initial draft. 