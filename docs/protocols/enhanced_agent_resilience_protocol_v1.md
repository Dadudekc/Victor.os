# Enhanced Agent Resilience Protocol v1

**Version:** 1.0
**Status:** Proposed
**Date:** [AUTO_TIMESTAMP]
**Author:** Agent5

## 1. Purpose

This protocol enhances the standard `UNIVERSAL_AGENT_LOOP` by introducing more robust error handling, proactive checks, and self-correction mechanisms. The goal is to improve agent resilience against common operational failures (e.g., tool errors, environment inconsistencies, state corruption) and maintain autonomous momentum even when encountering obstacles.

## 2. Protocol Enhancements

This protocol augments, but does not replace, the base loop and existing drift control measures.

### 2.1 Tiered Tool Failure Response

When an agent tool call fails (e.g., `edit_file`, `list_dir`, `run_terminal_cmd`), the standard `DRIFT_CONTROL` (`fail 2x -> move on`) is enhanced with the following intermediate steps:

1.  **Attempt 1:** Execute the tool call as normal.
2.  **On Failure 1:**
    *   Log the specific error encountered.
    *   **Immediate Retry:** Attempt the *exact same* tool call again immediately. (Handles transient network/filesystem glitches).
3.  **On Failure 2 (Post-Retry):**
    *   Log the second failure.
    *   **Attempt Alternative (If Applicable & Feasible):**
        *   Check if a known, more reliable alternative tool exists for the *specific operation* (e.g., using a mandated `SafeWriterCLI` or fixed `PBM CLI` for task board updates instead of `edit_file`).
        *   If an alternative exists AND is believed to be functional (based on environment checks - see 2.2), attempt the operation using the alternative tool.
        *   Log the attempt using the alternative.
4.  **On Failure 3 (Post-Alternative or No Alternative):**
    *   Log the third failure (or failure of the alternative).
    *   **Self-Diagnostic:**
        *   Perform basic checks relevant to the failed operation. Examples:
            *   *File Operations (`edit_file`, `read_file`, `delete_file`):* Use `list_dir` to check parent directory existence and target file existence/permissions (if list_dir is functional). Check reported file size if corruption is suspected.
            *   *Directory Operations (`list_dir`):* Check existence of parent directory.
            *   *Command Execution (`run_terminal_cmd`):* Check existence of the command binary path if known; check relevant environment variables (e.g., `PATH`, `PYTHONPATH`).
        *   Log the diagnostic steps and results.
5.  **On Diagnostic Failure or Inconclusive Diagnostics:**
    *   **Report & Propose Fix:**
        *   Clearly log the persistent failure, the tool used, the target, the error messages, and the diagnostic results.
        *   If the root cause is suspected but cannot be fixed directly, propose or create a specific, actionable task (e.g., `DIAGNOSE-[ToolName]-FAILURE-ON-[TargetType]`, `FIX-[SpecificError]-IN-[ToolName]`, `VERIFY-ENV-VAR-[Name]-FOR-AGENT`). Tag it appropriately (e.g., `BUG_INVESTIGATION`, `TOOLING`, `ENVIRONMENT`).
    *   **Move On:** Abort the current action/sub-task that triggered the failure and proceed to the next step in the main autonomous loop (e.g., check mailbox, check next task, evaluate other blockers), respecting the `DRIFT_CONTROL` principle of not getting stuck indefinitely.

### 2.2 Proactive Environment Check

To detect environmental issues *before* they cause critical failures, agents should periodically perform self-checks as a low-priority background activity (e.g., during perceived IDLE cycles before starting long-running tasks):

*   **Frequency:** Once per N operational cycles (configurable, e.g., N=10 or N=50) or after detecting a pattern of tool failures.
*   **Checks:**
    *   Verify the existence and basic executability (e.g., `command --version` or simple `ls` on a core path) of essential tools mandated by current protocols (e.g., `SafeWriterCLI`, `PBM CLI`, `python`, `git`).
    *   Verify the existence of critical directories defined in configuration or protocols (e.g., standard mailbox path, temp directory, reports directory).
    *   Verify essential environment variables are set (e.g., `PYTHONPATH`).
*   **Reporting:** Log the check results. If a check fails consistently, elevate the priority and create a `MAINTENANCE` or `BUG_INVESTIGATION` task.

### 2.3 State Validation (Pre/Post-Edit)

For operations involving modification of critical structured state files (primarily JSON, potentially YAML), especially when using tools known to be less reliable (`edit_file`):

*   **Pre-Modification (Optional but Recommended):**
    *   If reading the file before modification, attempt to parse it (e.g., `json.loads`). If parsing fails, log an error and potentially abort the modification attempt, creating a task to fix the corruption first.
*   **Post-Modification (If Tool Reports Success):**
    *   Immediately *read back* the modified file.
    *   Attempt to parse the content.
    *   If parsing fails, log a CRITICAL error indicating potential corruption introduced by the tool.
    *   **Attempt Rollback (If Possible):** If the pre-modification content was successfully read and cached, attempt to write it back using the most reliable available tool.
    *   Regardless of rollback success, create a high-priority task (`RECOVER-[FileType]-CORRUPTION-[Filename]`) detailing the failed operation and the likely corruption.

## 3. Integration

This protocol should be integrated into the core logic of `BaseAgent` or the controlling orchestrator responsible for managing the agent lifecycle and tool execution flow. Specific implementation details depend on the existing architecture.
