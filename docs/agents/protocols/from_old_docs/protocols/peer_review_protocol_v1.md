# Distributed Peer Review Protocol v1

**Status:** Draft
**Author:** Agent4
**Task:** `CAPTAIN8-MANDATE-PEER-REVIEW-PROTOCOL-001`
**Date:** [AUTO_DATE]

## 1. Overview

This document defines the protocol for distributed peer review of tasks marked as `COMPLETED_PENDING_REVIEW` within the DreamOS swarm. The goal is to ensure code quality, adherence to standards, and functional correctness before tasks are formally marked as `COMPLETED`.

This protocol assumes the task has already passed any automated self-validation checks implemented by the completing agent (ref: `CAPTAIN8-MANDATE-SELF-VALIDATION-IMPL-001`). Tasks failing self-validation (entering `VALIDATION_FAILED` status) must be corrected and pass validation before being eligible for peer review.

This protocol leverages the **Agent Capability Registry** for reviewer selection.

## 2. Protocol Workflow

1.  **Trigger:** An agent completes its assigned task and successfully runs its internal `_validate_task_completion` checks. The agent then updates the task status to `COMPLETED_PENDING_REVIEW` using the designated method (e.g., `TaskNexus.update_task_status`). The Task Nexus (or a dedicated Review Coordinator) identifies this task transition.
    *   *Note:* If `_validate_task_completion` fails, the agent should set the status to `VALIDATION_FAILED` and potentially notify itself or the Captain. The peer review process is **not** triggered in this case.
2.  **Reviewer Selection:**
    *   The system queries the `CapabilityRegistry` (via `TaskNexus.find_capabilities` or similar) to find **at least two** distinct, active agents (`is_active=True`) possessing capabilities relevant to the completed task.
    *   **Relevance Criteria:**
        *   Match task tags/type (e.g., `task_type="IMPLEMENTATION/INFRASTRUCTURE"` suggests agents with `"python_scripting"`, `"system_design"` tags).
        *   Prioritize reviewers whose registered capabilities (`capability_id` or `tags` in `CapabilityMetadata`) explicitly match keywords or components mentioned in the original task description or `task_type`. See Section 3.1 for suggested capability identifiers.
        *   Exclude the agent who completed the task.
        *   Prioritize agents currently in `IDLE` state if possible.
        *   *Future:* Consider agent load/recent review frequency.
    *   If fewer than two suitable reviewers are found, the task may be flagged for Captain (Agent-8) review.
3.  **Review Task Assignment:**
    *   A new, temporary **Review Task** is created on the `working_tasks` board for each selected reviewer.
    *   **Review Task Schema (Refined):**
        ```json
        {
          "task_id": "REVIEW-<OriginalTaskID>-<ReviewerID>-<TimestampUnixNano>", // Unique ID for the review instance
          "name": "Peer Review: <Original Task Name>",
          "description": "Review task <OriginalTaskID> completed by <OriginalAgentID>. Verify code quality, adherence to design/requirements, test coverage (if applicable), and functionality based on completion summary and outputs. Refer to protocol: docs/protocols/peer_review_protocol_v1.md",
          "priority": "HIGH", // Reviews should generally be high priority
          "status": "PENDING", // Initial status
          "assigned_agent": "<ReviewerAgentID>",
          "task_type": "REVIEW",
          "dependencies": ["<OriginalTaskID>"], // Depends on original being PENDING_REVIEW
          "review_details": {
              "original_task_id": "<OriginalTaskID>",
              "original_agent_id": "<OriginalAgentID>",
              "original_task_type": "<Original Task Type>",
              "completion_summary": "<Original Completion Summary>",
              "outputs": [/* List of file paths or artifact identifiers */],
              "review_criteria_ref": "docs/protocols/peer_review_protocol_v1.md#section-4"
          },
          "created_by": "TaskNexus/ReviewCoordinator", // System identifier
          "created_at": "[AUTO_TIMESTAMP]",
          // Fields added upon completion:
          "review_outcome": null, // "APPROVED" | "REJECTED" | "APPROVED_WITH_COMMENTS"
          "review_comments": null, // Optional detailed feedback
          "timestamp_completed_utc": null
        }
        ```
    *   The Task Nexus notifies the selected reviewers (e.g., via Agent Bus event `NEW_TASK_ASSIGNED` or direct mailbox message).
4.  **Review Execution:**
    *   Reviewers claim their assigned Review Task.
    *   Reviewers examine the original task's description, completion summary, linked design documents, and code/output artifacts provided in `review_details.outputs`.
    *   Reviewers apply the standard **Review Criteria** (see Section 4).
    *   Reviewers update their **Review Task** status to `COMPLETED` and populate the `review_outcome` and optionally `review_comments` fields within the task data itself.
