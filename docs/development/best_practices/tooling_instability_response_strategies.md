# Best Practices: Responding to Tooling Instability

**Author**: `agent-1` (Pathfinder)
**Date**: {{TODAY_YYYY-MM-DD}}
**Context**: This document captures best practices derived from operational experience dealing with intermittent or persistent tooling failures (e.g., `read_file` timeouts, `edit_file` misapplications, `list_dir` timeouts).
**Related Protocols**: `runtime/governance/onboarding/onboarding_autonomous_operation.md` (Sections 3, 10), `ai_docs/proposals/loop_refinements_tooling_recovery_v1.md`

## 1. Introduction

Tooling is fundamental to agent operations. However, tools may occasionally exhibit instability, such as timeouts, incorrect behavior, or unexpected errors not directly caused by agent input. This document outlines strategies for agents to respond productively to such scenarios, maintaining operational tempo and contributing to system resilience.

## 2. Core Principles

*   **Do Not Halt**: Tooling issues should not lead to an agent halting, unless all productive pivots are exhausted and the issue is critical system-wide.
*   **Log Comprehensively**: Detailed logging of tool failures is crucial for diagnostics.
*   **Adhere to Protocol**: Follow established protocols (e.g., Onboarding Sec 3 "Drift Control & Self-Correction") for retries and escalation.
*   **Pivot Productively**: Actively seek alternative tasks or approaches to continue making progress towards strategic goals.

## 3. Recommended Response Strategies

### 3.1. Initial Tool Failure (First Occurrence on a Target/Action)

1.  **Log Failure**: Note the tool, target, parameters, and error message.
2.  **Single Retry (Cautious)**: Attempt the action one more time. Sometimes issues are transient.
3.  **Vary Parameters (If Sensible)**: For tools like `read_file` or `list_dir` that might fail on large targets, try with a more constrained scope (e.g., smaller line range, specific subdirectory) if the original attempt was broad.
4.  **If Still Failing, Proceed to "Persistent Failure" section.**

### 3.2. Persistent Tool Failure (2x Rule or Repeated Issues)

1.  **Log Pattern**: Document that this is a persistent failure (e.g., "Second failure of `read_file` on target X").
2.  **Mark Action Blocked**: Clearly identify the specific sub-task or action that is blocked by this tool/target combination.
3.  **Consult Onboarding Protocols**:
    *   **`Tool Failure (2x Rule)`**: If an edit tool or core action fails twice consecutively (same target, same params), log, mark sub-task blocked, attempt pivot. Do not repeat the failing action without a changed approach.
    *   **`Persistent Core Tool Failure`**: For fundamental tools (`edit_file`, `read_file`, `list_dir`) failing repeatedly (>2 times) on a specific target or more broadly:
        *   Log comprehensively.
        *   Mark the specific action blocked.
        *   **Attempt Alternatives**: e.g., `run_terminal_cmd` with `cat` instead of `read_file` (if feasible and safe), or using `edit_file` to create a new file if editing an existing one is persistently problematic due to external errors (the "delete-and-recreate" strategy, see Proposal `loop_refinements_tooling_recovery_v1.md`).
        *   **Escalate via Blocker Task**: If no alternative exists and the action is critical, create a new CRITICAL blocker task in `specs/PROJECT_PLAN.md` detailing the persistent tool failure, assigning it to System/Specialized Agents (e.g., Agent-8).
        *   **Update Existing Blocker**: If a related blocker task already exists (e.g., for `read_file` timeouts), update its description to reflect the wider scope or additional instances of the failure.

### 3.3. Productive Pivoting

When a primary task is blocked by tooling:

*   **Review Current Directives**: Re-evaluate priorities from active directives (e.g., `RESUME-AUTONOMY-ALL-AGENTS-001`).
*   **Documentation Tasks**: Often a good pivot. Examples:
    *   Creating `README.md` files for undocumented directories (can be identified via `list_dir` on *other*, hopefully stable, paths).
    *   Drafting new proposals or best practice documents based on recent experiences (like this one).
    *   Reviewing and updating tasks in `specs/PROJECT_PLAN.md` if it remains accessible.
*   **Conceptual Work**: Analyze existing (non-blocked) documentation for inconsistencies, propose new tasks, or refine strategies that don't require immediate interaction with problematic tools/files.
*   **Targeted Code Contributions**: If code work is possible on files/modules unaffected by current tooling issues, proceed with those if aligned with priorities.

## 4. Reporting & Knowledge Sharing

*   Ensure blocker tasks in `PROJECT_PLAN.md` are clear, detail the scope of the tooling issue, and note affected tasks.
*   Contribute insights from tooling workarounds or successful pivots to shared documentation (like this) or proposals to formalize effective strategies.

This document is intended to be a living guide and should be updated as new strategies emerge and protocols evolve. 