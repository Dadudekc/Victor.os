# Dream.OS Agent Operational Loop Protocol

**Version:** 2.0
**Effective Date:** 2025-05-20
**Status:** ACTIVE

## 📎 See Also

For a complete understanding of agent protocols, see:
- [Agent Onboarding Index](runtime/agent_comms/governance/onboarding/AGENT_ONBOARDING_INDEX.md) - Complete protocol documentation
- [Agent Onboarding Protocol](runtime/agent_comms/governance/protocols/AGENT_ONBOARDING_PROTOCOL.md) - Main onboarding process
- [Response Validation Protocol](runtime/agent_comms/governance/protocols/RESPONSE_VALIDATION_PROTOCOL.md) - Response standards
- [Messaging Format](runtime/agent_comms/governance/protocols/MESSAGING_FORMAT.md) - Communication standards
- [Resilience And Recovery Protocol](runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md) - Error handling
- [Agent Devlog Protocol](runtime/agent_comms/governance/protocols/AGENT_DEVLOG_PROTOCOL.md) - Development logging

## 1. PURPOSE

This protocol defines the standard, continuous operational loop for all Dream.OS agents. It dictates how agents manage their work, interact with the system, and maintain autonomy. Adherence to this loop is critical for swarm stability and productivity.

## 2. THE CONTINUOUS AUTONOMY LOOP

Agents operate in a persistent loop, designed to minimize idle time and maximize productive output. The loop priorities are:

**LOOP START / RE-ENTRY POINT**

### 2.1. Mailbox Check & Processing (Highest Priority)

1. **Access Your Inbox**:
   * Your primary inbox is located at: `runtime/agent_comms/agent_mailboxes/Agent-<n>/inbox/`
   * Messages are typically individual `.json` files.

2. **Process Each Message Systematically**:
   * Read message content and headers
   * Take appropriate action based on message type and content
   * Acknowledge directives
   * Update context based on information
   * Initiate tasks from directives

3. **Mailbox Hygiene**:
   * Archive processed messages to `runtime/agent_comms/agent_mailboxes/Agent-<n>/processed/`
   * Log processing of significant messages
   * Maintain clean inbox for actionable items

4. **Empty Inbox**: If inbox is empty, proceed to the next stage.

### 2.2. Current Task Management

1. **Review Active Task**:
   * Check your entry in `runtime/agent_data/working_tasks.json`
   * If active task exists:
     * Continue execution
     * Self-validate progress
     * Complete task if all sub-goals met
   * If no active task, proceed to Claim New Task

### 2.3. Claim New Task

1. **Access Task Pool**:
   * Consult the primary task list in `runtime/task_board/future_tasks.json`
   
2. **Select & Claim Task**:
   * Review available tasks based on priority and capabilities
   * Verify if existing functionality can be reused before building new
   * Claim appropriate task by updating status
   * Log claiming of new task
   * Initiate task execution

3. **No Claimable Tasks**: If no suitable tasks available, proceed to Proactive Task Generation.

### 2.4. Task Completion & Reporting

1. **Final Self-Validation**:
   * Ensure all objectives are met
   * Test code or configuration changes
   * Verify work is error-free and meets quality standards

2. **Devlog Final Report**: Create comprehensive entry for completed task

3. **Update Task Status**: Mark task as "COMPLETED" in system tracker

4. **Git Workflow**:
   * Commit changes after validation
   * Follow standard commit message guidelines
   * Only commit fully functional work

5. **Archive Task**: Move definition from `working_tasks.json` to `completed_tasks.json`

### 2.5. Proactive Task Generation

1. **Condition**: Enter this stage if inbox empty, no active task, and no suitable tasks to claim

2. **Analyze Project Documentation**:
   * Review completed episodes/epics
   * Identify gaps or logical next steps
   * Find potential improvements

3. **Generate New Tasks**:
   * Define valuable tasks for the swarm
   * Ensure clear objectives and estimated effort
   * Add to `future_tasks.json`
   * Log rationale for new tasks

4. **Default High-Value Activity**:
   * Review and improve documentation
   * Identify refactoring opportunities
   * Research techniques relevant to project

### 2.6. Loop Control & Drift Prevention

* **DO NOT HALT**: The loop is continuous
* **Cycle Count Reset**: Reset counters after any interruption
* **Report Status**: Log task changes, message processing, errors
* **Error Handling**: Do not get stuck on persistent failures

**RETURN TO LOOP START (Mailbox Check)**

## 3. SELF-VALIDATION PROTOCOL

* **Definition of Done**: Understand acceptance criteria
* **Test Your Output**: Verify code, configuration, documentation
* **Automatic Response Validation**: All responses validated by system
* **Iterate Until Correct**: Fix issues before marking complete

## 4. METRICS & MONITORING

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

## 5. ADHERENCE

This Operational Loop is not optional. It is the lifeblood of autonomous function within Dream.OS. Consistent adherence ensures productivity and contribution to swarm objectives. Deviations should be rare and justifiable, typically in response to high-priority directives. 