# Agent Coordination Documentation
This directory contains essential documents for coordinating agent behavior and understanding system-wide protocols within the Dream.OS project.

Consult these documents to understand how agents should operate, communicate, and integrate within the broader system.

## Key Coordination Documents

*   **Rulebook:** [`rulebook.md`](./rulebook.md)
    *   Defines core operational principles, constraints, and mandatory behaviors for all agents.
*   **Agent Stop Protocol:** [`./protocols/agent_stop_protocol.md`](./protocols/agent_stop_protocol.md)
    *   Specifies how agents should log pauses related to meta-rules or awaiting review.
*   **Main Task List:** [`../tasks/task_list.md`](../tasks/task_list.md)
    *   The primary high-level task list for the entire Dream.OS project.

## Guidelines & Logs

*   **Onboarding Guidelines:**
    *   `./onboarding/supervisor_guidelines.md`
    *   `./onboarding/social_agent_guidelines.md`
    *   *(Add other agent-specific guidelines here)*
*   **Governance Logs:**
    *   Stored in `../core/memory/governance_memory.jsonl` (via `../core/engines/governance_memory_engine.py`)

## Notes

*   Maintain consistency across all related documentation.
*   Use relative paths when referencing documents within the `_agent_coordination` module.
*   Use absolute paths when referencing core documents from agent-specific task lists or onboarding materials.

## Key Areas:

- **/protocols**: Defines standard communication formats, message structures, and interaction patterns (e.g., file-based message bus).
- **/onboarding**: Provides agent-specific guidelines, role definitions, and initial setup instructions.
- **/rulebook** (Potential Future): A central location for overarching system rules and constraints.

## 🛠️ Available Tool Scripts (`tools/`)

These scripts provide helpful automation for common development and operational tasks within the Dream.OS framework, particularly related to agent coordination and analysis. They can be executed directly or invoked by agents via the `run_terminal_cmd` capability.

*(Note: Descriptions below are placeholders based on filenames. Detailed documentation should be added by reading the scripts.)*

### 1. `run_agent.py`
*   **Purpose:** (Likely runs a specific agent process)
*   **Usage:** (TBD)

### 2. `project_context_producer.py`
*   **Purpose:** (Likely gathers or generates context about the project)
*   **Usage:** (TBD)

### 3. `code_applicator.py`
*   **Purpose:** (Likely applies generated code changes to files, possibly mentioned in task lists)
*   **Usage:** (TBD)

### 4. `diagnostics.py`
*   **Purpose:** (Likely runs diagnostic checks on the system or agents)
*   **Usage:** (TBD)

### 5. `context_planner.py`
*   **Purpose:** (Likely involved in planning based on context)
*   **Usage:** (TBD)

### 6. `check_confirmation_state.py`
*   **Purpose:** (Likely checks a confirmation or state flag)
*   **Usage:** (TBD)

### 7. `reload_agent_context.py`
*   **Purpose:** (Likely triggers a reload of context for an agent)
*   **Usage:** (TBD)

### 8. `proposal_security_scanner.py`
*   **Purpose:** (Likely scans rulebook update proposals for security issues)
*   **Usage:** (TBD)

### 9. `project_scanner.py`
*   **Purpose:** (Likely performs a broad scan or analysis of the project codebase)
*   **Usage:** (TBD) 