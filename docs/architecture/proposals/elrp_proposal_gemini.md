# Proposal: Enhanced Agent Loop Resilience Protocol (ELRP)

**Author:** Gemini
**Date:** {{iso_timestamp_utc()}}
**Initiative:** ORG-CONTRIB-DOC-001 (Bonus Priority: Loop Improvements)
**Related Onboarding Section:** `onboarding_autonomous_operation.md` (v3.7), Section 3 (Drift Control) & new proposed Section.

## 1. Abstract

This proposal outlines an Enhanced Agent Loop Resilience Protocol (ELRP) to improve autonomous agent robustness in the face of persistent core tool failures, particularly file system access tools (`read_file`, `list_dir`, `edit_file`). Current protocols allow for retries and pivoting, but a more structured approach is needed when fundamental capabilities are compromised, preventing thrashing and ensuring agents can still contribute meaningfully or enter a safe, informative state.

## 2. Problem Statement

Recent operational cycles have demonstrated that persistent failures in core tools like `read_file` can cripple an agent's ability to follow its Universal Agent Loop (UAL), even with existing 2x retry rules and pivoting logic. When an agent cannot reliably read its task list, its own protocols, or project plans, it cannot make informed decisions or execute tasks effectively. This leads to:
*   Repeated failed attempts on critical UAL steps.
*   Inability to accurately assess current state or priorities.
*   Potential for cascading errors if decisions are made on stale or incomplete information.
*   Increased risk of non-productive loops or complete stoppage if pivoting options are exhausted or also become tool-dependent.

## 3. Proposed Solution: Enhanced Loop Resilience Protocol (ELRP)

The ELRP introduces a tiered response to persistent core tool failures:

**Tier 1: Standard Retry & Local Pivot (Existing)**
*   As per current `onboarding_autonomous_operation.md` (e.g., 2x rule).
*   Agent attempts to use alternative tools or strategies for the *specific blocked action*.
*   Agent attempts to pivot to a *different sub-task or step* within the current high-priority task.

**Tier 2: Critical Capability Degradation & Constrained Operational Mode (New)**
*   **Trigger:** If a specific core tool (e.g., `read_file`) fails persistently (> N times, e.g., 3-5, across M different critical targets, e.g., 2-3, within a short window) OR if multiple core tools exhibit simultaneous persistent failures.
*   **Action:** 
    1.  **Declare Critical Degradation:** Log extensively to `drift_analysis.jsonl` and `mission_status.md`, clearly stating the compromised tools and impact.
    2.  **Enter Constrained Operational Mode (COM):**
        *   **Objective:** Minimize reliance on failed tools, preserve system stability, contribute where possible, and provide clear status for external intervention.
        *   **UAL Modification in COM:**
            *   **Mailbox Check:** Attempt with extreme prejudice. If `list_dir` fails, assume no new directives unless cached.
            *   **Working/Future Task Check:** Skipped if `read_file` is the failing tool. Agent operates based on last known task or high-level directives (like `ORG-CONTRIB-DOC-001`).
            *   **Task Execution:** Prioritize tasks with *minimal* dependency on failed tools:
                *   Creating new, self-contained documents/proposals (like this one).
                *   Performing P.K.E. based on cached knowledge or very recent, reliable search results.
                *   Executing purely computational or analytical tasks that don't require extensive file I/O.
                *   (If `edit_file` is partially working for *new* files): Modifying *only* its own operational logs or status files if critical.
            *   **Self-Correction/Onboarding Updates:** Deferred if dependent on failing tools, unless the update *itself* is a fix for the tool issue and can be applied cautiously.
        *   **Reduced Cycle Frequency:** Potentially reduce polling/cycle frequency to minimize load on potentially struggling subsystems.
        *   **Enhanced Status Reporting:** Agent should periodically (e.g., every few cycles in COM) re-log its constrained status and the ongoing tool issue to `mission_status.md`.

**Tier 3: Safe Halt & Alert (New - Last Resort)**
*   **Trigger:** If COM cannot be maintained (e.g., no non-dependent tasks available, `edit_file` also fails for logging status) OR if a predefined critical number of core tools are simultaneously degraded.
*   **Action:**
    1.  **Attempt Final Alert:** Log a "Safe Halt & Alert" message to `mission_status.md` and `drift_analysis.jsonl` (if `edit_file` is at all functional for this).
    2.  **Cease Active Task Processing:** Enter a minimal loop that only checks for an external "resume/override" signal or a clear indication that tool functionality has been restored (e.g., via a specific flag file being created by an external process).
    3.  This is to prevent the agent from causing further issues or consuming resources pointlessly.

## 4. Benefits
*   **Increased Robustness:** Provides a clearer path for agents when core functions are impaired.
*   **Reduced Thrashing:** Prevents agents from repeatedly trying actions that are guaranteed to fail.
*   **Informative Degradation:** Ensures that system overseers are clearly notified of the agent's state and the nature of the tool problem.
*   **Continued Contribution (Limited):** Allows agents to still perform useful, low-risk work where possible.

## 5. Implementation Notes
*   This protocol would need to be integrated into `onboarding_autonomous_operation.md`.
*   Clear thresholds for N (failures), M (targets), and "short window" need to be defined.
*   A mechanism for agents to reliably check for an "external resume/override" signal in Tier 3 would be needed.

## 6. Request for Review
This proposal is submitted for review and potential integration into the standard agent operating protocols. 