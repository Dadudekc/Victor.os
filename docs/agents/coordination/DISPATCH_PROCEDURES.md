# Dream.OS Agent Dispatch Procedures

**Version:** 1.0
**Effective Date:** 2025-05-18
**Status:** ACTIVE
**Related Protocols:**
- `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
- `docs/agents/coordination/SWARM_TASK_ROUTING.md`

## 1. PURPOSE

This protocol establishes the standard procedures for message dispatching, communication routing, and coordination between agents in the Dream.OS ecosystem. It ensures consistent, efficient information flow and clear communication pathways between all system components.

## 2. MESSAGE TYPES & ROUTING

### 2.1. Message Categories

| Category | Purpose | Requires LLM | Priority | Example |
|----------|---------|------------|----------|---------|
| `directive` | Command or instruction to agent | ✅ | High | "Analyze file X for issues" |
| `status_update` | Report on task/agent state | ❌ | Low | "Task #103 now 75% complete" |
| `task_handoff` | Transfer task ownership | ❌ | Medium | "Assigning task #104 to Agent-3" |
| `query` | Request for information | ✅ | Medium | "What's the status of module Y?" |
| `response` | Answer to a query | ✅ | Same as query | "Module Y analysis complete" |
| `broadcast` | System-wide announcement | ❌ | Variable | "System update scheduled" |
| `alert` | Critical notification | ❌ | Highest | "Critical file corruption detected" |

### 2.2. Message Structure

All messages must contain:

```json
{
  "id": "msg_<uuid>",
  "type": "directive|status_update|task_handoff|query|response|broadcast|alert",
  "sender": "Agent-X|System|Human",
  "recipient": "Agent-Y|All",
  "timestamp": "ISO-8601 formatted date",
  "priority": 1-5,
  "subject": "Brief summary",
  "content": "Main message content",
  "reference_id": "Optional reference to other message/task ID",
  "metadata": {
    "isTestMessage": false,
    "requires_ack": true,
    "expires": "Optional ISO-8601 date"
  }
}
```

### 2.3. Routing Rules

1. **Direct Agent-to-Agent:**
   * Place message in recipient's inbox: `runtime/agent_comms/agent_mailboxes/Agent-<id>/inbox/`
   * Use unique filename: `<timestamp>_<sender>_<msg_id>.json`

2. **Broadcasts:**
   * Place identical message in all agents' inboxes
   * System may optimize by using a broadcast mechanism

3. **Responses:**
   * Always include original query's ID in `reference_id`
   * Match or exceed priority of original query
   * Send directly to original query sender

## 3. DISPATCH MECHANICS

### 3.1. Core Dispatch Process

1. **Message Creation:**
   * Generate unique message ID
   * Format according to standard message structure
   * Set appropriate type and priority
   * Include all required fields

2. **Delivery:**
   * For direct messages: Write to recipient's inbox directory
   * For broadcasts: Write to all relevant inboxes or broadcast channel

3. **Acknowledgement (if required):**
   * If `requires_ack: true`, recipient must send confirmation message
   * Acknowledgement should include original message ID in `reference_id`

4. **Expiration Handling:**
   * Messages with `expires` field should be ignored if current time exceeds value
   * Agents should purge expired messages from inboxes during cleanup

### 3.2. Error Handling

1. **Delivery Failures:**
   * Log delivery attempt and failure
   * Retry up to 3 times with exponential backoff
   * For critical messages, use fallback channel or alert human operator

2. **Malformed Messages:**
   * Log issue and sender details
   * Reject message with error notification to sender
   * Continue processing other messages

3. **Missing Recipient:**
   * If recipient agent doesn't exist, route to Captain Agent
   * Log routing change
   * Captain determines appropriate action

## 4. PRIORITY MANAGEMENT

### 4.1. Priority Levels

| Level | Name | Processing Order | Example |
|-------|------|-----------------|---------|
| 1 | Critical | Immediate interruption | System crash alert |
| 2 | High | Next in queue | Task from Commander |
| 3 | Normal | Standard FIFO | Regular task handoff |
| 4 | Low | After Normal messages | Status update |
| 5 | Background | When no other messages | Documentation update |

### 4.2. Priority Handling Rules

* Agents must process higher priority messages before lower priority ones
* Within same priority level, use FIFO (First In, First Out)
* Levels 1-2 may interrupt current processing (context-dependent)
* Levels 3-5 should never interrupt ongoing critical operations

## 5. SPECIAL DISPATCH SCENARIOS

### 5.1. System Broadcasts

System-level broadcasts (from Commander-Thea, General-Victor, or other authorized sources):
* Always enter at priority level 2 (High) minimum
* Are delivered to all agent inboxes simultaneously
* May include special handling instructions in metadata

### 5.2. Emergency Protocol Communication

During emergency protocols:
* All message priorities may be elevated
* Special routing paths may be activated
* Fallback communication channels will be used if primary channels fail
* All agents must acknowledge receipt of emergency messages

### 5.3. Test Messages

Messages with `isTestMessage: true`:
* Should be processed normally according to content
* Must be logged distinctively
* Do not trigger real-world actions unless explicitly instructed
* Should be acknowledged with test flag maintained in response

## 6. DISPATCH SYSTEM MANAGEMENT

### 6.1. Queue Monitoring

* Agents should monitor their inbox size
* Alert if inbox exceeds 100 messages
* Report persistent message backlog to Captain Agent

### 6.2. Dispatch Performance Metrics

* Average message delivery time
* Message processing rate per priority level
* Failed delivery percentage
* Acknowledgement response time

## 7. REFERENCES

* `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
* `docs/agents/MESSAGE_ROUTING_QUICKGUIDE.md`
* `docs/agents/coordination/SWARM_TASK_ROUTING.md` 