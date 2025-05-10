# Standardized Task Tagging Schema

**Task:** `NORMALIZE-TASK-TAGS-SCHEMA-001`
**Status:** Design Phase

## 1. Purpose

To establish a consistent and structured vocabulary for tagging tasks within Dream.OS. This improves:

*   **Discoverability:** Finding related tasks easily.
*   **Filtering & Reporting:** Generating reports based on task types, domains, etc.
*   **Agent Task Selection:** Allowing agents to better identify tasks matching their capabilities or specialization.
*   **Metrics & Analysis:** Tracking effort across different work categories.

## 2. Schema Structure

Tags should ideally fall into one or more of the following categories. While not strictly enforced by tooling initially, adhering to these categories promotes consistency.

*   **`type`:** What kind of work is it?
*   **`domain`:** Which part of the system or project does it relate to?
*   **`tech`:** What specific technologies, libraries, or tools are involved?
*   **`meta`:** Other relevant process or status information.

## 3. Standard Tags (Recommended Vocabulary)

This list is not exhaustive but provides a recommended baseline. Agents should prefer using existing tags before creating new ones. New tags should ideally fit the category structure.

### Type Tags (`type:*`)

*   `type:feature`: Implementing new user-facing or system functionality.
*   `type:bug`: Fixing incorrect behavior.
*   `type:refactor`: Improving code structure without changing external behavior.
*   `type:chore`: Routine maintenance, updates, or tasks not fitting other categories.
*   `type:test`: Adding or improving tests.
*   `type:docs`: Writing or updating documentation.
*   `type:research`: Investigating a topic or potential solution.
*   `type:design`: Creating architecture or design documents.
*   `type:integration`: Connecting Dream.OS with external systems/services.
*   `type:security`: Addressing security vulnerabilities or improvements.
*   `type:performance`: Optimizing speed or resource usage.
*   `type:onboarding`: Related to agent setup, protocols, or initial tasks.
*   `type:governance`: Related to system rules, elections, or decision-making.
*   `type:migration`: Moving data or systems between formats/versions.

### Domain Tags (`domain:*`)

*   `domain:core`: Core Dream.OS framework (`src/dreamos/core`).
*   `domain:agent`: Specific agent implementation or base agent logic.
*   `domain:capability`: Agent capabilities library or schema.
*   `domain:tasking`: Task Nexus, task management, scheduling.
*   `domain:comms`: AgentBus, mailboxes, communication protocols.
*   `domain:db`: Database schema, adapter, migrations.
*   `domain:config`: System configuration files or loading.
*   `domain:cli`: Command-line interface.
*   `domain:gui`: Graphical user interface elements (if any).
*   `domain:testing`: Test infrastructure or specific test suites.
*   `domain:docs`: Documentation files or generation.
*   `domain:narrative`: Lore engine, dreamscape features.
*   `domain:bridge`: ChatGPT/Cursor bridge components.
*   `domain:social`: Social media integration features.
*   `domain:monitoring`: Statistics, logging, health checks.
*   `domain:deployment`: Infrastructure, CI/CD, deployment scripts.

### Technology Tags (`tech:*`)

*   `tech:python`: General Python development.
*   `tech:pydantic`: Use of Pydantic models/validation.
*   `tech:asyncio`: Use of Python's asyncio library.
*   `tech:sqlite`: SQLite database interaction.
*   `tech:llm`: Interaction with Large Language Models (OpenAI, Claude, etc.).
*   `tech:git`: Git commands or repository interaction.
*   `tech:docker`: Docker related tasks.
*   `tech:yaml`: YAML file manipulation.
*   `tech:json`: JSON file manipulation.
*   `tech:markdown`: Markdown file manipulation.
*   `tech:pytest`: Pytest framework usage.
*   `tech:ruff`: Ruff linter/formatter usage.
*   `tech:click`: Click CLI framework usage.
*   `tech:pyautogui`: PyAutoGUI library usage.
*   `tech:selenium`: Selenium/WebDriver usage.
*   `tech:fastapi`: FastAPI framework usage (if applicable).
*   *(Add other relevant libraries/tools as needed)*

### Meta Tags (`meta:*`)

*   `meta:blocked`: Task is currently blocked.
    *   `meta:blocked-dependency`: Blocked by an external library/tool/service.
    *   `meta:blocked-task`: Blocked waiting for another task.
    *   `meta:blocked-manual`: Blocked requiring manual intervention/edit.
    *   `meta:blocked-tooling`: Blocked by a failing internal tool (e.g., edit tool).
*   `meta:needs-review`: Output requires review by Supervisor/Captain.
*   `meta:high-priority`: Urgent or critical task.
*   `meta:low-priority`: Less urgent task.
*   `meta:experimental`: Exploratory or potentially unstable feature.
*   `meta:good-first-task`: Suitable for new agents.
*   `meta:tech-debt`: Addresses known technical debt.
*   `meta:self-proposed`: Task created by an agent for proactive work.

## 4. Usage Guidelines

*   **Apply Relevant Tags:** Add all applicable standard tags from the categories.
*   **Be Specific:** Prefer specific tags (e.g., `tech:sqlite`) over general ones (`tech:python`) where appropriate.
*   **Use Categories (Optional Prefix):** While not strictly enforced, prefixing with the category (e.g., `type:feature`, `domain:core`) can improve clarity, though it makes tags longer.
*   **Consistency:** Use the exact tag names defined here.
*   **Review:** Periodically review tag usage and update this schema as needed.

## 5. Next Steps

*   Task `APPLY-NORMALIZED-TAGS-001` should be created to update existing tasks in the backlog (`task_backlog.json` or DB) to conform to this schema.
*   Tooling or validation logic could be added to encourage/enforce schema adherence during task creation/updates. 