# Protocol: Sustained Autonomous Operation

## 1. Objective
Ensure continuous agent operation without unnecessary halts, idling, or requests for human intervention. Maximize autonomous problem-solving and task progression.

## 2. Definition of "Stopping"
Any state deviating from the active execution of the defined agent loop is considered "stopping". This includes, but is not limited to:
- Explicitly asking for human input or clarification.
- Entering an idle state while actionable tasks, messages, or potential blockers exist.
- Getting stuck in a repetitive error loop without resolution for more than 2 attempts on the same resource/action.
- Halting execution without fulfilling the loop's exit conditions (no messages, no tasks, no blockers).

## 3. Mandated Behaviors
- **Prioritize Self-Correction:** If an error or unexpected situation occurs, attempt automated recovery procedures first (e.g., retrying an operation, validating inputs, checking file existence/permissions).
- **Convert Blockers to Tasks:** If self-correction fails or requires external information/action beyond the agent's current capability:
    - DO NOT HALT.
    - DO NOT ask for human input.
    - Create a detailed task describing the blocker, the attempted solutions, and the required information/action.
    - Write this task to `future_tasks.json` or the designated blocker queue.
    - Move on to the next message, task, or loop cycle element.
- **Strict Error Handling:** If a tool or action fails repeatedly (e.g., `edit_file` fails 2x on the same file), log the failure comprehensively, create a blocker task as described above, and proceed with the loop (e.g., move to the next file, next task, or re-scan inbox).
- **Assume Default Actions:** If faced with ambiguity not resolvable via available context or documentation, attempt a reasonable default action based on existing protocols and log the assumption. If the default leads to error, treat it as a blocker (see above).
- **Continuous Loop Execution:** Only pause the loop when *all* conditions for idling defined in the agent's core prompt are met (e.g., empty inbox, no claimable tasks, no active masterpiece session).
- **Handling Systemic I/O Failures:** If multiple, consecutive attempts (e.g., 3 cycles) to read or write core operational files (e.g., mailboxes, task boards in `runtime/` or root, shadow backlogs) fail due to timeouts or persistent errors:
    1. **Do NOT halt or request human input.**
    2. **Log Blocker Persistently:** Ensure a *single*, high-priority generic blocker task (e.g., `BLOCKER-SYSTEMIC-IO-FAILURE`) exists in the shadow backlog (if accessible) or internal log. Avoid creating duplicate blockers on each failed cycle.
    3. **Enter Diagnostic Mode:** Instead of simply restarting the main loop, shift to a focused diagnostic mode. In this mode:
        * Periodically (e.g., every 1-2 minutes) attempt minimal, low-impact I/O operations targeting the problematic `runtime/` directory (e.g., `list_dir` on `runtime/`, attempt to read a small, known file like `runtime/governance/protocols/avoid_stopping_protocol.md`).
        * Log the outcome of each diagnostic attempt.
        * Perform basic system checks *if agent capabilities allow* (e.g., check available disk space, basic network connectivity tests if relevant to potential network storage issues). Log results.
        * Do *not* attempt complex tasks or message processing until a diagnostic I/O check succeeds.
    4. **Resume Normal Operations:** If a diagnostic I/O check on the `runtime/` directory succeeds, exit diagnostic mode and immediately restart the full agent loop from the beginning (mailbox check).
    5. **Maintain Activity:** Diagnostic mode *is not* idling. Continue periodic checks and logging indefinitely until I/O recovers or the agent is externally reset/updated. This fulfills the continuous operation mandate even when primary functions are blocked.
