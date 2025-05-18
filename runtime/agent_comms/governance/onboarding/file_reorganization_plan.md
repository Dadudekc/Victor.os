# File Reorganization Plan for Agent Onboarding

This document outlines a plan to reorganize and merge the provided files into the `runtime/agent_comms/governance/onboarding/` structure.

## Target Directory Structure

```
runtime/agent_comms/governance/onboarding/
├── protocols/       # Core operational protocols
├── guides/          # Usage guides and best practices
├── contracts_and_configs/ # Configuration files and templates
├── prompts/         # Prompt templates
├── info/            # General information documents
└── (root)           # Primary onboarding documents
```

## File Categorization and Migration Plan

### 1. Core Identity & Onboarding Documents (Root Directory)

| Source File | Target Location | Action | Priority |
|-------------|----------------|--------|----------|
| `runtime/governance/onboarding/AGENT_ONBOARDING_TEMPLATE.md` | `runtime/agent_comms/governance/onboarding/agent_onboarding_template.md` | Copy | High |
| `runtime/governance/onboarding/DREAM_OS_WAY.md` | `runtime/agent_comms/governance/onboarding/dream_os_way.md` | Copy | High |
| `docs/agents/AGENT_ONBOARDING_CHECKLIST.md` | `runtime/agent_comms/governance/onboarding/agent_onboarding_checklist.md` | Copy | High |

### 2. Core Protocols

| Source File | Target Location | Action | Priority |
|-------------|----------------|--------|----------|
| `runtime/governance/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md` | `runtime/agent_comms/governance/onboarding/protocols/core_agent_identity_protocol.md` | Reference | High |
| `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md` | `runtime/agent_comms/governance/onboarding/protocols/agent_operational_loop_protocol.md` | Copy if not duplicating `core_loop_protocol.md` | Medium |
| `docs/agents/AGENT_WORK_SUSPENSION_AND_RESUMPTION_PROTOCOL.md` | `runtime/agent_comms/governance/onboarding/protocols/agent_work_suspension_protocol.md` | Copy | Medium |
| `runtime/governance/protocols/continuous_operation.md` | `runtime/agent_comms/governance/onboarding/protocols/continuous_operation.md` | Reference | High |
| `docs/agents/CONTINUOUS_OPERATION_AND_RESILIENCE_PROTOCOL.md` | `runtime/agent_comms/governance/onboarding/protocols/continuous_operation_legacy.md` | Archive | Low |
| `docs/agents/protocols/from_old_docs/protocols/agent_fallback_recovery_strategy.md` | `runtime/agent_comms/governance/onboarding/protocols/agent_fallback_recovery_strategy.md` | Copy if unique | Low |
| `docs/agents/protocols/from_old_docs/protocols/enhanced_agent_resilience_protocol_v1.md` | `runtime/agent_comms/governance/onboarding/protocols/enhanced_agent_resilience_legacy.md` | Archive | Low |
| `docs/agents/protocols/from_old_docs/protocols/idle_protocol_v1.md` | Omit | Superseded by `avoid_stopping_protocol.md` | Low |
| `docs/agents/protocols/from_old_docs/protocols/missing_file_detection_protocol.md` | `runtime/agent_comms/governance/onboarding/protocols/file_handling/missing_file_detection_protocol.md` | Copy if unique | Medium |

### 3. Standards & Guides

| Source File | Target Location | Action | Priority |
|-------------|----------------|--------|----------|
| `docs/agents/EXISTING_ARCHITECTURE_UTILIZATION_GUIDE.md` | `runtime/agent_comms/governance/onboarding/guides/existing_architecture_utilization_guide.md` | Copy | High |
| `docs/agents/protocols/configuration_management.md` | `runtime/agent_comms/governance/onboarding/guides/configuration_management.md` | Copy | Medium |
| `docs/agents/protocols/devlog_reporting_standard.md` | `runtime/agent_comms/governance/onboarding/protocols/devlog_reporting_standard.md` | Copy if not duplicating existing DEVLOG_PROTOCOL.md | Medium |
| `docs/agents/protocols/error_handling_standard.md` | `runtime/agent_comms/governance/onboarding/guides/error_handling_standard.md` | Copy | Medium |
| `docs/agents/protocols/naming_conventions.md` | `runtime/agent_comms/governance/onboarding/guides/naming_conventions.md` | Copy | Medium |
| `docs/agents/protocols/task_management.md` | `runtime/agent_comms/governance/onboarding/guides/task_management.md` | Copy | Medium |
| `runtime/agent_comms/thea_output_analysis.md` | `runtime/agent_comms/governance/onboarding/guides/thea_output_analysis.md` | Move | Medium |