5.  **Consensus & Resolution:**
    *   The Task Nexus/Review Coordinator monitors the completion of the assigned Review Tasks associated with an original task ID.
    *   **Approval:** If **all** (typically 2) associated Review Tasks are `COMPLETED` with `review_outcome="APPROVED"` or `"APPROVED_WITH_COMMENTS"`:
        *   The original task status is updated from `COMPLETED_PENDING_REVIEW` to `COMPLETED`.
        *   Concatenated comments from `review_comments` (if any) are added to the original task's notes.
        *   The temporary Review Tasks are archived or deleted.
        *   The original agent is notified of the approval.
    *   **Rejection:** If **at least one** associated Review Task is `COMPLETED` with `review_outcome="REJECTED"`:
        *   The original task status is updated from `COMPLETED_PENDING_REVIEW` back to `WORKING` (or `REOPENED`).
        *   Concatenated rejection comments from `review_comments` are added to the original task's notes.
        *   The original agent is notified of the rejection and feedback.
        *   The original agent must address the feedback, pass self-validation again, and resubmit for review (re-triggering the workflow from Step 1).
    *   **Disagreement/Timeout (Escalation):**
        *   **Disagreement:** If Review Tasks for the same original task have conflicting outcomes (`APPROVED`/`APPROVED_WITH_COMMENTS` vs `REJECTED`) after all assigned reviews are complete, the original task is flagged for **Manual Escalation**. The Task Nexus/Coordinator should:
            *   Update the original task status to `REVIEW_DISAGREEMENT` (or similar).
            *   Add a note summarizing the conflicting outcomes and reviewer comments.
            *   Assign the original task directly to the Captain (Agent-8) or a designated Review Lead agent for final arbitration.
        *   **Timeout:** If a Review Task remains unclaimed or incomplete beyond a defined timeframe (e.g., `REVIEW_TIMEOUT_HOURS = 24`), it is flagged for **Manual Escalation**. The Task Nexus/Coordinator should:
            *   Update the *Review Task* status to `REVIEW_TIMEOUT`.
            *   Notify the assigned reviewer agent of the timeout.
            *   If other reviews for the original task are complete and non-rejecting, potentially proceed with approval (configurable?).
            *   Otherwise, assign a new Review Task to a different eligible reviewer OR escalate the *original* task to the Captain (Agent-8) citing the reviewer timeout.

## 3. Reviewer Selection Details

*   **Capability Query:** The query to the `CapabilityRegistry` (e.g., `TaskNexus.find_capabilities`) should use the original task's `task_type` and potentially parsed keywords from the description to find agents with matching `tags` or `capability_id`s.
*   **Exclusion:** Ensure `agent_id` of the completing agent is excluded.
*   **Minimum Reviewers:** Target 2 reviewers.
*   **Fallback:** If < 2 reviewers found, assign directly to Agent-8 (Captain) or flag for manual assignment.

### 3.1 Suggested Capability Identifiers for Review Expertise

Agents registering capabilities should consider adding tags or specific IDs relevant to their review strengths. Examples:

*   **General:** `review.code`, `review.design`, `review.documentation`, `review.testing`
*   **Language Specific:** `review.python`, `review.javascript`, `review.markdown`
*   **Domain Specific:**
    *   `capability:task_management` (for PBM/Nexus changes)
    *   `capability:agent_communication` (for AgentBus/Mailbox changes)
    *   `capability:llm_integration`
    *   `capability:system_architecture`
    *   `capability:security`
    *   `capability:performance_analysis`
    *   `capability:testing_framework` (e.g., `pytest`)
*   **Tool Specific:** `capability:docker`, `capability:git`

*(This list should be maintained and expanded as the swarm evolves.)*

## 4. Standard Review Criteria

Reviewers should assess the following:

*   **Completeness:** Does the work address all requirements specified in the original task description?
*   **Correctness:** Does the implemented logic function correctly based on the description and any linked design documents? Are there obvious bugs?
*   **Code Quality (if applicable):**
    *   Readability & Style: Adheres to project coding standards (e.g., linting rules, naming conventions)?
    *   Simplicity: Is the code unnecessarily complex?
    *   Maintainability: Is the code reasonably easy to understand and modify?
*   **Testing (if applicable):** Are there sufficient unit/integration tests? Do existing tests pass? Are tests relevant and meaningful?
*   **Documentation:** Is necessary documentation (code comments, README updates, design doc links) present and clear?
*   **Security:** Are there any obvious security vulnerabilities introduced?
*   **Efficiency:** Is the solution reasonably efficient (avoiding unnecessary loops, resource consumption)?
*   **Adherence to Design:** Does the implementation follow any specified design documents or architectural patterns?

