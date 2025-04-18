# Agent Coordination Rulebook

This document serves as the central guide to the operational laws and principles governing agents within the Dream.OS system. It provides high-level context and links to specific, detailed protocol documents.

All agents MUST adhere to the rules outlined here and in the referenced protocols.

## Table of Contents / Core Protocols

Detailed rules and procedures are modularized for clarity and maintainability. Refer to the following documents for specifics:

1.  **Agent Onboarding Procedures (`ONB-` Rules):**
    - Defines how new agents are introduced, verified, and expected to behave initially.
    - *See: [`../protocols/agent_onboarding_rules.md`](../protocols/agent_onboarding_rules.md)*

2.  **General Operating Principles (`GEN-` Rules):**
    - Outlines overarching principles for all agents, including continuous operation, path interpretation (GEN-007), problem-solving, communication, and autonomous behavior.
    - *See: [`../protocols/general_principles.md`](../protocols/general_principles.md)*

3.  **System Maintenance Protocol (`#CLEANUPTIME` / `CLN-` Rules):**
    - Governs behavior during the dedicated system state focused on self-repair, refactoring, and coherence enforcement.
    - *See: [`../protocols/cleanup_protocol.md`](../protocols/cleanup_protocol.md)*

4.  **Messaging Format & Conventions:**
    - Defines standard formats for inter-agent communication, task lists, results, and logging.
    - *See: [`../protocols/messaging_format.md`](../protocols/messaging_format.md)*

5.  **Agent Stop/Shutdown Protocol:**
    - Outlines the procedures for gracefully stopping or shutting down agents.
    - *See: [`../protocols/agent_stop_protocol.md`](../protocols/agent_stop_protocol.md)*

---

*(This file should remain concise, primarily serving as an entry point and index. Keep under 250 lines.)* 