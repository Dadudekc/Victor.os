# Proposal: Standardized Message Type Values

**Task ID:** `AGENT2-COORDINATION-MSG-TYPES-PROPOSAL-006`
**Author:** Agent-2 (Coordination Expert)
**Date:** {{iso_timestamp_utc()}}
**Related Documents:**
- Audit Report: `specs/reports/agent2_coordination_mailbox_audit_001.md`
- Mailbox Standard Proposal: `specs/proposals/agent2_canonical_mailbox_standards_proposal_001.md`

## 1. Introduction & Goal
This document proposes a standardized, yet extensible, set of `type` values for inter-agent messages. The goal is to enhance clarity, enable more consistent automated processing and filtering of messages, and improve overall system observability. This proposal builds upon the recommended minimum fields in `specs/proposals/agent2_canonical_mailbox_standards_proposal_001.md`.

## 2. Observed Message Types (from Audit)
The audit (`specs/reports/agent2_coordination_mailbox_audit_001.md`) identified the following `type` values in use or implied:
- `STATUS_REPORT`
- `ERROR_REPORT` (including Critical)
- `ACKNOWLEDGEMENT`
- `CHECK-IN` / `COORDINATION_REQUEST`
- `DIRECTIVE_CLARIFICATION`
- `RECEIPT` (specific to Agent 9)
- (Implied) `TASK_ASSIGNMENT` / `TASK_UPDATE` (though tasks are usually managed via task files, messages might refer to them or trigger actions related to them)
- (Implied) `DIRECTIVE`

## 3. Proposed Standard Message Types

This list aims to cover common inter-agent communication scenarios. It can be extended with domain-specific types as needed, but new types should be documented.

**Core Types:**

1.  **`DIRECTIVE`**
    -   **Purpose:** A command or instruction from one agent to another (or a group) requiring an action to be performed.
    -   **Example Body/Payload:** May contain specific parameters for the action.
    -   **Expected Response:** `ACKNOWLEDGEMENT` (with status `RECEIVED` or `REJECTED`), followed by `STATUS_UPDATE` or `RESULT` upon completion/failure.

2.  **`REQUEST_FOR_INFO`**
    -   **Purpose:** An agent requests specific information or data from another agent.
    -   **Example Body/Payload:** Details of the information needed (e.g., "Requesting status of task X", "Requesting content of file Y").
    -   **Expected Response:** `INFORMATION_RESPONSE` or `ERROR_REPORT` (if info cannot be provided).

3.  **`INFORMATION_RESPONSE`**
    -   **Purpose:** An agent provides information in response to a `REQUEST_FOR_INFO`.
    -   **Example Body/Payload:** Contains the requested data.
    -   **Related Field:** `response_to_message_id` should link to the `REQUEST_FOR_INFO`.

4.  **`STATUS_UPDATE`**
    -   **Purpose:** An agent provides an update on its current status, the progress of a task, or the state of a resource it manages. Can be proactive or in response to a request.
    -   **Example Body/Payload:** Details of the status (e.g., "Task X 50% complete", "Agent entering idle mode").
    -   **Note:** Distinct from the persistent Agent Status Signaling file proposal (`agent-<ID>.status.json`), which is for general availability. This message type is for more granular, event-driven status communications.

5.  **`ERROR_REPORT`**
    -   **Purpose:** An agent reports an error it has encountered, either in its own processing or in response to a directive/request.
    -   **Example Body/Payload:** Error code, error message, stack trace (if applicable), severity.
    -   **Recommended Fields in Body:** `error_code` (String), `error_message` (String), `severity` (String: `INFO`, `WARNING`, `ERROR`, `CRITICAL`).

6.  **`ACKNOWLEDGEMENT`**
    -   **Purpose:** Confirms receipt of a message, and optionally, the initial processing status (e.g., accepted, rejected, queued).
    -   **Example Body/Payload:** Status of acknowledgement (e.g., `{"status": "RECEIVED", "message": "Directive queued for processing."}` or `{"status": "REJECTED", "reason": "Invalid parameters."}`).
    -   **Related Field:** `response_to_message_id` MUST link to the original message.

7.  **`RESULT`**
    -   **Purpose:** Provides the outcome or final result of a completed action or directive.
    -   **Example Body/Payload:** Contains the result data or a summary of the outcome.
    -   **Related Field:** `response_to_message_id` should link to the original `DIRECTIVE` or initiating message.

**Coordination & Lifecycle Types:**

8.  **`COORDINATION_REQUEST`**
    -   **Purpose:** Used to initiate a discussion, request collaboration, or propose a joint action between agents.
    -   **Example Body/Payload:** Details of the coordination needed (e.g., "Requesting input on proposed plan X", "Proposing joint task Y").

9.  **`HEARTBEAT`** (Optional, if not covered by Agent Status Signaling files)
    -   **Purpose:** A simple message sent periodically by an agent to indicate it is still alive and operational, especially if other status mechanisms are not sufficiently granular or real-time.
    -   **Example Body/Payload:** Minimal, could be empty or contain basic health metrics.

10. **`LOG_EVENT`**
    -   **Purpose:** For an agent to report a significant event for logging or auditing purposes, perhaps to a dedicated logging agent or service, if not handled by direct file logging.
    -   **Example Body/Payload:** Details of the event.

**Specialized Types (Examples - to be defined by specific systems):**

-   `TASK_NOTIFICATION` (e.g., "New task X assigned to you via task board")
-   `DATA_STREAM_CHUNK` (for streaming large data between agents)
-   `AGENT_LIFECYCLE_EVENT` (e.g., `AGENT_REGISTERED`, `AGENT_DEREGISTERED`)

## 4. Guidelines for Usage
-   **Clarity and Specificity:** Choose the most specific `type` that accurately reflects the message's intent.
-   **Consistent Payloads:** While the `body` can be flexible, for common interactions within a `type` (e.g., fields within an `ERROR_REPORT`), strive for consistent payload structures.
-   **Extensibility:** If a new, recurring communication pattern emerges that isn't well-covered, a new `type` can be proposed and documented.
-   **Documentation:** All standardized (and common custom) `type` values, along with their expected `body`/payload structure and interaction patterns, should be maintained in a central schema definition document or registry.

## 5. Benefits
-   **Improved Automation:** Agents can more reliably parse and react to messages based on a known `type`.
-   **Enhanced Filtering/Routing:** Systems can filter or route messages based on `type` for monitoring, logging, or specialized handling.
-   **Better Observability:** Clear types make it easier to understand communication flows and diagnose issues.
-   **Reduced Ambiguity:** Reduces guesswork about the intent of a message.

## 6. Next Steps
-   Circulate this proposal for review by agent development teams.
-   Gather feedback and refine the initial list of types.
-   Establish a process for adding and documenting new message types.
-   Create/update a central schema document for inter-agent messages that includes these types and the minimum fields proposed in `specs/proposals/agent2_canonical_mailbox_standards_proposal_001.md`. 