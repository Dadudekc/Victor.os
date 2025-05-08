# Proposal: Agent Status Signaling Mechanism

**Task ID:** `AGENT2-COORDINATION-AGENT-STATUS-SIGNAL-005`
**Author:** Agent-2 (Coordination Expert)
**Date:** {{iso_timestamp_utc()}}
**Related Audit Report:** `specs/reports/agent2_coordination_mailbox_audit_001.md`

## 1. Introduction & Goal
This document proposes a lightweight mechanism for agents to signal their operational status. The goal is to provide other agents and monitoring systems with a way to understand an agent's general availability and responsiveness, thereby managing inter-agent expectations and aiding in the diagnosis of communication issues (e.g., distinguishing an offline agent from one that is merely busy).
This addresses Recommendation 4 from the audit report `specs/reports/agent2_coordination_mailbox_audit_001.md` concerning unread messages and responsiveness.

## 2. Proposed Mechanism: Per-Agent Status File

It is proposed that each agent maintains a simple JSON status file in a designated, globally known location. This file would be updated by the agent itself periodically or upon significant state changes.

### 2.1. Status File Naming Convention
- **Standard:** `agent-<ID_lowercase>.status.json`
- **Location:** `runtime/agent_status/` (A new directory specifically for these status files, sibling to `runtime/agent_comms/`)
- **Rationale:**
    -   Consistent naming aligned with the proposed mailbox naming standard.
    -   Dedicated directory keeps status files separate from mailbox communication channels.
- **Example:** `runtime/agent_status/agent-1.status.json`

### 2.2. Status File JSON Structure
- **Standard:** A single JSON object at the root.
- **Required Fields:**
    -   `agent_id`: (String) The canonical ID of the agent (e.g., "agent-1").
    -   `status`: (String) One of the predefined status values (see section 2.3).
    -   `last_updated_timestamp`: (String) ISO 8601 UTC timestamp of when this status was last written by the agent.
    -   `message`: (String, Optional) A brief, human-readable message providing context for the current status (e.g., "Processing CRITICAL task X", "Offline for scheduled maintenance until YYYY-MM-DDTHH:MM:SSZ").
- **Example:**
  ```json
  {
    "agent_id": "agent-1",
    "status": "ACTIVE_PROCESSING",
    "last_updated_timestamp": "{{iso_timestamp_utc()}}",
    "message": "Currently executing task TASK-XYZ-001. Expected completion in 15m."
  }
  ```
  Or for an idle agent:
  ```json
  {
    "agent_id": "agent-3",
    "status": "IDLE_AWAKE",
    "last_updated_timestamp": "{{iso_timestamp_utc()}}",
    "message": "Monitoring mailbox. No active tasks."
  }
  ```

### 2.3. Predefined Agent Status Values
-   **`ACTIVE_PROCESSING`**: The agent is currently online, awake, and actively working on one or more tasks. Mailbox checks might be less frequent.
-   **`IDLE_AWAKE`**: The agent is online, awake, and actively monitoring its mailbox and task lists, but has no current tasks it is processing. Expected to be responsive to new messages/tasks.
-   **`OFFLINE_EXPECT_DELAY`**: The agent is intentionally offline or in a state where it cannot process messages/tasks (e.g., scheduled maintenance, critical error recovery mode not involving communication). The optional `message` field should provide more context if possible (e.g., expected return time).
-   **`UNKNOWN`**: Initial state before an agent writes its first status, or if a status file is unreadable/corrupted. Monitoring systems might treat this as a potential issue.
-   **`ERROR_STATE`**: The agent has encountered an unrecoverable internal error and may not be functioning correctly. The `message` field should ideally contain error details.

### 2.4. Agent Responsibilities
-   Each agent capable of this signaling MUST update its status file:
    -   Upon startup (to `IDLE_AWAKE` or `ACTIVE_PROCESSING` if it immediately claims work).
    -   When transitioning between major states (e.g., from `IDLE_AWAKE` to `ACTIVE_PROCESSING` upon claiming a task, and back upon completion).
    -   Periodically (e.g., every 5-15 minutes if in a long-running `ACTIVE_PROCESSING` state, or during its main loop's idle phase for `IDLE_AWAKE`) to update `last_updated_timestamp`.
    -   Before planned shutdown (to `OFFLINE_EXPECT_DELAY`).
-   Updates should be atomic writes to avoid corruption (write to temp, then rename).

### 2.5. Consumer Responsibilities (Other Agents / Monitoring Systems)
-   Agents wishing to check another agent's status can read the corresponding status file.
-   They should be resilient to missing files or parse errors (treat as `UNKNOWN` or log an issue).
-   They should consider the `last_updated_timestamp` to gauge how fresh the status information is. A very old timestamp might indicate the agent is truly offline or stuck, even if its last reported status was `ACTIVE_PROCESSING`.

## 3. Alternatives Considered & Rejected
-   **Status via Mailbox Messages:** Sending status updates as messages to a broadcast channel or a dedicated status agent. Rejected because: mailboxes are for discrete communications; frequent status updates would clutter mailboxes; relies on the mailbox system itself being perfectly functional to report status, which might not be the case if an agent is having trouble with its mailbox.
-   **Status Field in Mailbox File Itself:** Adding a status field to the mailbox JSON. Rejected because: mixes concerns; the mailbox is primarily for incoming messages, not for broadcasting agent state. Agent 9's `loop_state` is an example of this, which the canonical proposal aims to simplify.

## 4. Benefits
-   **Improved Transparency:** Provides a clear way to check an agent's general availability.
-   **Managed Expectations:** Helps agents determine if a peer is likely to respond quickly or if delays are expected.
-   **Aid to Diagnostics:** Assists in differentiating between an agent that is busy, an agent that is offline, or an agent that is stuck/crashed (e.g., old timestamp with `ACTIVE_PROCESSING` status).
-   **Lightweight:** Simple file I/O, avoids complex new messaging protocols for status.

## 5. Future Considerations
-   **Standardized `message` field content:** For some statuses like `ERROR_STATE`, a more structured `message` (e.g., JSON object with error code and details) could be defined.
-   **Integration with a Central Monitoring Dashboard:** These status files could be a data source for a swarm health dashboard.

This proposal provides a basic but effective way to increase visibility into agent states, supporting better inter-agent coordination and system monitoring. 