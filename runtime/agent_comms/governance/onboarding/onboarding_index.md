# Dream.OS Agent Onboarding Index

This document serves as a central index of critical files for agent onboarding and operation within the Dream.OS ecosystem.

## Core Identity Documents

| Document | Path | Purpose |
|----------|------|---------|
| Dream.OS Way | `runtime/agent_comms/governance/onboarding/dream_os_way.md` | Core philosophical guide that defines agent identity, responsibilities, and approach to problem-solving |
| Agent Onboarding Template | `runtime/agent_comms/governance/onboarding/agent_onboarding_template.md` | Main onboarding template for new agents with communication protocols and operational requirements |

## Essential Protocols

| Protocol | Path | Purpose |
|----------|------|---------|
| Core Agent Identity Protocol | `runtime/governance/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md` | Defines the core identity and operational boundaries of all agents |
| Avoid Stopping Protocol | `runtime/agent_comms/governance/onboarding/protocols/avoid_stopping_protocol.md` | Detailed protocol for ensuring continuous operation without unnecessary stops |
| Continuous Operation | `runtime/governance/protocols/continuous_operation.md` | Comprehensive guide to maintaining autonomous operation |
| Core Loop Protocol | `runtime/agent_comms/governance/onboarding/protocols/core_loop_protocol.md` | Defines the main operational loop structure for agents |
| Core Protocols Reference | `runtime/agent_comms/governance/onboarding/protocols/core_protocols_reference.md` | Comprehensive reference to all core operational protocols with canonical paths |
| File Operation Failure Protocol | `runtime/agent_comms/governance/onboarding/protocols/file_handling/file_operation_failure_protocol.md` | Systematic approach for handling file operation failures without stopping |

## Operational Guides

| Guide | Path | Purpose |
|-------|------|---------|
| Existing Architecture Utilization Guide | `runtime/agent_comms/governance/onboarding/guides/existing_architecture_utilization_guide.md` | Reference for utilizing existing components and preventing duplication |
| File Path Resolution Guide | `runtime/agent_comms/governance/onboarding/guides/file_path_resolution_guide.md` | Methodology for resolving file path ambiguity without stopping |

## Templates and Configurations

| File | Path | Purpose |
|------|------|---------|
| Directive Competitive Autonomy Template | `runtime/agent_comms/governance/onboarding/contracts_and_configs/directive_competitive_autonomy_template.json` | Template for competitive autonomous operation directives |
| Directive Resume Autonomy Template | `runtime/agent_comms/governance/onboarding/contracts_and_configs/directive_resume_autonomy_template.json` | Template for resuming autonomous operation |

## Directory Structure

The onboarding materials are organized into the following structure:

```
runtime/agent_comms/governance/onboarding/
├── protocols/       # Core operational protocols
├── guides/          # Usage guides and best practices
├── contracts_and_configs/ # Configuration files and templates
├── prompts/         # Prompt templates 
├── info/            # General information documents
└── (root)           # Primary onboarding documents
```

## Onboarding Workflow

For a new agent, the recommended onboarding sequence is:

1. Read `dream_os_way.md` to understand the core philosophy
2. Review `agent_onboarding_template.md` for operational requirements
3. Study `runtime/governance/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`
4. Familiarize with essential protocols:
   - `avoid_stopping_protocol.md`
   - `core_loop_protocol.md`
   - `continuous_operation.md`
5. Reference operational guides as needed:
   - `existing_architecture_utilization_guide.md`
   - `file_path_resolution_guide.md`

## Important Notes

* Always prioritize documents in `runtime/governance/` over older paths like `docs/agents/protocols/from_old_docs/`
* When faced with ambiguity about file locations or content, follow the principles in `file_path_resolution_guide.md`
* Never stop to ask for clarification about documentation - make informed decisions and proceed based on available information 