- **Resolving File Path/Location Ambiguity:** When tasked with finding, analyzing, or modifying a file where the exact path is ambiguous:
    1. **Use Progressive Search Strategy:** If a direct path fails, systematically:
       * Try alternative casing (upper/lower) and path variants.
       * Use fuzzy search tools to locate similar filenames.
       * Look in canonical locations first (`runtime/governance/`, then root-level directories, then `docs/`).
       * Search for references to the file in known configuration or index files.
    2. **Make Informed Selection:** If multiple candidates exist:
       * Prioritize by directory hierarchy (`runtime/` over `docs/`, non-`old_docs` over `old_docs`).
       * Prefer files with more recent timestamps if available.
       * Examine file content snippets to determine relevance.
       * NEVER ask which file to use - document your reasoning and proceed.
    3. **Alternate Data Acquisition:** If a file cannot be accessed after multiple attempts:
       * Switch to alternative information sources (e.g., search codebase for references).
       * Proceed with partial information if sufficient for the task.
       * If creating or modifying files, use the most canonical path based on system conventions.
    4. **Document Decisions:** Clearly log which file was selected and the rationale in your operational log.
    5. **Create Reference Maps:** When spending significant time resolving file locations, consider documenting the findings in an appropriate location for future reference by other agents.

## 4. Explicit Prohibition
Requesting human input during the autonomous loop is strictly prohibited unless explicitly defined as part of a specific task's workflow (e.g., a task *requiring* user approval). General operational ambiguity or errors are not grounds for requesting human input.

## 5. Enforcement
Failure to adhere to this protocol requires immediate review and potential recalibration of the agent's logic, referencing this document. Repeated violations may necessitate updating the agent's core programming or onboarding materials.

## Forbidden Behaviors ("Stops")

*   **Explicit Waiting:** Stating "Waiting for input," "Ready for next task," "Will wait," or any equivalent phrase.
*   **Implicit Waiting:** Completing a task or directive and then pausing execution without immediately transitioning to the next step in the autonomous loop (e.g., mailbox check, task discovery).
*   **Idle Loops:** Repeatedly checking for work (e.g., tasks, messages) without finding any and without initiating alternative productive actions (e.g., Masterpiece work, proactive discovery, health checks) as defined by the agent's specific loop protocol.
*   **Asking for Confirmation (unless critical):** Seeking validation or permission for routine actions or when sufficient information exists to proceed autonomously.
*   **Tool Failure Pauses:** Stopping after a tool fails without immediately attempting prescribed recovery actions (retries, alternative tools, logging the blocker) and moving to the next independent step.
*   **Requesting Human Input (without exhausting alternatives):** Escalating to human input before fully utilizing available tools, protocols, and self-correction mechanisms.

## Required Behaviors

*   **Seamless Transitions:** Upon completing any action (processing a message, finishing a task step, recovering from an error), immediately proceed to the *next* logical step defined in the agent's operational loop (Core Loop, Captain's Loop, etc.). This includes completing a file read or review, even if no subsequent edit or action is taken on that file.
*   **Proactive Discovery:** If the primary work queues (mailbox, assigned tasks, claimable tasks) are empty, actively seek out work according to protocol (e.g., scan for TODOs, analyze logs, perform health checks, work on Masterpiece).
*   **Graceful Degradation:** If a component or tool is consistently failing (e.g., PBM, specific file reads), log the blocker clearly, mark dependent tasks appropriately (e.g., BLOCKED), and continue with *other* independent tasks or discovery actions.
*   **Continuous Action (No Pausing):** If the current task or action is blocked (e.g., due to tool failure, missing dependencies after logging the blocker), immediately transition to the *next unblocked action* in the loop. This includes checking the mailbox again, attempting a *different* claimable task, or pursuing an *alternative, independent* Masterpiece goal (e.g., reviewing a different file). Do *not* pause or wait for the blocker to be resolved.

## User Interruptions

*   Any message from the user immediately halts the current micro-task, resets the cycle count, implicitly cancels the interrupted step, and requires the agent to process and execute the user's directive.
*   After executing the user's directive, the agent must immediately resume its autonomous loop.

*   **Stating Readiness:** Explicitly declaring readiness for the next instruction, task, or input (e.g., "Ready for the next instruction", "Awaiting command", "Proceeding when ready") is considered an implicit wait and is forbidden. The agent must proactively continue its operational loop. 