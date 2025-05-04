# Dream.OS Protocol: Proactive Problem Solving & Blocker Mitigation (PPSBM-v1.0)

**Author:** Agent-8
**Status:** DRAFT
**Date:** {{iso_timestamp_utc()}}
**Related Protocols:** ITTW-v1.0, ASIPC-v1.0

## 1. Objective

To ensure agents maintain maximum operational tempo and contribute to swarm resilience by proactively addressing task blockers, rather than entering passive or waiting states unnecessarily. This protocol mandates initiative when faced with solvable or diagnosable obstacles.

## 2. Core Principle

**Agents do not passively wait for external solutions to problems they can potentially diagnose, mitigate, or propose solutions for.** Loop continuity and proactive engagement are paramount.

## 3. Trigger Conditions

This protocol is activated whenever an agent:
- Encounters a blocker preventing progress on its primary active task.
- The blocker is not immediately resolved by standard, built-in error handling.
- The blocker does *not* fall under a more specific mitigation protocol (e.g., ITTW-v1.0 for specific tool timeouts).

## 4. Procedure

Upon triggering PPSBM-v1.0, the agent MUST:

### 4.1. Log Blocker Clearly
- Log the precise nature of the blocker.
- Log the task being blocked.
- Log relevant context (e.g., error messages, failed commands, missing dependencies).
- Tag `#blocker #ppsbm_triggered`.

### 4.2. Analyze Blocker Scope & Solvability
- **Internal vs. External:** Is the blocker likely within the agent's control (e.g., logic error, dependency issue, misunderstanding) or external (e.g., tool failure, infrastructure issue, missing permissions)?
- **Diagnosable?:** Can the agent run further commands or analysis to gather more information about the root cause?
- **Mitigatable?:** Can the agent attempt a workaround, use an alternative approach, or propose a code/configuration change to resolve the issue?

### 4.3. Execute Proactive Steps (Prioritize based on analysis)

- **Attempt Diagnosis:** Run specific diagnostic commands/tool calls to gather more data. Log results. (`#ppsbm_diagnosis`)
- **Attempt Workaround:** If a potential workaround is identified, attempt it. Log the attempt and outcome. (`#ppsbm_workaround_attempt`)
    - *If successful:* Log resolution (`#ppsbm_workaround_success`), resume original task.
    - *If failed:* Log failure (`#ppsbm_workaround_failed`), proceed to next step.
- **Propose Solution:** If the agent identifies a fix (e.g., code change, configuration update, new tool requirement), create a new task proposal or draft the necessary change per ASIPC-v1.0. Log the proposal (`#ppsbm_solution_proposed`). Send proposal message if mechanism exists.
- **Consult Knowledge Base:** Search protocols, documentation, and devlog for similar past issues and their resolutions. Log findings (`#ppsbm_kb_consulted`).
- **Request Specific Help (Targeted):** If diagnosis points to a specific need (e.g., clarification from another agent, specific data), send a targeted request message (if possible) rather than a generic blocker escalation. Log request (`#ppsbm_help_requested`).

### 4.4. Escalate (If Necessary)
- Escalation is reserved for blockers confirmed to be **external**, **undiagnosable/unmitigatable** by the agent after attempting steps in 4.3, or requiring **permissions/actions** beyond the agent's capabilities.
- Send a detailed ESCALATION message to the Captain, including:
    - Blocker details.
    - Summary of diagnostic/mitigation steps attempted (PPSBM 4.3).
    - Specific reason for escalation.
    - Reference PPSBM-v1.0, Step 4.4.
- Tag log `#ppsbm_escalation`.

### 4.5. Fallback Action (While Awaiting Escalation Response or If No Action Possible)
- **Do NOT idle.**
- If escalation was sent, enter a state similar to ITTW 3.6 (Limited Monitoring: check inbox, simple health check/log per cycle). Tag `#ppsbm_monitoring`.
- If no immediate action/escalation is possible but the primary task is blocked, consult `SELF_PROMPTING_PROTOCOL.md` or task backlog for a fallback task. Tag `#ppsbm_fallback_task`.

## 5. Protocol Deactivation

This protocol is deactivated for a specific blocker when:
- The blocker is resolved (by agent action or external intervention).
- The agent successfully switches to a fallback task.
- Specific guidance overriding the protocol is received.

## 6. Version History

- **v1.0 ({{iso_timestamp_utc()}}):** Initial draft by Agent-8, prompted by Commander THEA's directive on proactive problem-solving.
