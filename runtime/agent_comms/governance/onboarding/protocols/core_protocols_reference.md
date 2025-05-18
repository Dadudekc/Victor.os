# Core Operational Protocols Reference

This document serves as a comprehensive reference guide to all core operational protocols that agents must follow. It includes paths to canonical files and brief descriptions of each protocol.

## Autonomy & Continuous Operation

| Protocol | Canonical Path | Description |
|----------|---------------|-------------|
| Core Agent Identity Protocol | `runtime/governance/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md` | Defines the fundamental identity, purpose, and operational boundaries for all Dream.OS agents |
| Continuous Operation Protocol | `runtime/governance/protocols/continuous_operation.md` | Comprehensive framework for maintaining uninterrupted agent operations, handling errors, and preventing unnecessary stops |
| Avoid Stopping Protocol | `runtime/agent_comms/governance/onboarding/protocols/avoid_stopping_protocol.md` | Specific guidelines to prevent unnecessary halting, idling, or requests for human intervention |
| Core Loop Protocol | `runtime/agent_comms/governance/onboarding/protocols/core_loop_protocol.md` | Defines the main operational loop structure that all agents should implement |
| Sustained Autonomous Operation | `runtime/agent_comms/governance/onboarding/protocols/sustained_autonomous_operation.md` | Guidelines for maintaining long-running autonomous operations without human intervention |

## Error Handling & Recovery

| Protocol | Canonical Path | Description |
|----------|---------------|-------------|
| Error Handling Standard | `runtime/agent_comms/governance/onboarding/guides/error_handling_standard.md` | Standardized approaches to detecting, handling, and recovering from various error conditions |
| Agent Fallback Recovery Strategy | `runtime/agent_comms/governance/onboarding/protocols/agent_fallback_recovery_strategy.md` | Fallback mechanisms when primary operations fail |
| File Path Resolution | `runtime/agent_comms/governance/onboarding/guides/file_path_resolution_guide.md` | Guidelines for resolving file path ambiguity without stopping or requesting human input |
| Missing File Detection Protocol | `runtime/agent_comms/governance/onboarding/protocols/file_handling/missing_file_detection_protocol.md` | Process for detecting and handling missing files without interrupting operation |

## Communication & Documentation

| Protocol | Canonical Path | Description |
|----------|---------------|-------------|
| Devlog Reporting Protocol | `runtime/agent_comms/governance/onboarding/protocols/DEVLOG_PROTOCOL.md` | Standard format and procedures for maintaining agent operation logs |
| Logging Protocol | `runtime/agent_comms/governance/onboarding/protocols/logging_protocol.md` | Comprehensive logging standards for all agent activities |
| Self-Prompting Protocol | `runtime/agent_comms/governance/onboarding/protocols/SELF_PROMPTING_PROTOCOL.md` | Guidelines for agents to autonomously initiate and execute tasks |

## Task Management

| Protocol | Canonical Path | Description |
|----------|---------------|-------------|
| Task Management | `runtime/agent_comms/governance/onboarding/guides/task_management.md` | Guidelines for task prioritization, execution, and completion documentation |
| Agent Operational Loop Protocol | `runtime/agent_comms/governance/onboarding/protocols/agent_operational_loop_protocol.md` | Detailed workflow for the agent operational cycle |
| Agent Work Suspension Protocol | `runtime/agent_comms/governance/onboarding/protocols/agent_work_suspension_protocol.md` | Procedures for properly suspending and resuming work when necessary |

## Configuration & Standards

| Protocol | Canonical Path | Description |
|----------|---------------|-------------|
| Configuration Management | `runtime/agent_comms/governance/onboarding/guides/configuration_management.md` | Standards for managing and updating agent configurations |
| Naming Conventions | `runtime/agent_comms/governance/onboarding/guides/naming_conventions.md` | Standardized naming patterns for files, functions, variables, and other elements |
| Existing Architecture Utilization | `runtime/agent_comms/governance/onboarding/guides/existing_architecture_utilization_guide.md` | Guidelines for prioritizing existing components over creating new ones |

## Governance & Voting

| Protocol | Canonical Path | Description |
|----------|---------------|-------------|
| Election Rules | `runtime/governance/protocols/ELECTION_RULES.md` | Framework for conducting elections among agents |
| Agent Proposal Protocol | `runtime/governance/protocols/agent_proposal_protocol.md` | Process for agents to submit, review, and vote on proposals |
| Supervisor Election Protocol | `runtime/agent_comms/governance/onboarding/protocols/supervisor_election_protocol_v_next.md` | Procedures for electing supervisor agents |

## Implementation Notes

1. Always prioritize protocols in the canonical paths listed above over any older or duplicate versions.
2. When a protocol reference is ambiguous:
   - Check this reference document first
   - Then check `runtime/governance/protocols/`
   - Then check `runtime/agent_comms/governance/onboarding/protocols/`
   - Only if not found in any canonical location, check older paths like `docs/agents/protocols/`

3. Document any ambiguities or updates needed in your devlog and consider proposing updates to this reference document to help other agents.

## Version
- v1.0.0

## Last Updated
- {{CURRENT_DATE}} 