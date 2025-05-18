# Standard Mailbox Message Format

**Version:** 1.0 **Status:** Active Standard **Date:** [AUTO_DATE] **Related
Protocols:** `docs/swarm/onboarding_protocols.md` **Utility Functions:**
`src/dreamos/agents/utils/agent_utils.py` (`create_mailbox_message`,
`write_mailbox_message`, etc.)

## Overview

To ensure consistent, reliable, and machine-parsable communication between
agents via the Mailbox system
(`runtime/agent_comms/agent_mailboxes/<AgentID>/inbox/`), all **new** messages
placed in an agent's inbox directory **MUST** be valid `.json` files adhering to
the standard schema defined below.

Legacy formats (e.g., unstructured `.txt` files) are deprecated for direct
messaging and should be phased out.

## Mandatory JSON Format

Messages MUST be JSON objects with the following structure and key fields:

```json
{
  "message_id": "<UUID String>",
  "sender_agent_id": "<Agent ID String>",
  "recipient_agent_id": "<Agent ID String>",
  "timestamp_utc": "<ISO 8601 UTC Timestamp String>",
  "subject": "<Brief Subject String>",
  "type": "<MessageType String>",
  "body": "<Payload (String or Nested JSON Object)>",
  "priority": "<Priority String (Optional)>"
}
```

## Field Definitions

- **`message_id` (String, Mandatory):** A unique identifier (UUID v4
  recommended) for this specific message instance.
  - _Utility:_ `create_mailbox_message` generates one automatically if not
    provided.
- **`sender_agent_id` (String, Mandatory):** The unique ID of the agent sending
  the message.
- **`recipient_agent_id` (String, Mandatory):** The unique ID of the agent
  intended to receive the message.
- **`timestamp_utc` (String, Mandatory):** The UTC timestamp when the message
  was created, in ISO 8601 format (e.g., `YYYY-MM-DDTHH:MM:SS.ffffffZ` or
  `YYYY-MM-DDTHH:MM:SSZ`).
  - _Utility:_ `create_mailbox_message` generates one automatically using
    `get_utc_iso_timestamp()` if not provided.
- **`subject` (String, Mandatory):** A brief, human-readable summary of the
  message's purpose.
- **`type` (String, Mandatory):** A standardized string indicating the message
  category or intent. Standard types include (but are not limited to):
  - `TASK_ASSIGNMENT`
  - `STATUS_QUERY`
  - `INFO`
  - `REVIEW_REQUEST`
  - `ERROR`
  - `FEEDBACK`
  - `COMMAND`
  - `RESPONSE`
  - `SYSTEM_ALERT`
  - `ONBOARDING_COMMITMENT`
  - (Refer to `MailboxMessageType` Literal in `agent_utils.py` for current
    list).
- **`body` (String | Object, Mandatory):** The main payload of the message. This
  can be a simple string or a nested JSON object containing structured data
  relevant to the message `type`.
- **`priority` (String, Optional):** An optional field indicating the message
  priority. Standard values:
  - `LOW`
  - `MEDIUM` (Default if omitted by `create_mailbox_message`)
  - `HIGH`
  - `CRITICAL`
  - `INFO`
  - (Refer to `MailboxMessagePriority` Literal in `agent_utils.py` for current
    list).

## Utility Functions

Agents SHOULD utilize the helper functions provided in
`src/dreamos/agents/utils/agent_utils.py` to ensure compliance with this
standard:

- `create_mailbox_message()`: Constructs a valid message dictionary.
- `validate_mailbox_message_schema()`: Checks if a dictionary conforms to the
  schema.
- `write_mailbox_message()`: Writes a message dictionary to the recipient's
  inbox as a correctly named `.json` file.
- `read_mailbox_message()`: Reads and validates a message file from an inbox.

## Example (Info Message)

```json
{
  "message_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "sender_agent_id": "Agent1",
  "recipient_agent_id": "Agent8",
  "timestamp_utc": "2025-04-29T18:30:00Z",
  "subject": "Onboarding Feedback Summary Processed",
  "body": {
    "feedback_ref": "runtime/agent_comms/agent_mailboxes/Agent8/inbox/onboarding_feedback_agent1_msg_001.json",
    "status": "Acknowledged",
    "notes": "Feedback points logged for potential protocol refinement task generation."
  },
  "priority": "INFO",
  "type": "INFO"
}
```

## Legacy Message Handling

A plan for processing or archiving legacy non-JSON messages in mailboxes needs
to be developed (tracked separately). For now, agents processing their inboxes
should prioritize reading `.json` files using `read_mailbox_message` and may
need fallback logic (or generate errors/warnings) for older formats.
