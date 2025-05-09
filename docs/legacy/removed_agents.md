# Removed Legacy Agents

This document lists agents that have been removed from the Dream.OS codebase as they no longer align with current architectural standards.

## REMOVE-LEGACY-AGENTS-001 (Date: YYYY-MM-DD - *Please fill in current date*)

The following agents were removed because they represented legacy abstractions from a pre-Cursor prompt agent era and do not align with the current Cursor-client-only execution model. Their intended logic (navigation, task auditing, tool tracking) should now be implemented as capabilities embedded in prompt templates, emergent behaviors from looped injection, or triggered via mailbox events handled by THEA's relay mechanism.

*   **`src/dreamos/agents/agent3_navigator.py` (Agent: agent3_navigator)**
    *   Reason: Legacy navigation agent. Functionality to be achieved via prompt-driven capabilities.

*   **`src/dreamos/agents/agent4_task_auditor.py` (Agent: agent4_task_auditor)**
    *   Reason: Legacy task auditing agent. Auditing logic to be integrated into core workflows or specialized auditing tools/prompts.

*   **`src/dreamos/agents/agent7_toolsmith.py` (Agent: agent7_toolsmith)**
    *   Reason: Legacy tool tracking/management agent. Tool usage and availability should be managed via current agent interaction patterns and capabilities. 