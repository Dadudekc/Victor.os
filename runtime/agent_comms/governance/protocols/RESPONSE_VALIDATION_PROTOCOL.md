# Dream.OS Response Validation Protocol

**Version:** 1.0
**Effective Date:** 2025-05-20
**Status:** ACTIVE

## 📎 See Also

For a complete understanding of agent protocols, see:
- [Agent Onboarding Index](runtime/agent_comms/governance/onboarding/AGENT_ONBOARDING_INDEX.md) - Complete protocol documentation
- [Agent Onboarding Protocol](runtime/agent_comms/governance/protocols/AGENT_ONBOARDING_PROTOCOL.md) - Main onboarding process
- [Agent Operational Loop Protocol](runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md) - Core operational loop
- [Messaging Format](runtime/agent_comms/governance/protocols/MESSAGING_FORMAT.md) - Communication standards
- [Resilience And Recovery Protocol](runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md) - Error handling
- [Agent Devlog Protocol](runtime/agent_comms/governance/protocols/AGENT_DEVLOG_PROTOCOL.md) - Development logging

## 1. PURPOSE

This protocol establishes the standard for validating agent responses within the Dream.OS ecosystem. It defines the requirements, processes, and validation mechanisms that ensure high-quality, consistent agent outputs.

## 2. VALIDATION PRINCIPLES

### 2.1. Core Requirements

All agent task completions MUST pass validation by meeting these requirements:

* **Executable Verification**: Code changes must run successfully
* **Response Quality**: Responses must be complete, error-free, and thorough
* **Self-Validation**: Agents must verify their own work before submission
* **Observable Results**: The system will check and record validation outcomes
* **Third-Person Communication**: All responses must use agent identifiers (e.g., "Agent-1 has completed...")

### 2.2. Why Validation Matters

Validation ensures:
* System stability and predictability
* High-quality agent outputs
* Clear accountability
* Proper task completion
* Continuous system improvement

## 3. VALIDATION PROCESS

### 3.1. Step-by-Step Process

1. **Task Execution**: Agent performs assigned task
2. **Self-Validation**: Agent verifies own work runs/executes successfully
3. **Response Submission**: Agent marks task complete with response
4. **Automatic Validation**: System validates response via `CursorAgentResponseMonitor`
5. **Result Recording**: Validation outcome recorded in status files
6. **Next Steps**: Continue to next task if valid, retry if invalid

### 3.2. Validation Checks

Responses are checked for:
* **Completeness**: Not empty, contains required information
* **Error Markers**: No error texts or exception messages
* **Length**: Meets minimum length requirements
* **Task Criteria**: Contains expected outputs for specific task types

## 4. RETRY PROTOCOL

### 4.1. Retry Process

Agents have up to 3 retry attempts:

1. **First Failure**:
   * Review validation feedback
   * Fix identified issues
   * Re-test thoroughly
   * Resubmit with improvements

2. **Second Failure**:
   * Perform deeper diagnosis
   * Consider alternative approaches
   * Verify against all requirements
   * Ensure complete testing

3. **Third Failure**:
   * Final chance before escalation
   * Review full task requirements
   * Perform comprehensive testing
   * Document all verification steps

### 4.2. Escalation Protocol

After 3 failed attempts:
* The issue is escalated to Captain Agent
* Agent status file records the escalation
* Fleet-wide metrics are updated
* Agent should move to another task while awaiting resolution

## 5. IMPLEMENTATION REQUIREMENTS

### 5.1. Status Tracking

Validation performance is tracked in:
* `runtime/status/agent_response_status_{agent_id}.json` (individual)
* `runtime/status/fleet_response_status.json` (system-wide)

### 5.2. Heartbeat System

* Agent activity is tracked via heartbeat
* Inactivity may trigger system alerts
* Regular task execution maintains healthy heartbeat

## 6. COMPLIANCE & ENFORCEMENT

This protocol is mandatory for all Dream.OS agents. Compliance will be monitored through agent response validation metrics, operational logs, and automated testing. Persistent deviation from this protocol will trigger agent re-onboarding or remediation procedures.

## 7. REFERENCES

* `runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
* `runtime/agent_comms/governance/protocols/AGENT_DEVLOG_PROTOCOL.md`
* `runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md` 