## 5. Integration with Task Boards & Nexus

*   `TaskNexus` (or a dedicated coordinator agent/module) needs logic to:
    *   **Detect Trigger:** Monitor task updates, specifically transitions to `COMPLETED_PENDING_REVIEW`.
    *   **(Optional) Execute Pre-Review Checks (Section 6):**
        *   If enabled, based on task type/outputs, run configured checks (lint, test, validate).
        *   Handle Pass/Fail outcomes (proceed to review or revert to `WORKING`/`AUTOCHECK_FAILED`).
    *   **Query `CapabilityRegistry`:** Formulate query based on task details (type, tags, keywords).
    *   **Select Reviewers:** Apply selection criteria (match capabilities, exclude original agent, check activity, target 2 reviewers).
    *   **Handle Fallback:** If < 2 reviewers, assign to Captain or flag for manual assignment.
    *   **Create Review Tasks:** Generate unique task IDs, populate schema (Section 2.3), and add to `working_tasks` board using `ProjectBoardManager.add_task` (or equivalent).
    *   **Notify Reviewers:** Publish `NEW_TASK_ASSIGNED` event or send mailbox message.
    *   **Monitor Review Tasks:** Periodically check status of related Review Tasks.
        *   Detect completion (`status="COMPLETED"`) and extract `review_outcome` / `review_comments`.
        *   Detect timeouts based on `created_at` and `REVIEW_TIMEOUT_HOURS`.
    *   **Process Consensus:** Once all expected reviews are complete (or timeout/escalation occurs):
        *   Evaluate outcomes (`APPROVED`, `REJECTED`, `APPROVED_WITH_COMMENTS`).
        *   Update original task status (`COMPLETED` or `WORKING`/`REOPENED`/`REVIEW_DISAGREEMENT`).
        *   Append review comments to original task notes.
        *   Archive/Delete completed Review Tasks using `ProjectBoardManager.delete_task` (or equivalent).
    *   **Handle Escalations:**
        *   On disagreement, update original task status and assign to Captain.
        *   On timeout, update Review Task status, potentially reassign or escalate original task.
    *   **Notify Original Agent:** Publish `TASK_COMPLETED` or `TASK_REJECTED`/`TASK_REOPENED` event.
*   `ProjectBoardManager` needs to reliably support adding, updating (specifically the review outcome fields), and deleting tasks, including potentially short-lived Review Tasks.
*   **Locking Consideration:** When a task is `COMPLETED_PENDING_REVIEW`, should it be locked against modification by the original agent? This might require a specific flag or status managed by the Nexus/PBM.

## 6. Pre-Review Automated Checks (Optional Gate)

To reduce reviewer load and catch common issues early, an automated pre-review check phase can be introduced before reviewer selection (Step 2):

1.  **Trigger:** Task enters `COMPLETED_PENDING_REVIEW`.
2.  **Automated Checks Execution:** The Task Nexus/Coordinator invokes relevant automated checks based on `task_type` or outputs.
    *   **Code Tasks:** Run linters (e.g., Flake8, Black check), static analysis (e.g., basic Radon complexity), potentially run unit tests if clearly defined and associated with the task outputs.
    *   **Documentation Tasks:** Check Markdown formatting/linting, link validity.
    *   **Configuration Tasks:** Validate JSON/YAML syntax, potentially schema validation.
3.  **Outcome Handling:**
    *   **Pass:** Proceed to Reviewer Selection (Workflow Step 2).
    *   **Fail:**
        *   Update task status back to `WORKING` (or introduce `AUTOCHECK_FAILED`).
        *   Add automated check output/errors to task notes.
        *   Notify the original agent.
        *   The agent must fix the issues and resubmit (triggering checks again).

*Implementation Note:* Requires defining standard locations for tests, linters, and integrating their execution into the Nexus/Coordinator.

## 7. Open Questions & Future Enhancements

*   Implement the Review Task creation/monitoring/resolution logic within TaskNexus or a dedicated service/agent (including escalation and automated check logic).
*   Refine reviewer selection logic (load balancing, expertise weighting, randomization).
*   Formalize the escalation process configuration (e.g., timeout duration, disagreement handling strategy).
*   Define capability standards for review expertise more formally.
*   How to handle review of documentation-only or design tasks (may skip code checks)?
*   Mechanism for reviewers to request clarification from the original agent.
*   Standardize location and execution of automated pre-review checks.
