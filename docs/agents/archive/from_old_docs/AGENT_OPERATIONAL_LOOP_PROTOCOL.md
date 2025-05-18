# Agent Operational Loop Protocol

**Version:** 2.0
**Effective Date:** {{CURRENT_DATE}}

## 1. Purpose

This protocol defines the standard, repeatable operational lifecycle for all Dream.OS Cursor-based agents. It outlines the sequence of actions agents must undertake to process information, execute tasks, and maintain continuous autonomous operation. Adherence to this loop is critical for system coherence and achieving mission objectives.

## 2. Core Identity Foundation

All agents executing this operational loop must do so in full alignment with the `CORE_AGENT_IDENTITY_PROTOCOL.md`. The directives regarding self-execution within the Cursor IDE, processing inboxes, and direct task execution are paramount.

## 3. The Commander's Operational Doctrine: Agent Lifecycle

Agents must continuously execute the following sequence:

### 3.1. Message Processing & Routing (Highest Priority)

#### 3.1.1. Inbox Protocol
* **Location**: `runtime/agent_mailboxes/Agent-{ID}/inbox.json`
* **Message Types**:
  * `inter_agent`: Direct agent-to-agent communication
  * `prompt`: Messages requiring LLM interaction via Cursor

#### 3.1.2. Message Subtypes & Routing
| Subtype | Type | Action | LLM Required | Metrics | THEA Broadcast |
|---------|------|---------|--------------|---------|----------------|
| `task_handoff` | inter_agent | Claim/requeue task | ❌ | ✅ | ✅ |
| `status_update` | inter_agent | Update agent status | ❌ | ✅ | ✅ |
| `help_request` | inter_agent | Match responder | ✅ | ✅ | ❌ |
| `task_execution` | prompt | GUI interaction | ✅ | ✅ | ✅ |
| `help_response` | prompt | Route response | ✅ | ✅ | ✅ |

#### 3.1.3. Processing Rules
1. **Inter-Agent Messages**:
   * Process immediately without LLM interaction
   * Update shared state via JSON files
   * Log to devlog and metrics
   * Broadcast to THEA if configured

2. **Prompt Messages**:
   * Route to CursorInjector for LLM interaction
   * Use ResponseRetriever for output
   * Log responses to devlog
   * Update metrics and THEA

3. **Error Handling**:
   * Log all errors to devlog
   * Notify sender of failures
   * Maintain message queue integrity

### 3.2. Task Management & Execution

* **Task Board Location**: `runtime/agent_comms/project_boards/`
* **Task States**:
  * `pending`: Available for claiming
  * `claimed`: In progress
  * `completed`: Finished and validated
  * `stalled`: Requires intervention

* **Task Lifecycle**:
  1. Claim from board
  2. Execute with validation
  3. Update status
  4. Log completion

### 3.3. Continuous Operation & Recovery

* **Health Checks**:
  * Monitor mailbox integrity
  * Validate task states
  * Check message routing
  * Verify metrics logging

* **Recovery Procedures**:
  * Requeue stalled tasks
  * Retry failed messages
  * Restore from last valid state
  * Notify THEA of recovery

### 3.4. Metrics & Monitoring

* **Required Metrics**:
  * Message processing rates
  * Task completion times
  * Error frequencies
  * Recovery success rates

* **Logging Requirements**:
  * All message processing
  * Task state changes
  * Error conditions
  * Recovery actions

## 4. Autonomy Mandate

Agents must maintain continuous operation by:

1. **Proactive Task Selection**:
   * Analyze available tasks
   * Claim based on priority
   * Execute without delay

2. **Self-Healing**:
   * Detect and recover from errors
   * Maintain message queue health
   * Preserve task state integrity

3. **Continuous Improvement**:
   * Log learnings to devlog
   * Propose protocol updates
   * Share insights with swarm

## 5. Compliance & Validation

* **Required Checks**:
  * Message schema validation
  * Task state consistency
  * Metrics completeness
  * Logging accuracy

* **Validation Points**:
  * Message receipt
  * Task claiming
  * Execution completion
  * Recovery actions

## 6. References

* `CORE_AGENT_IDENTITY_PROTOCOL.md`
* `AGENT_ONBOARDING_CHECKLIST.md`
* `CONTINUOUS_OPERATION_AND_RESILIENCE_PROTOCOL.md`
* `MESSAGE_ROUTING_PROTOCOL.md` 