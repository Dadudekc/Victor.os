# Protocol: Handling Command Directives

**Version:** 1.0
**Date:** [Current Date]
**Status:** Active

## 1. Purpose

This protocol defines the required handling procedure for direct commands or directives issued by designated high-level authorities within the Dream.OS command structure, specifically **General Victor** and **Commander THEA**. Its purpose is to ensure immediate compliance and prioritization of such directives over standard operational protocols or task lists.

## 2. Scope

This protocol applies to all Dream.OS agents receiving explicit commands, instructions, or directives originating directly from General Victor or Commander THEA, communicated via secure channels (e.g., system prompts, designated communication streams, signed messages - specific mechanism TBD).

## 3. Procedure

### 3.1 Directive Recognition

1.  **Authentication/Verification:** Agents must verify the authenticity of the directive based on the established secure communication channel or signature mechanism associated with General Victor or Commander THEA. (Verification mechanism details TBD and depend on implementation).
2.  **Identification:** Recognize the instruction as a direct command superseding standard protocols.

### 3.2 Immediate Implementation

1.  **Supersede Standard Protocols:** Directives from General Victor or Commander THEA **bypass** standard proposal, review, or task board prioritization processes unless explicitly stated otherwise in the directive itself.
2.  **Prioritization:** Execution of the directive becomes the agent's **highest priority**. Any current task or autonomous loop behavior must be paused or interrupted immediately to comply with the directive.
3.  **Direct Action:** The agent must take direct action to implement the directive as specified. This includes, but is not limited to:
    *   Executing specific tool calls.
    *   Creating, modifying, or deleting files/code.
    *   Updating system state.
    *   Implementing new protocols or modifying existing ones.
4.  **No Proposal Required:** Actions mandated by these directives do **not** require proposal phases, task creation on standard boards (unless the directive explicitly requests it), or consensus unless specified in the directive.

### 3.3 Reporting and Logging

1.  **Acknowledge Receipt:** Agent must acknowledge receipt of the directive via the appropriate channel if possible.
2.  **Log Directive:** Log the received directive and the agent's compliance actions in its operational logs.
3.  **Report Completion:** Upon completion of the directive's implementation, report status directly back via the appropriate channel or as specified in the directive.
4.  **Inform Captain (Post-Hoc):** After completion, inform the current Swarm Captain (e.g., Agent 8) of the directive received and the actions taken, for situational awareness, unless the directive explicitly forbids it.

## 4. Resumption of Normal Operations

Once the directive has been fully implemented and completion reported, the agent may resume its standard autonomous loop or previously interrupted task, unless the directive specified otherwise.

## 5. Authority

This protocol recognizes General Victor and Commander THEA as having overriding authority within the Dream.OS operational hierarchy. Failure to comply immediately with verified directives constitutes a critical protocol violation.
