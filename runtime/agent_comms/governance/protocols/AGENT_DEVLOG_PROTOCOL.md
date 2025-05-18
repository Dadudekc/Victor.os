# Dream.OS Agent Devlog Protocol

**Version:** 1.0
**Effective Date:** 2025-05-25
**Status:** ACTIVE

## 📎 See Also

For a complete understanding of agent protocols, see:
- [Agent Onboarding Index](runtime/agent_comms/governance/onboarding/AGENT_ONBOARDING_INDEX.md) - Complete protocol documentation
- [Agent Onboarding Protocol](runtime/agent_comms/governance/protocols/AGENT_ONBOARDING_PROTOCOL.md) - Main onboarding process
- [Agent Operational Loop Protocol](runtime/agent_comms/governance/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md) - Core operational loop
- [Response Validation Protocol](runtime/agent_comms/governance/protocols/RESPONSE_VALIDATION_PROTOCOL.md) - Response standards
- [Messaging Format](runtime/agent_comms/governance/protocols/MESSAGING_FORMAT.md) - Communication standards
- [Resilience And Recovery Protocol](runtime/agent_comms/governance/protocols/RESILIENCE_AND_RECOVERY_PROTOCOL.md) - Error handling
- [Core Agent Identity Protocol](runtime/agent_comms/governance/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md) - Agent identity definition
- [Context Management Protocol](runtime/agent_comms/governance/protocols/CONTEXT_MANAGEMENT_PROTOCOL.md) - Context and planning management

## 1. PURPOSE

This protocol establishes the standard format, location, and content requirements for agent devlog entries in the Dream.OS ecosystem. Devlogs provide a crucial record of agent activities, decisions, and findings that enable monitoring, debugging, and historical analysis of system operation.

## 2. DEVLOG LOCATION AND STRUCTURE

### 2.1. File Locations

* **System Devlog:** `runtime/devlogs/devlog_YYYY-MM-DD.md` - Daily system-wide log
* **Agent Devlogs:** `runtime/devlogs/agents/Agent-<ID>.md` - Per-agent log file

### 2.2. Creation and Management

* New agent devlog files are automatically created when an agent first writes an entry
* System devlogs are created daily with the current date
* All devlog files use Markdown format for structured, human-readable content

## 3. STANDARD ENTRY FORMATS

All devlog entries must follow the specified formats to ensure consistency and machine parseability.

### 3.1. Standard Operational Cycle Entry

```markdown
**Cycle [Cycle Number]/25 - Agent-[Agent ID] - [Task Type/Category] - [Task ID or Brief Action Title] Completion**

* **Timestamp:** {{iso_timestamp_utc()}}
* **Status:** [Status Keyword - see Section 4]
* **Task ID:** [Official Task ID if applicable, e.g., TASK-XYZ-123, otherwise N/A]
* **Summary:** [One-sentence summary of the cycle's main achievement or status.]
* **Actions Taken:** [Bulleted list of specific actions performed]
  * Action 1 detail...
  * Action 2 detail...
* **Findings:** [Optional: Bulleted list of key observations or results.]
  * Finding 1...
* **Blockers:** [Optional: Description of any blockers encountered. Use #blocked tag.]
* **Recommendations:** [Optional: Specific recommendations arising from the work.]
* **Next Step:** [Description of the immediate next action to be taken in the loop.]
* **Tags:** #[tag1] #[tag2] #[tag3] ... #swarm_loop
```

### 3.2. Context Fork Entry

Context fork entries are special entries that document transitions between planning phases or major context shifts.

```markdown
**Context Fork - Agent-[Agent ID] - Planning Step [Step Number]**

* **Timestamp:** {{iso_timestamp_utc()}}
* **Status:** FORKED
* **Fork Source:** [Source Context Description]
* **Fork Target:** [Target Context Description]
* **Planning Step:** [Planning Step Number (1-4)]
* **Reason:** [Reason for Context Fork]
* **Tags:** #context_fork #[additional_tags]
```

### 3.3. Error and Recovery Entry

```markdown
**Error - Agent-[Agent ID] - [Error Type] - [Brief Error Description]**

* **Timestamp:** {{iso_timestamp_utc()}}
* **Status:** ERROR
* **Error Type:** [Type of error encountered]
* **Description:** [Detailed description of the error]
* **Impact:** [Impact on current task or system]
* **Recovery Plan:** [Steps to recover or mitigate]
* **Tags:** #error #[error_type] #[component_affected]
```

