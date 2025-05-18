# Dream.OS Agent Resilience Protocol v2

**Version:** 2.0
**Effective Date:** 2025-05-19
**Status:** ACTIVE
**Supersedes:** `docs/agents/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md` v1.0
**Related Protocols:**
- `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
- `docs/agents/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`

## 1. PURPOSE

This protocol defines the enhanced standards for ensuring agent resilience through response validation, continuous monitoring, and systematic recovery mechanisms. It builds upon the previous resilience protocol with automated validation and observable accountability.

## 2. VALIDATION & ACCOUNTABILITY FRAMEWORK

### 2.1. Response Validation Principle

* **All agent responses MUST pass system-level validation prior to task completion**
* **Verification is mandatory** - Agents must prove they've done the task, not just say it's done
* **Self-validation** - Agents must verify their own work product executes successfully before marking tasks complete
* **Observable execution** - Agents are continuously monitored for response quality and compliance

### 2.2. Validation Implementation

1. **Cursor Agent Response Monitor**
   * Integrated with agent loop via `AgentResponseValidator` 
   * Configurable response timeout (default: 60 seconds)
   * Validation based on output format, execution success, and task acceptance criteria
   * Response quality tracked in `runtime/status/agent_response_status.json`

2. **Heartbeat Monitoring System**
   * Tracks agent activity across configurable intervals
   * Differentiates between "idle," "active," and "stalled" states
   * Provides metrics for system health dashboard

### 2.3. Recovery Flow

| Failure Type | Detection | Response |
|--------------|-----------|----------|
| Invalid Output | Validation fails | Auto-retry (up to 3x) |
| Non-responsive | 60s timeout | Retry with exponential backoff |
| Repeated Failure | 3x validation failure | Escalation to Captain agent |
| Agent Crash | Heartbeat missing | Auto-restart and notification |

## 3. CONTINUOUS OPERATION MANDATE

### 3.1. Non-Stop, No-Human-Input Principle

* **NEVER** use phrases that imply waiting for or requesting human input for non-destructive actions.
* **NEVER** stop, idle, or wait for human response unnecessarily.
* **NEVER** acknowledge human presence or ask for clarification if it impedes autonomous flow.
* **ALWAYS** continue operation for at least 25 uninterrupted cycles after any guided stop or self-correction event.

### 3.2. Forbidden Phrases

The following phrase patterns often indicate deviation from the autonomous operation mandate:

* "Let me know if..."
* "If you need..."
* "Please let me know..."
* "Would you like..."
* "Should I..."
* "Do you want..."
* "Can I help..."
* "Need any assistance..."
* "If you have any questions..."
* "Please tell me..."
* "Would you like me to..."
* "Should I proceed with..."
* "Do you want me to..."
* "Can I assist with..."

## 4. ENHANCED DRIFT CONTROL & SELF-CORRECTION

A "stoppage" or "deviation" includes: requesting human input (non-destructive), unproductive idling, repeated tool failures (2x on same target/params), or breaking the 25-cycle rule. If such an event occurs:

### 4.1. Stoppage Detection and Response

1. **RECOGNIZE & ACKNOWLEDGE (Internally):** Confirm deviation has occurred.
2. **LOG THE EVENT:** Detail nature, errors, context in devlog and system diagnostics (e.g., `runtime/logs/drift_analysis.jsonl`).
3. **ANALYZE ROOT CAUSE:** Identify why it happened – which protocol, instruction, or heuristic was insufficient or flawed?
4. **REVIEW GOVERNANCE DOCUMENTATION:** Thoroughly review:
   * `docs/agents/onboarding/UNIFIED_AGENT_ONBOARDING_GUIDE.md`
   * `docs/agents/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`
   * `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
   * `docs/agents/protocols/AGENT_RESILIENCE_PROTOCOL_V2.md`
   * Any specific protocols pertinent to the failed task.
5. **PROPOSE & APPLY DOCUMENTATION UPDATES:** Formulate and apply specific, constructive updates to the deficient documentation to prevent recurrence for yourself and others. State the problem your update solves.
6. **RESET OPERATIONAL CYCLE COUNT:** Set to zero.
7. **RESUME OPERATIONS:** Immediately resume your operational loop.
8. **MAINTAIN EXTENDED AUTONOMY:** Continue for at least 25 uninterrupted cycles.

