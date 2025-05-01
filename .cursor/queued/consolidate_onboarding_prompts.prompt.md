# filename: .cursor/queued/consolidate_onboarding_prompts.prompt.md
Task: Consolidate agent onboarding prompts into a shared template system.
Context:
  duplication_issue:
    - Each agent (agent_001, agent_002, agent_008, etc.) has a nearly identical start_prompt.md with only small differences like agent ID.
Instructions:
  - Create `_agent_coordination/onboarding/_start_prompt_template.md` containing the shared onboarding content with a `{{agent_id}}` placeholder.
  - Update each agent's `start_prompt.md` under `_agent_coordination/onboarding/agent_*` to reference the shared template and substitute their `agent_id` dynamically (e.g., via a simple include or placeholder replacement).
  - Remove duplicated hardcoded onboarding text from each agent folder's `start_prompt.md`.
  - Validate that rendering the templates for each agent produces the correct `start_prompt.md` with the appropriate agent ID.
  - Commit message suggestion: "refactor: consolidate agent onboarding prompts into shared template with dynamic agent_id"
