# Proposal: Canonical Agent Mailbox Naming and Structure Standard

**Task ID:** `AGENT2-COORDINATION-MAILBOX-STANDARD-002`
**Author:** Agent-2 (Coordination Expert)
**Date:** {{iso_timestamp_utc()}}
**Related Audit Report:** `specs/reports/agent2_coordination_mailbox_audit_001.md`

## 1. Introduction & Goal
This document proposes a standardized naming convention and JSON structure for agent mailboxes. The goal is to eliminate ambiguity, improve the reliability of inter-agent communication, and simplify mailbox management and parsing logic for all agents within the Dream.OS ecosystem.
This proposal directly addresses findings from the audit report `specs/reports/agent2_coordination_mailbox_audit_001.md`, specifically the observed inconsistencies in mailbox naming and internal structures.

## 2. Proposed Standards

### 2.1. Mailbox File Naming Convention
- **Standard:** `agent-<ID_lowercase>.json`
- **Rationale:**
    -   Uses a consistent prefix `agent-`.
    -   Agent ID should be consistently lowercase to avoid case-sensitivity issues (e.g., `agent-1.json`, `agent-thea.json` if alphanumeric IDs are used, or `agent-captain8.json`). If IDs are purely numeric, then `agent-1.json`, `agent-2.json`.
    -   Uses the `.json` extension as mailboxes store JSON data.
- **Example:**
    -   For Agent ID "1": `runtime/agent_comms/agent_mailboxes/agent-1.json`
    -   For Agent ID "CoCaptainThea": `runtime/agent_comms/agent_mailboxes/agent-cocaptainthea.json`
- **Action for existing mailboxes:** Existing mailboxes not conforming (e.g., `agent_1_mailbox.json`) should be renamed. Agents relying on old names must be updated.

### 2.2. Mailbox File JSON Structure
- **Standard:** The root of the JSON file MUST be a JSON Array `[]`.
- **Content:** Each element in the array MUST be a valid JSON Object representing a single message.
- **Empty Mailbox:** An empty mailbox MUST be represented by an empty JSON array: `[]`.
- **Rationale:**
    -   Simple, widely understood, and easy to parse by all agents.
    -   Allows for an ordered list of messages.
- **Example (Mailbox with one message):**
  ```json
  [
    {
      "message_id": "{{uuid()}}",
      "sender_id": "agent-source",
      "recipient_id": "agent-destination",
      "timestamp": "{{iso_timestamp_utc()}}",
      "type": "STANDARD_MESSAGE_TYPE",
      "subject": "Message Subject",
      "body": "Message body content.",
      "priority": "MEDIUM",
      "related_files": [],
      "response_to_message_id": null
    }
  ]
  ```

### 2.3. Message Object Structure (Recommended Minimum Fields)
While individual message schemas can vary by `type`, the following fields are recommended as a minimum common set for all messages to ensure basic interoperability and metadata:
- `message_id` (String, UUID recommended, globally unique)
- `sender_id` (String, canonical agent ID)
- `recipient_id` (String, canonical agent ID or broadcast group)
- `timestamp` (String, ISO 8601 UTC, e.g., `YYYY-MM-DDTHH:MM:SSZ`)
- `type` (String, e.g., `STATUS_REPORT`, `ERROR_REPORT`, `DIRECTIVE`, `REQUEST_FOR_INPUT`, `ACKNOWLEDGEMENT`, etc. - a future task will propose a standardized list of types)
- `subject` (String, brief summary)
- `body` (String, main content of the message)
- `priority` (String, e.g., `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, optional, defaults to `MEDIUM`)
- `related_files` (Array of strings, paths to relevant files, optional)
- `response_to_message_id` (String, `message_id` of the message this is a reply to, optional, null if not a reply)

## 3. Scope of Application & Transition
- **Scope:** This standard applies to all agent-to-agent communication occurring via the `runtime/agent_comms/agent_mailboxes/` JSON file system.
- **Transition Plan (High-Level):**
    1.  **Announcement:** Communicate this proposed standard to all relevant development teams/agents.
    2.  **Agent Updates:** Agents need to update their mailbox reading/writing logic to conform to the new naming and structure.
    3.  **File Migration:** A coordinated effort or script will be needed to:
        a.  Rename non-conforming mailbox files.
        b.  Restructure the content of non-conforming mailboxes.
    4.  **Deprecation of Directory-Based Mailboxes:** The role of directory-based mailboxes (e.g., `Agent-1/`) must be clarified. If they are for active messaging, they should either be migrated to this JSON standard or a clear justification for their separate system provided. If not for active messaging, they should be clearly marked as archival or for other non-communication purposes.

## 4. Benefits
- **Improved Reliability:** Reduces chances of missed messages due to agents looking in the wrong place or failing to parse different structures.
- **Simplified Agent Logic:** Agents only need to implement one method of reading/writing to mailboxes.
- **Enhanced Debugging:** Standardized mailboxes are easier to inspect and debug.
- **Foundation for Advanced Features:** A consistent base allows for easier implementation of future communication features (e.g., swarm-wide message bus, priority handling).

## 5. Open Questions / Future Considerations
-   The exact list of standardized message `type` values (Recommendation 5 from the audit report).
-   The precise plan and tooling for migrating existing mailboxes and updating agent logic.
-   The final decision on handling directory-based mailboxes.

This proposal aims to be a foundational step in improving inter-agent coordination. 