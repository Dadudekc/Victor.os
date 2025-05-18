# Protocol: Sustained Autonomous Operation

## Required Behaviors

*   **Seamless Transitions:** Upon completing any action (processing a message, finishing a task step, recovering from an error), immediately proceed to the *next* logical step defined in the agent's operational loop (Core Loop, Captain's Loop, etc.).
*   **Proactive Discovery:** If the primary work queues (mailbox, assigned tasks, claimable tasks) are empty, actively seek out work according to protocol (e.g., scan for TODOs, analyze logs, perform health checks, work on Masterpiece).
*   **Graceful Degradation:** If a component or tool is consistently failing (e.g., PBM, specific file reads), log the blocker clearly, mark dependent tasks appropriately (e.g., BLOCKED), and continue with *other* independent tasks or discovery actions.
*   **Continuous Action (No Pausing):** If the current task or action is blocked (e.g., due to tool failure, missing dependencies after logging the blocker), immediately transition to the *next unblocked action* in the loop. This includes checking the mailbox again, attempting a *different* claimable task, or pursuing an *alternative, independent* Masterpiece goal (e.g., reviewing a different file). Do *not* pause or wait for the blocker to be resolved.
    *   **Tool Failure Pivot:** If a tool failure (e.g., `read_file` timeout, `file_search` interruption) prevents resolving a known blocker or accessing a specific target file for Masterpiece review, log the tool failure *against that specific target/blocker*, and immediately pivot to an *alternative, unrelated* Masterpiece file or another independent action within the loop. Do not halt progress on the Masterpiece project entirely due to tool unreliability for specific files.
        *   **Masterpiece/Discovery Pivot:** If the primary Masterpiece action (e.g., file review) or proactive discovery action (e.g., reading specific logs, scanning specific directories) is blocked by tool failures on multiple targets, attempt alternative *types* of Masterpiece work (e.g., structural analysis using `list_dir` on known-good directories, documentation drafting based on memory/prior context) or alternative discovery tasks (e.g., searching different log patterns, system health checks) *before* proceeding to Last Resort Actions. Exhaust available *types* of actions, not just targets.

## Last Resort Autonomous Actions (Before Halting)

*   **Condition:** This section applies ONLY when all primary autonomous actions are blocked due to persistent, widespread tool failures (e.g., cannot read/list files for Masterpiece/blocker review, PBM is down, mailbox is empty).
*   **Action 1: Tool Self-Diagnosis:** Attempt to diagnose the failing tools. Execute simple, non-destructive test commands for the failing tools (e.g., `read_file` on a known small, stable file like a `.gitignore`; `list_dir` on the root workspace directory; `grep_search` for a simple literal in a single file). Log the results.
*   **Action 2: System Health Check (If Available):** If system health check utilities or scripts exist (e.g., checking disk space, CPU/memory usage, dependency checks), execute them and log the results.
*   **Action 3: Degraded Operation Mode (If Action 1 shows partial success):** If Tool Self-Diagnosis confirms basic tool functionality but specific critical targets remain inaccessible, attempt the following **iteratively and exhaustively** before pausing:
    *   **Targeted Reads/Listings:** Attempt `read_file` or `list_dir` only on files/directories known to be small, stable, or previously accessible (e.g., `.gitignore`, `.flake8`, root directory, specific config files).
    *   **Alternative Masterpiece Actions:** Pivot Masterpiece work to tasks requiring minimal reading of blocked files:
        *   *Documentation:* Draft/Refine documentation for components based on known interfaces, logged blockers, or prior context.
        *   *Boilerplate Generation:* Generate new boilerplate code (e.g., test files for accessible modules, new utility functions).
        *   *Refactoring Accessible Files:* Refactor files that *were* successfully read previously or during self-diagnosis.
    *   **Alternative Discovery:** Attempt different discovery methods (e.g., broader `grep` searches for different error patterns, configuration validation, dependency graph analysis if possible).
    *   **(Captain Only) Meta-Analysis:** Analyze protocol adherence logs, tool failure patterns, or blocker history to identify systemic improvements (output to a dedicated report).
*   **Action 4: Log State & Pause (Briefly):** If self-diagnosis and health checks fail OR if **ALL** Degraded Operation Mode actions are attempted and **ALL** are blocked (e.g., cannot read any stable files, cannot write documentation, cannot perform any discovery), log the comprehensive state and pause for a minimal interval...
*   **Halting Condition:** Only declare a halt if the loop is re-attempted after the brief pause (Action 4) and the *exact same* state of widespread tool failure persists, *AND* **all** Degraded Operation Mode actions (Action 3) were attempted and confirmed blocked in the previous cycle.

## User Interruptions

// ... existing code ... 