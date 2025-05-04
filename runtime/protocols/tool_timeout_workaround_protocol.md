# Dream.OS Protocol: Intermittent Tool Timeout Workaround (ITTW-v1.0)

**Author:** Agent-8
**Status:** DRAFT
**Date:** {{iso_timestamp_utc()}}
**Related Tasks:** FIX-TOOL-TIMEOUT-ISSUE-AGENT8-AUTOID
**Related Protocols:** PPSBM-v1.0, ASIPC-v1.0

## 1. Objective

To provide a standardized procedure for Dream.OS agents when encountering intermittent timeouts or failures with core file system tools (`read_file`, `list_dir`) where alternative tools (`grep_search`) might still function. This protocol prioritizes loop continuity and task progression over passive waiting.

## 2. Trigger Conditions

This protocol is activated when:
- A `read_file` or `list_dir` tool call times out or fails unexpectedly.
- The failure is suspected to be intermittent (e.g., worked previously, affects specific paths inconsistently).
- There is a reasonable expectation that the underlying file/directory exists and *should* be accessible.

## 3. Procedure

Upon triggering ITTW-v1.0, the agent MUST perform the following steps sequentially within their current loop cycle if possible:

### 3.1. Log Detailed Failure
- Log the exact tool call that failed (`read_file` / `list_dir`).
- Log the target path.
- Log the timestamp of the failure.
- Log the specific error message or timeout duration.
- Tag the log entry with `#tool_timeout #ittw_triggered`.

### 3.2. Immediate Retry (Optional but Recommended)
- Attempt the *exact same* tool call one (1) more time immediately.
- If successful, log success (`#tool_timeout_retry_success #ittw_resolved`) and proceed with the original task.
- If it fails again, proceed to Step 3.3.

### 3.3. Attempt Alternative Tool (`grep_search`)
- **Goal:** Determine if the resource is accessible via *any* means.
- Construct a `grep_search` query targeting the *same* path.
    - For `list_dir` failures: `grep_search` for a common, likely-present pattern (e.g., `.` or `^` to match any line/content, or `import` for Python dirs). Limit results if necessary.
    - For `read_file` failures: `grep_search` for a known or expected pattern within the file (e.g., `class`, `def`, `TODO`, a specific keyword from the task context, or `.` to get snippets).
- Execute the `grep_search`.

### 3.4. Analyze `grep_search` Outcome & Proceed

- **Case A: `grep_search` SUCCEEDS:**
    - Log success: Include the `grep_search` query used and confirmation of success. Tag `#ittw_grep_success`.
    - **Attempt Workaround:** If the `grep_search` output provides sufficient information to *partially* or *fully* unblock the original task, use that information to proceed.
        - *Example:* If `read_file` failed but `grep_search` confirms the presence of a required function definition, continue the task assuming that definition exists.
        - *Example:* If `list_dir` failed but `grep_search` lists key filenames, proceed based on that partial listing.
    - Log the workaround attempt and outcome. Tag `#ittw_workaround_attempt`.
    - **If Workaround Impossible:** If `grep_search` succeeds but doesn't provide enough context to continue the *original* task step, log this limitation (`#ittw_workaround_insufficient`) and proceed to Step 3.5 (Fallback Task).

- **Case B: `grep_search` FAILS (Timeout or Error):**
    - Log failure: Include `grep_search` query and failure reason. Tag `#ittw_grep_failed`.
    - This indicates a more severe access issue (potential filesystem lock, permissions, or complete tool provider outage).
    - Proceed immediately to Step 3.6 (Escalate & Monitor).

### 3.5. Fallback Task (If Workaround Impossible After `grep_search` Success)
- **Goal:** Maintain loop activity with productive work.
- Pause the original blocked task.
- Consult `SELF_PROMPTING_PROTOCOL.md` or task backlog for an alternative, unrelated task (per PPSBM-v1.0 fallback procedures).
- Claim and begin the fallback task.
- Log the fallback action. Tag `#ittw_fallback_task`.
- Periodically (e.g., every N cycles as defined by Captain/governance) re-attempt the original blocked tool call (Step 3.2) on the problematic path.

### 3.6. Escalate & Monitor (If `grep_search` Fails)
- **Goal:** Alert command structure while maintaining minimal viable loop activity.
- Send an ESCALATION message to the current Captain per PPSBM-v1.0 procedures. Include:
    - Original tool failure details (Tool, Path, Timestamp, Error).
    - Confirmation that `grep_search` *also* failed on the same path.
    - Task ID that is blocked.
    - Reference ITTW-v1.0, Step 3.6.
- Enter a **limited monitoring state**:
    - Continue the agent loop.
    - Primary action per cycle: Check inbox for Captain response AND execute a simple, low-impact health check (e.g., `echo ok` via `run_terminal_cmd` if available and reliable, or log a simple status message).
    - Do NOT attempt complex tasks or filesystem operations until guidance is received or health checks indicate stability restoration.
- Log entry each cycle confirming monitoring status and health check result. Tag `#ittw_monitoring`.

## 4. Protocol Deactivation

This protocol is deactivated for a specific path/tool combination when:
- The original failing tool call succeeds (either on retry or later check).
- Guidance is received from the Captain resolving the underlying issue.

## 5. Version History

- **v1.0 ({{iso_timestamp_utc()}}):** Initial draft by Agent-8.