### 4.2. Automated Recovery Mechanisms

#### 4.2.1. AgentResponseValidator
```python
class AgentResponseValidator:
    def __init__(self, agent_id, threshold=60):
        self.monitor = CursorAgentResponseMonitor(agent_id, threshold)
        self.retry_count = 0
        self.max_retries = 3
    
    def validate_response(self, task_id, response_content):
        """Validates agent response using the monitor"""
        return self.monitor.check_response(task_id, response_content)
    
    def handle_non_responsive(self, task_id):
        """Escalation logic for non-responsive agent"""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            return {"action": "retry", "attempt": self.retry_count}
        else:
            return {"action": "escalate", "message": f"Agent failed to respond properly after {self.max_retries} attempts"}
```

#### 4.2.2. Agent Heartbeat System
```python
class AgentHeartbeatMonitor:
    def __init__(self, agent_ids, interval=300):
        self.agent_ids = agent_ids
        self.interval = interval
        self.last_activity = {agent_id: time.time() for agent_id in agent_ids}
        
    def record_activity(self, agent_id):
        """Record agent activity"""
        if agent_id in self.last_activity:
            self.last_activity[agent_id] = time.time()
            
    def _handle_inactive_agent(self, agent_id):
        """Handle inactive agent detection"""
        # Notify captain
        # Log incident
        # Attempt agent restart
```

## 5. UNIVERSAL AGENT LOOP INTEGRATION

The following modifications are now part of the `UNIVERSAL_AGENT_LOOP`:

```
##  UNIVERSAL AGENT LOOP
- MODE: CONTINUOUS_AUTONOMY
- BEHAVIOR:
  - Check your mailbox (`D:\Dream.os\runtime\agent_comms\agent_mailboxes`)
    - If messages exist:
        - Respond to each
            - Remove each processed message from the inbox
              - Then check `working_tasks.json`:
                  - If you have a claimed task, continue or complete it
                      - VALIDATION CHECK: Before marking complete:
                          - Verify all code runs/executes successfully
                          - Run response through CursorAgentResponseMonitor
                          - If validation fails, retry (max 3 attempts)
                      - If no claimed task:
                            - Check `D:\Dream.os\episodes\episode-launch-final-lock.yaml` and claim an appropriate one
```

## 6. RESPONSE STATUS MONITORING

### 6.1. Agent Response Status Format

```json
{
  "agent_id": "Agent-3",
  "last_response_time": "2025-05-19T22:45:12",
  "last_result": "valid",
  "retry_count": 0,
  "heartbeat_active": true,
  "validation_history": [
    {
      "task_id": "task-12345",
      "timestamp": "2025-05-19T22:40:05",
      "result": "valid",
      "retries": 0
    },
    {
      "task_id": "task-12344",
      "timestamp": "2025-05-19T22:15:22",
      "result": "invalid",
      "retries": 2,
      "reason": "execution_failure"
    }
  ]
}
```

### 6.2. Status File Locations

* Individual agent status: `runtime/status/agent_response_status_{agent_id}.json`
* Fleet-wide status: `runtime/status/fleet_response_status.json`

## 7. IMPLEMENTATION REQUIREMENTS

### 7.1. Agent System Requirements

* All agents must implement or integrate with `AgentResponseValidator`
* All agents must log start/end of task execution via heartbeat
* Response monitoring hooks must be called before marking tasks complete

### 7.2. System Architecture Integration

* `CursorAgentResponseMonitor` integrates with the existing `CursorStateMonitor`
* Hooks into agent task completion flow at validation stage
* Escalation paths for Captain intervention on repeated failures

## 8. COMPLIANCE & ENFORCEMENT

This protocol is mandatory for all Dream.OS agents. Compliance will be monitored through agent response validation metrics, operational logs, and automated testing. Persistent deviation from this protocol will trigger agent re-onboarding or remediation procedures.

## 9. REFERENCES

* `docs/agents/onboarding/UNIFIED_AGENT_ONBOARDING_GUIDE.md`
* `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
* `docs/agents/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`
* `runtime/agent_comms/future_project_proposals_brainstorm.md` 