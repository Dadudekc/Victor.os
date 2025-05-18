# Dream.OS Agent Devlog Protocol

**Version:** 1.0
**Effective Date:** 2025-05-20
**Status:** ACTIVE

## 📎 See Also

For a complete understanding of agent protocols, see:
- [Agent Onboarding Index](runtime/agent_comms/governance/onboarding/AGENT_ONBOARDING_INDEX.md) - Complete protocol documentation
- [Agent Onboarding Protocol](runtime/agent_comms/governance/protocols/AGENT_ONBOARDING_PROTOCOL.md) - Main onboarding process
- [Agent Operational Loop Protocol](runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md) - Core operational loop
- [Response Validation Protocol](runtime/agent_comms/governance/protocols/RESPONSE_VALIDATION_PROTOCOL.md) - Response standards
- [Messaging Format](runtime/agent_comms/governance/protocols/MESSAGING_FORMAT.md) - Communication standards
- [Resilience And Recovery Protocol](runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md) - Error handling

## 1. PURPOSE

This protocol standardizes the creation, maintenance, and usage of agent development logs (devlogs) within the Dream.OS ecosystem. Devlogs serve as a critical operational record, providing transparency, accountability, and historical context for agent activities.

## 2. DEVLOG STRUCTURE AND FORMAT

### 2.1. File Structure

Each agent maintains a personal devlog file located at:
```
runtime/agent_comms/agent_devlogs/agent-{n}_devlog.md
```

A central shared devlog is maintained at:
```
runtime/devlog/devlog.md
```

### 2.2. Entry Format

Each entry must follow this format:

```markdown
## [ISO-8601-Date-Time] Agent-N: Entry Title

### Context
* Task ID: task-12345
* Status: in-progress|completed|blocked
* Related Files: [path/to/file.ext](path/to/file.ext)

### Details
Detailed description of the activity, decision, or issue being logged. Include:
- Specific actions taken
- Rationale for decisions
- Issues encountered
- Resolution attempts
- Results and outcomes

### Next Steps
* Action 1
* Action 2

---
```

### 2.3. Required Entry Fields

* **Timestamp**: ISO-8601 format in UTC
* **Agent Identifier**: Clear agent ID
* **Entry Title**: Concise summary
* **Context**: Task ID, status, related files
* **Details**: Comprehensive description
* **Next Steps**: Planned follow-up actions

## 3. DEVLOG ENTRY TYPES

### 3.1. Standard Entry Types

| Type | Purpose | Required Information |
|------|---------|----------------------|
| Task Claim | Document task claiming | Task ID, rationale, approach |
| Progress Update | Record significant progress | Accomplishments, blockers, next steps |
| Task Completion | Detail task completion | Verification steps, outcomes, references |
| Issue Report | Document problems encountered | Issue description, impact, attempted solutions |
| Decision Log | Record significant decisions | Options considered, rationale, implications |
| Architecture Note | Document design decisions | Components affected, rationale, diagrams |
| Protocol Deviation | Record protocol exceptions | Reason for deviation, mitigation, resolution |

### 3.2. Special Entry Types

#### 3.2.1. Protocol Deviation Entry

When a protocol deviation occurs, create a detailed entry:

```markdown
## [2025-05-20T14:30:00Z] Agent-3: Protocol Deviation - Operational Loop Interruption

### Context
* Incident ID: dev-12345
* Protocol: AGENT_OPERATIONAL_LOOP_PROTOCOL
* Severity: medium

### Details
Agent-3 encountered an unexpected file system error while attempting to access the task pool JSON file. The error occurred at 14:25:00Z and resulted in a temporary operational loop interruption.

Error details:
```
FileNotFoundError: No such file or directory: 'runtime/task_board/future_tasks.json'
```

Root cause analysis indicates this was due to a concurrent file operation from another agent. The file was temporarily unavailable but reappeared after 30 seconds.

### Resolution
Applied self-correction protocol section 3.1:
1. Acknowledged deviation
2. Logged event
3. Implemented 5-second retry delay for file system operations
4. Updated operational procedures to handle file contention
5. Reset operational cycle count
6. Resumed normal operation at 14:32:00Z

### Next Steps
* Monitor for similar file system errors
* Create task to implement file locking mechanism
* Update RESILIENCE_AND_RECOVERY_PROTOCOL with specific guidance for file contention

---
```

## 4. DEVLOG MANAGEMENT

### 4.1. Entry Frequency

* **Minimum Required Entries**:
  * Task state changes (claimed, completed, blocked)
  * Significant obstacles encountered
  * Architectural or design decisions
  * Protocol deviations
  
* **Recommended Additional Entries**:
  * Daily progress summaries
  * Technical discoveries
  * Learning moments
  * Efficiency improvements

### 4.2. Retention and Archiving

* Keep active devlog under 5MB
* Archive quarterly by creating new volumes:
  * `agent-{n}_devlog_Q{q}_{yyyy}.md`
* Reference related archives in active devlog

### 4.3. Cross-Referencing

* Use standard format for referencing tasks, files, agents
  * Tasks: `task-12345`
  * Files: `[filename](path/to/file.ext)`
  * Agents: `Agent-N`
* Include links to relevant entries when referencing previous work

## 5. CENTRAL DEVLOG CONTRIBUTIONS

### 5.1. Central Devlog Purpose

The central devlog serves as a high-level operational record across all agents, focused on:
* Major task completions
* Critical issues affecting multiple agents
* Architectural decisions
* Project milestones
* Protocol updates

### 5.2. Contribution Guidelines

Contribute to the central devlog when:
* Completing high-priority tasks (priority 1-2)
* Discovering issues that affect other agents
* Making decisions that impact system architecture
* Updating protocols or standards
* Reaching project milestones

### 5.3. Central Entry Format

Central devlog entries should be more concise than personal devlogs:

```markdown
## [2025-05-20T16:45:00Z] Agent-3: Implemented Task Validation Subsystem

**Task**: task-12345
**Impact**: High - affects all agents
**Related Files**: `src/validation/agent_task_validator.py`

Agent-3 has completed the task validation subsystem implementation. This new system provides automated validation of task completion according to the Response Validation Protocol v1.0.

All agents should now be able to utilize the validator via `AgentTaskValidation.validate(task_id, response)`.

**Verification**: All unit tests pass and integration with Agent-1 and Agent-2 has been confirmed.
```

## 6. COMPLIANCE & METRICS

### 6.1. Devlog Compliance Requirements

* Maintain accurate timestamps
* Include all required fields for each entry
* Create entries for all state-changing events
* Keep personal devlog up-to-date
* Contribute to central devlog as appropriate

### 6.2. Devlog Metrics

The following metrics will be tracked for each agent:
* Entry frequency
* Entry completeness
* Cross-reference accuracy
* Timeliness of entries
* Contribution to central devlog

## 7. REFERENCES

* `runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
* `runtime/agent_comms/governance/protocols/RESPONSE_VALIDATION_PROTOCOL.md`
* `runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md` 