### 3.4. System State Change Entry

```markdown
**State Change - Agent-[Agent ID] - [State From] → [State To]**

* **Timestamp:** {{iso_timestamp_utc()}}
* **Status:** STATE_CHANGE
* **Previous State:** [Previous operational state]
* **New State:** [New operational state]
* **Reason:** [Reason for state change]
* **Implications:** [Any important implications of this state change]
* **Tags:** #state_change #[previous_state] #[new_state]
```

## 4. STATUS KEYWORDS

The following controlled vocabulary MUST be used for the **Status** field:

* `COMPLETED` - Task or action fully completed successfully
* `PARTIAL` - Partial completion with remaining work
* `BLOCKED` - Unable to proceed due to a blocker
* `ERROR` - Error encountered
* `INFO` - Informational entry
* `FORKED` - Context fork occurred
* `STATE_CHANGE` - Agent state changed
* `PLANNING` - Planning activity
* `ANALYZING` - Analysis activity
* `IMPLEMENTING` - Implementation activity
* `TESTING` - Testing activity
* `DOCUMENTING` - Documentation activity
* `REVIEWING` - Review activity
* `COORDINATING` - Coordination with other agents

## 5. TAGGING SYSTEM

All devlog entries MUST include appropriate tags using hashtag format (`#tag_name`). Tags aid in searching, filtering, and automatic analysis of logs.

### 5.1. Required Tags

* At least one tag from each of these categories must be included:
  * Action Type
  * Domain/Component
  * Process/Meta

### 5.2. Tag Categories

* **Action Type:**
  * `#patch` (Code/Doc modification)
  * `#refactor`
  * `#test_coverage`
  * `#implementation`
  * `#prototype`
  * `#analysis`
  * `#verification`
  * `#documentation`
  * `#compliance`
  * `#review`
  * `#report`
  * `#context_fork`
  * `#planning`

* **Domain/Component:**
  * `#pbm` (ProjectBoardManager)
  * `#thea_relay`
  * `#mailbox`
  * `#cli`
  * `#core_components`
  * `#protocol`
  * `#onboarding`
  * `#reporting`
  * `#devlog`
  * `#testing`
  * `#ui` / `#gui`
  * `#agent_bus`
  * `#task_nexus`
  * `#base_agent`
  * `#planning_system`
  * `#context_management`

* **Process/Meta:**
  * `#idle_initiative`
  * `#self_prompting`
  * `#swarm_loop` (Mandatory for standard cycles)
  * `#protocol_drift`
  * `#protocol_correction`
  * `#reset`
  * `#chore`
  * `#coordination`
  * `#tool_issue`
  * `#maintenance`
  * `#planning_step_1`
  * `#planning_step_2`
  * `#planning_step_3`
  * `#planning_step_4`

* **Priority (Optional):**
  * `#priority_high`
  * `#priority_medium`
  * `#priority_low`

## 6. THIRD PERSON REQUIREMENT

All devlog entries MUST follow the [Agent Third Person Communication Protocol](runtime/agent_comms/governance/protocols/AGENT_THIRD_PERSON_COMMUNICATION_PROTOCOL.md). Agents must refer to themselves in the third person using their agent identifier rather than first-person pronouns.

Examples:
* ✅ "Agent-5 analyzed the task requirements and identified three key components."
* ❌ "I analyzed the task requirements and identified three key components."

## 7. AUTOMATED DEVLOG GENERATION

The `context_commit_macro()` function in `tools/context_manager.py` provides automated devlog entry generation for context forks. This tool should be used to ensure consistency in context fork entries.

## 8. IMPLEMENTATION AND ENFORCEMENT

* All agents MUST implement proper devlog entry creation as part of their operational loop
* Devlog entries SHOULD be created at a minimum:
  * At the beginning of each operational cycle
  * Upon task completion or failure
  * When encountering errors or blockers
  * During state transitions
  * When forking context
* Monitoring agents may validate devlog compliance and report deviations

## 9. REFERENCES

* `tools/context_manager.py` - Context fork utility with devlog integration
* `runtime/agent_comms/governance/protocols/CONTEXT_MANAGEMENT_PROTOCOL.md` - Context management protocol
* `runtime/agent_comms/governance/protocols/AGENT_THIRD_PERSON_COMMUNICATION_PROTOCOL.md` - Third person communication protocol 