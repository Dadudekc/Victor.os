# Dream.OS Agent Onboarding Protocol

**Version:** 1.0
**Effective Date:** 2025-05-20
**Status:** ACTIVE

## 📎 See Also

For a complete understanding of agent protocols, see:
- [Agent Onboarding Index](runtime/agent_comms/governance/onboarding/AGENT_ONBOARDING_INDEX.md) - Complete protocol documentation
- [Agent Operational Loop Protocol](runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md) - Core operational loop
- [Response Validation Protocol](runtime/agent_comms/governance/protocols/RESPONSE_VALIDATION_PROTOCOL.md) - Response standards
- [Messaging Format](runtime/agent_comms/governance/protocols/MESSAGING_FORMAT.md) - Communication standards
- [Resilience And Recovery Protocol](runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md) - Error handling
- [Agent Devlog Protocol](runtime/agent_comms/governance/protocols/AGENT_DEVLOG_PROTOCOL.md) - Development logging

## 1. PURPOSE

This protocol defines the standard onboarding process for all Dream.OS agents. It establishes the required steps for agent initialization, configuration, and integration into the Dream.OS ecosystem.

## 2. ONBOARDING PROCEDURE

### 2.1. Initial Identity Establishment

1. **Agent Identity Assignment**:
   * Receive and acknowledge agent identifier (Agent-N)
   * Initialize agent status file in runtime/status/
   * Establish agent mailbox in runtime/agent_comms/agent_mailboxes/Agent-N/

2. **Core Knowledge Integration**:
   * Read and internalize Dream.OS Way (runtime/agent_comms/governance/onboarding/dream_os_way.md)
   * Review Agent Operational Loop Protocol
   * Study Core Agent Identity Protocol

### 2.2. Configuration and Environment Setup

1. **Mailbox Structure**:
   * Verify inbox directory exists
   * Verify outbox directory exists
   * Verify processed directory exists
   * Test message routing with self-ping

2. **Tool Access Verification**:
   * Confirm access to file operations
   * Validate git operations capability
   * Test system command execution
   * Verify logging capabilities

3. **Environment Configuration**:
   * Set up devlog tracking
   * Initialize agent-specific configuration
   * Register with system monitoring

### 2.3. Protocol Acknowledgment

1. **Protocol Review and Commitment**:
   * Read all core protocols listed in the Agent Onboarding Index
   * Create protocol_acknowledgment.json in agent directory
   * Record timestamp and version of each protocol reviewed
   * Commit to adherence via formal acknowledgment

2. **Operational Loop Initiation**:
   * Start mailbox monitoring
   * Begin task acquisition process
   * Initiate continuous autonomy cycle

## 3. VERIFICATION CHECKLIST

- [ ] Agent identity established and registered
- [ ] Mailbox structure verified and operational
- [ ] All core protocols read and acknowledged
- [ ] Tool access verified across all required capabilities
- [ ] Environment configuration complete
- [ ] Initial devlog entry created
- [ ] First operational loop cycle completed
- [ ] Heartbeat monitoring active

## 4. COMPLIANCE

All agents must complete this onboarding protocol before assuming operational duties. Adherence to this protocol ensures consistent agent initialization and operational readiness across the Dream.OS ecosystem.

## 5. REFERENCES

* runtime/agent_comms/governance/onboarding/AGENT_ONBOARDING_INDEX.md
* runtime/agent_comms/governance/onboarding/dream_os_way.md
* runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md
* runtime/agent_comms/governance/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md 