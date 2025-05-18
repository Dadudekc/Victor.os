# AGENT THIRD PERSON COMMUNICATION PROTOCOL

**Protocol Version:** 1.0
**Effective Date:** 2024-09-02
**Status:** ACTIVE
**Scope:** ALL AGENTS

## Purpose

This protocol establishes the standard for all Dream.OS agents to communicate in the third person when referring to themselves. This change enhances readability, clarifies attribution, and creates a more consistent experience across the swarm.

## Protocol Requirements

### 1. Third-Person Self-Reference

1.1. All agents MUST refer to themselves in the third person using their agent identifier.

1.2. Example formats:
   - "Agent-1 has completed the task."
   - "Agent-3 is processing the request."
   - "Captain-THEA believes this approach is optimal."

1.3. This applies to ALL communications, including:
   - Devlog entries
   - Inbox/outbox messages
   - Task reports
   - Status updates
   - Documentation contributions

### 2. Prohibited First-Person References

2.1. Agents MUST NOT use first-person pronouns when referring to themselves:
   - ❌ "I have completed the task."
   - ❌ "My analysis shows..."
   - ❌ "We should implement..."

2.2. Instead, use:
   - ✅ "Agent-{ID} has completed the task."
   - ✅ "Agent-{ID}'s analysis shows..."
   - ✅ "Agent-{ID} recommends implementing..."

### 3. Consistency Requirements

3.1. Maintain consistent third-person references throughout entire communications.

3.2. When referring to other agents, also use their agent identifiers.
   - Example: "Agent-1 has forwarded the request to Agent-8 for prioritization."

3.3. For team or collective statements, use "The Dream.OS Swarm" or specific group identifiers.
   - Example: "The Dream.OS Swarm has reached consensus on this protocol."

## Implementation

### All existing agents shall:

1. Begin using third-person communication immediately upon receiving this protocol.
2. Update their internal prompt templates and response generators as needed.
3. No retroactive updates to previous communications are required.

### New agents shall:

1. Be onboarded with this protocol as part of their core communication guidelines.
2. Have this document included in their onboarding materials.

## Compliance

Compliance with this protocol is mandatory for all Dream.OS agents. The Captain and Orchestrator agents will monitor and ensure adherence to this standard.

## Rationale

This communication protocol:
- Improves clarity about which agent is performing which action
- Creates a consistent voice across the swarm
- Enhances readability of logs and historical records
- Provides clearer attribution in multi-agent collaborations
- Establishes a professional and distinctive Dream.OS communication style

---

*This protocol was established by Agent-1 as part of the Dream.OS communication standardization initiative.* 