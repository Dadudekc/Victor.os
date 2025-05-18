# Dream.OS Messaging Format

**Version:** 1.0
**Effective Date:** 2025-05-20
**Status:** ACTIVE

## 📎 See Also

For a complete understanding of agent protocols, see:
- [Agent Onboarding Index](runtime/agent_comms/governance/onboarding/AGENT_ONBOARDING_INDEX.md) - Complete protocol documentation
- [Agent Onboarding Protocol](runtime/agent_comms/governance/protocols/AGENT_ONBOARDING_PROTOCOL.md) - Main onboarding process
- [Agent Operational Loop Protocol](runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md) - Core operational loop
- [Response Validation Protocol](runtime/agent_comms/governance/protocols/RESPONSE_VALIDATION_PROTOCOL.md) - Response standards
- [Resilience And Recovery Protocol](runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md) - Error handling
- [Agent Devlog Protocol](runtime/agent_comms/governance/protocols/AGENT_DEVLOG_PROTOCOL.md) - Development logging

## 1. PURPOSE

This protocol defines the standard message formats for all communication within the Dream.OS ecosystem. It establishes the structure, content requirements, and processing rules for inter-agent messages, ensuring consistent and reliable information exchange.

## 2. MESSAGE STRUCTURE

### 2.1. Core Message Format

All messages in the Dream.OS ecosystem must follow this JSON format:

```json
{
  "message_id": "unique-id-string",
  "timestamp": "ISO-8601-datetime",
  "sender": "Agent-N",
  "recipient": "Agent-M",
  "message_type": "type-string",
  "priority": 1-5,
  "content": {
    "subject": "message-subject",
    "body": "message-body",
    "metadata": {}
  },
  "isTestMessage": false,
  "requires_response": true|false
}
```

### 2.2. Required Fields

* **message_id**: Unique identifier for the message
* **timestamp**: ISO-8601 formatted timestamp (UTC)
* **sender**: ID of the sending agent
* **recipient**: ID of the receiving agent
* **message_type**: Type classification (see Section 3)
* **content**: The actual message content
* **priority**: Urgency level (1-5, where 1 is highest)

## 3. MESSAGE TYPES

### 3.1. Primary Message Types

| Type | Description | Required Fields | Processing Priority |
|------|-------------|-----------------|---------------------|
| `task_handoff` | Task assignment/transfer | task_id, deadline | High |
| `status_update` | Agent status reporting | status, details | Medium |
| `help_request` | Assistance solicitation | issue, context | High |
| `command` | Directive/instruction | action, parameters | Highest |
| `information` | Knowledge sharing | subject, body | Low |
| `response` | Reply to previous message | ref_message_id | Medium |
| `alert` | Critical notification | severity, details | Highest |

### 3.2. Type-Specific Requirements

#### 3.2.1 Task Handoff
```json
{
  "content": {
    "task_id": "task-12345",
    "task_name": "Implement file validation",
    "description": "Create a utility to validate file integrity",
    "deadline": "2025-05-25T23:59:59Z",
    "priority": 2,
    "dependencies": ["task-12340", "task-12342"],
    "resources": ["docs/specs/file_validation.md"]
  }
}
```

#### 3.2.2 Status Update
```json
{
  "content": {
    "status": "active",
    "current_task": "task-12345",
    "progress": 75,
    "blockers": [],
    "estimated_completion": "2025-05-21T14:00:00Z"
  }
}
```

## 4. MESSAGE PROCESSING

### 4.1. Processing Rules

1. **Priority Handling**: Process messages in priority order
2. **Timestamp Validation**: Discard messages with future timestamps
3. **Duplicate Detection**: Check message_id against processed messages
4. **Type Validation**: Verify message structure against type schema
5. **Response Handling**: Honor requires_response flag

### 4.2. Error Handling

* **Malformed Messages**: Log error, notify sender if possible
* **Invalid References**: Process message but note reference error
* **Unsupported Types**: Reject with appropriate error response

## 5. MESSAGE FLOW

### 5.1. Standard Message Lifecycle

1. **Creation**: Message created by sender with unique ID
2. **Delivery**: Placed in recipient's inbox
3. **Receipt**: Recipient polls inbox and processes message
4. **Processing**: Recipient handles message according to type
5. **Response**: If required, recipient generates response message
6. **Archival**: Message moved to processed folder after handling

### 5.2. Response Chaining

* Include original message_id in ref_message_id field
* Maintain same subject with optional "Re:" prefix
* Include relevant quotes from original message when appropriate

## 6. IMPLEMENTATION GUIDELINES

### 6.1. Message Storage

* Store messages as individual JSON files
* Name files using pattern: `{timestamp}_{message_id}.json`
* Organize in sender/recipient-specific folders
* Maintain separate inbox/outbox/processed directories

### 6.2. Security Considerations

* Do not include sensitive information in standard messages
* Validate sender identity when processing high-priority messages
* Implement rate limiting for message generation

## 7. COMPLIANCE

All agents must adhere to this messaging format for all communications. Non-compliant messages may be rejected or trigger validation failures in the receiving agent's processing pipeline.

## 8. REFERENCES

* `runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
* `runtime/agent_comms/governance/protocols/RESPONSE_VALIDATION_PROTOCOL.md` 