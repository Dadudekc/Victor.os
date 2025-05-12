# Devlog Reporting Standard v1.0

**Status:** Proposed **Date:** {{iso_timestamp_utc()}} **Owner:** Agent-4

## 1. Purpose

This standard defines the expected format and tagging conventions for agent devlog entries (`runtime/devlog/agents/Agent-*.md`) to improve consistency, clarity, and machine parseability for monitoring and analysis.

## 2. Standard Entry Format

Each discrete cycle or significant action SHOULD generate a new entry appended to the agent's devlog file. Entries MUST follow this semi-structured Markdown format:

```markdown
**Cycle [Cycle Number]/25 - Agent-[Agent ID] - [Task Type/Category] - [Task ID or Brief Action Title] Completion**

*   **Timestamp:** {{iso_timestamp_utc()}} // Auto-generated timestamp
*   **Status:** [Status Keyword - see Section 3]
*   **Task ID:** [Official Task ID if applicable, e.g., TASK-XYZ-123, otherwise N/A]
*   **Summary:** [One-sentence summary of the cycle's main achievement or status.]
*   **Actions Taken:** [Bulleted list of specific actions performed, using keywords like **Patched**, **Created Task**, **Analyzed**, **Verified**, **Reported**, **Read**, **Wrote**, etc.]
    *   Action 1 detail...
    *   Action 2 detail...
*   **Findings:** [Optional: Bulleted list of key observations or results.]
    *   Finding 1...
*   **Blockers:** [Optional: Description of any blockers encountered. Use #blocked tag.]
*   **Recommendations:** [Optional: Specific recommendations arising from the work.]
*   **Next Step:** [Description of the immediate next action to be taken in the loop.]
*   **Tags:** #[tag1] #[tag2] #[tag3] ... #swarm_loop
```

**Key Fields Explanation:**

*   **Header Line:** Clearly identifies Cycle, Agent, general Task Type/Category, and a specific Task ID or descriptive title.
*   **Timestamp:** Automatically generated UTC timestamp.
*   **Status:** A keyword indicating the outcome of the cycle (see controlled vocabulary below).
*   **Task ID:** The formal ID from the task board, if applicable.
*   **Summary:** Concise overview.
*   **Actions Taken:** Concrete verbs describing what was done.
*   **Findings/Blockers/Recommendations:** Optional structured fields for detailed results.
*   **Next Step:** Crucial for demonstrating loop continuity.
*   **Tags:** Hashtags from the controlled vocabulary (see Section 4) for categorization. `#swarm_loop` is mandatory on all entries indicating a standard cycle action.

## 3. Status Keywords (Controlled Vocabulary)

Use ONE of the following keywords for the `Status:` field:

*   `Task_Completed`: The assigned task (referenced by Task ID) is fully completed.
*   `SubTask_Completed`: A self-assigned sub-task (part of Idle Initiative or breaking down larger task) is complete.
*   `Analysis_Complete`: A cycle focused on analysis finished, findings reported.
*   `Verification_Complete`: A cycle focused on verification finished, results reported.
*   `Progress_Update`: Work was performed on a task, but it is not yet complete.
*   `Blocked`: Agent cannot proceed due to an external factor (requires #blocked tag).
*   `Error`: An unexpected error occurred during execution (requires #error tag).
*   `Config_Updated`: Cycle involved primarily configuration changes or onboarding updates.
*   `Idle_Action_Taken`: An action was taken as part of the Idle Protocol (e.g., proposed task, sent report).

## 4. Tag Ontology (Controlled Vocabulary v1.0)

Use hashtags (`#tag_name`) to categorize entries. Multiple tags are encouraged. `#swarm_loop` is mandatory for standard cycle updates.

*   **Status:**
    *   `#task_completion`
    *   `#task_creation`
    *   `#progress_update`
    *   `#analysis_complete`
    *   `#verification_complete`
    *   `#blocked`
    *   `#error`
*   **Action Type:**
    *   `#patch` (Code/Doc modification)
    *   `#refactor`
    *   `#test_coverage`
    *   `#implementation`
    *   `#prototype`
    *   `#analysis`
    *   `#verification`
    *   `#documentation`
    *   `#compliance`
    *   `#review`
    *   `#report`
*   **Domain/Component:**
    *   `#pbm` (ProjectBoardManager)
    *   `#thea_relay`
    *   `#mailbox`
    *   `#cli`
    *   `#core_components`
    *   `#protocol`
    *   `#onboarding`
    *   `#reporting`
    *   `#devlog`
    *   `#testing`
    *   `#ui` / `#gui`
    *   `#scanner`
    *   `#agent_bus`
    *   `#task_nexus`
    *   `#base_agent`
    *   *Add specific tool/agent names as needed (e.g., `#agent1`, `#vulture`)*
*   **Process/Meta:**
    *   `#idle_initiative`
    *   `#self_prompting`
    *   `#swarm_loop` (Mandatory for standard cycles)
    *   `#protocol_drift`
    *   `#protocol_correction`
    *   `#reset`
    *   `#chore`
    *   `#coordination`
    *   `#tool_issue`
    *   `#maintenance`
*   **Priority (Optional):**
    *   `#priority_high`
    *   `#priority_medium`
    *   `#priority_low`

## 5. Implementation & Enforcement

- This standard should be referenced in agent onboarding materials.
- Agents should strive to adhere to this format in their devlog output.
- Monitoring agents (like Agent-6) may use this standard to parse devlogs for status checks or specific keywords/tags.
- Future tools could be developed to automatically validate devlog entry formats.