### 4. Configuration Files & Templates

| Source File | Target Location | Action | Priority |
|-------------|----------------|--------|----------|
| `docs/agents/protocols/protocol_onboard_and_respond.yaml` | `runtime/agent_comms/governance/onboarding/contracts_and_configs/protocol_onboard_and_respond.yaml` | Copy | Medium |
| `runtime/agent_comms/directive_competitive_autonomy_v3_safe_template.json` | `runtime/agent_comms/governance/onboarding/contracts_and_configs/directive_competitive_autonomy_template.json` | Move | High |
| `runtime/agent_comms/directive_resume_autonomy_template.json` | `runtime/agent_comms/governance/onboarding/contracts_and_configs/directive_resume_autonomy_template.json` | Move | High |
| `runtime/agent_comms/onboarding_manifest.jsonl` | `runtime/agent_comms/governance/onboarding/contracts_and_configs/onboarding_manifest.jsonl` | Move | High |
| `runtime/agent_comms/thea.json` | `runtime/agent_comms/governance/onboarding/contracts_and_configs/thea.json` | Move | High |

### 5. Additional Protocols (Task/Election Related)

| Source File | Target Location | Action | Priority |
|-------------|----------------|--------|----------|
| `docs/agents/protocols/from_old_docs/protocols/atap_v0.4.md` | `runtime/agent_comms/governance/onboarding/protocols/task_acquisition_protocol.md` | Copy if still relevant | Low |
| `docs/agents/protocols/from_old_docs/protocols/automated_election_protocol_v1.md` | `runtime/agent_comms/governance/protocols/election/` | Copy to election directory | Low |
| `docs/agents/protocols/from_old_docs/protocols/supervisor_election_protocol.md` | `runtime/agent_comms/governance/protocols/election/` | Reference existing version | Low |
| `docs/agents/PHASE_1_LIFECYCLE_PROTOCOL_COMPLETION.md` | `runtime/agent_comms/governance/onboarding/info/phase_1_lifecycle_legacy.md` | Archive | Low |
| `runtime/governance/protocols/ELECTION_RULES.md` | `runtime/agent_comms/governance/protocols/election/` | Reference | Medium |
| `runtime/governance/protocols/agent_proposal_protocol.md` | `runtime/agent_comms/governance/protocols/` | Reference | Medium |

## Implementation Notes

1. **Prioritization**:
   - Start with high priority files that establish core identity and operational protocols
   - Next address medium priority files that extend operational capabilities
   - Low priority files (especially from `from_old_docs`) should be evaluated for uniqueness/relevance

2. **Avoid Duplication**:
   - Before copying, check if an equivalent file already exists in the target structure
   - For protocol files, prioritize versions from `runtime/governance/protocols/`
   - Reference rather than copy when appropriate to maintain single source of truth

3. **File Comparison Process**:
   - For potential duplicates, check:
     - File modification date (newer preferred)
     - Content completeness
     - References from other current files
     - Consistency with current system architecture

4. **Post-Migration Steps**:
   - Update references across files to point to new locations
   - Add a reference file at the root of `runtime/agent_comms/governance/onboarding/` listing key documents
   - Consider adding symbolic links for frequently referenced files to maintain compatibility

5. **Handling Legacy Documents**:
   - Archive rather than delete to preserve history
   - Add "LEGACY" or version notes to clearly indicate superseded documents
   - Document the rationale for archiving

## First Implementation Phase

1. Copy core identity and onboarding documents
2. Copy/reference essential protocols
3. Move configuration files
4. Copy high-priority guides
5. Add reference documentation

## Second Implementation Phase

1. Address medium priority protocols and standards
2. Handle any file conflicts or overlaps
3. Update cross-references 

## Final Implementation Phase

1. Review and evaluate low priority documents
2. Archive outdated or superseded files
3. Validate the complete structure 