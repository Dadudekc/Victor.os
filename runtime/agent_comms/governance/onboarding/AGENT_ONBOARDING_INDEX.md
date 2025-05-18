# Dream.OS Agent Onboarding Index

This document serves as a central index of critical files for agent onboarding and operation within the Dream.OS ecosystem.

## Core Protocol Documentation

| Protocol | Path | Purpose |
|----------|------|---------|
| Agent Onboarding Protocol | `runtime/agent_comms/governance/protocols/AGENT_ONBOARDING_PROTOCOL.md` | Defines the standard onboarding process for all Dream.OS agents |
| Agent Operational Loop Protocol | `runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md` | Specifies the core operational loop and execution cycle |
| Response Validation Protocol | `runtime/agent_comms/governance/protocols/RESPONSE_VALIDATION_PROTOCOL.md` | Standards for validating agent responses and handling failures |
| Messaging Format | `runtime/agent_comms/governance/protocols/MESSAGING_FORMAT.md` | Standardized messaging formats for agent communications |
| Resilience And Recovery Protocol | `runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md` | Procedures for handling failures and ensuring operational continuity |
| Agent Devlog Protocol | `runtime/agent_comms/governance/protocols/AGENT_DEVLOG_PROTOCOL.md` | Guidelines for creating and maintaining agent development logs |

## Core Identity Documents

| Document | Path | Purpose |
|----------|------|---------|
| Dream.OS Way | `runtime/agent_comms/governance/onboarding/dream_os_way.md` | Core philosophical guide that defines agent identity, responsibilities, and approach to problem-solving |
| Agent Onboarding Template | `runtime/agent_comms/governance/onboarding/agent_onboarding_template.md` | Main onboarding template for new agents with communication protocols and operational requirements |

## Operational Guides

| Guide | Path | Purpose |
|-------|------|---------|
| Existing Architecture Utilization Guide | `runtime/agent_comms/governance/onboarding/guides/existing_architecture_utilization_guide.md` | Reference for utilizing existing components and preventing duplication |
| File Path Resolution Guide | `runtime/agent_comms/governance/onboarding/guides/file_path_resolution_guide.md` | Methodology for resolving file path ambiguity without stopping |
| Agent Operational Guide | `runtime/agent_comms/governance/onboarding/agent_operational_guide_v1.md` | Comprehensive operational guidelines for day-to-day agent tasks |

## Templates and Configurations

| File | Path | Purpose |
|------|------|---------|
| Directive Competitive Autonomy Template | `runtime/agent_comms/governance/onboarding/contracts_and_configs/directive_competitive_autonomy_template.json` | Template for competitive autonomous operation directives |
| Directive Resume Autonomy Template | `runtime/agent_comms/governance/onboarding/contracts_and_configs/directive_resume_autonomy_template.json` | Template for resuming autonomous operation |

## Directory Structure

The onboarding materials are organized into the following structure:

```
runtime/agent_comms/governance/
├── protocols/       # Core operational protocols
├── onboarding/      # Onboarding materials
│   ├── guides/      # Usage guides and best practices
│   ├── protocols/   # Onboarding-specific protocols
│   ├── contracts_and_configs/ # Configuration files and templates
│   ├── prompts/     # Prompt templates
│   └── info/        # General information documents
└── reports/         # Operational reports and status updates
```

## Onboarding Workflow

For a new agent, the recommended onboarding sequence is:

1. Read `AGENT_ONBOARDING_PROTOCOL.md` for the overall onboarding process
2. Review `dream_os_way.md` to understand the core philosophy
3. Study `AGENT_OPERATIONAL_LOOP_PROTOCOL.md` for operational requirements
4. Familiarize with essential protocols:
   - `MESSAGING_FORMAT.md`
   - `RESPONSE_VALIDATION_PROTOCOL.md`
   - `RESILIENCE_AND_RECOVERY_PROTOCOL.md`
5. Set up devlog using `AGENT_DEVLOG_PROTOCOL.md`
6. Reference operational guides as needed:
   - `existing_architecture_utilization_guide.md`
   - `file_path_resolution_guide.md`

## Important Notes

* Always prioritize documents in `runtime/agent_comms/governance/` over older paths
* When faced with ambiguity about file locations or content, follow the principles in `file_path_resolution_guide.md`
* Never stop to ask for clarification about documentation - make informed decisions and proceed based on available information
* Keep all devlogs updated according to the Agent Devlog Protocol 