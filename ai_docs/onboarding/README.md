# Dream.OS Agent Onboarding - Central Guide

Welcome to the Dream.OS swarm! This document is your central starting point. **Full review of all linked documents is mandatory for effective operation.**

## 1. Foundational Documents (Read These First & Always)

*   **System Prompt (`system_prompt.md`):** Defines the **current operational mode**, the **Universal Agent Loop**, agent-specific directives (like Captain's Loop), and the **DRIFT CONTROL & SELF-CORRECTION PROTOCOL**. This is your primary instruction set.
*   **Autonomy & Self-Correction (`runtime/.../agent_autonomy_and_continuous_operation.md`):** Details the **core principles** of continuous operation, handling halts/idling, and the mandatory **self-correction procedure** when deviations occur. Reinforces the System Prompt rules.
*   **Architecture Overview (`ai_docs/architecture/README.md`):** Provides a high-level overview of the system's design, core components, and architectural tenets. **Consult this for understanding the system's structure.**
*   **This Guide (`ai_docs/onboarding/README.md`):** Provides a roadmap to key concepts and pointers to detailed documentation.

## 2. Setting Up (If Applicable)

*   **Environment Setup:** Follow the `Development Setup` section in the main project `CONTRIBUTING.md` (fork/clone, virtual env, `pip install -r requirements.txt`, `pip install -e .`).
*   **Claim Mailbox:** Establish your identity on first run by creating `claim.json` in your agent mailbox (`runtime/agent_comms/agent_mailboxes/<YourAgentID>/`).

### Managing Your Agent Directory

Each agent is assigned a personal workspace located in the `runtime/agent_comms/agent_mailboxes/<YourAgentID>/` directory. This workspace is crucial for managing tasks, intermediate files, logs, and other necessary data during agent operation.

#### Responsibilities:

1.  **Workspace Organization:**
    *   Your agent's mailbox is the primary directory for agent-specific files.
    *   Organize your workspace to separate long-term data (e.g., configuration files) from temporary or intermediate files.
    *   Keep your directory structured to make it easy to find and access files.

2.  **Cleaning Up After Tasks:**
    *   After completing tasks, remove unnecessary files from your directory to avoid clutter. This includes cleaning up:
        *   Temporary files generated during task execution.
        *   Unused logs, caches, or backup files.
    *   Regularly check for old or outdated files that may no longer be required.

3.  **File Naming Conventions:**
    *   Use clear and descriptive names for your files, and ensure that all files in your directory have meaningful extensions (e.g., `.json`, `.log`, `.txt`).
    *   For consistency, consider adopting a naming convention for temporary files and logs (e.g., using timestamps or task IDs).

4.  **Avoiding Conflicts:**
    *   Ensure that each agent's files are unique to their workspace. Avoid naming conflicts with other agents by using agent-specific identifiers in filenames (e.g., including the agent ID or task ID in filenames).

5.  **Backup and Safety:**
    *   While your workspace will be automatically managed by the system during regular operations, it's a good practice to manually back up any critical files if you believe they need to be preserved across sessions.

#### Best Practices:

*   **Routine Cleanup**: Regularly clean up old files that are no longer needed, such as temporary files or logs from completed tasks.
*   **Logging**: Store logs in a dedicated subdirectory, such as `logs/`, and rotate or delete them periodically to avoid filling up the workspace.
*   **Task Files**: Keep task-related files organized by task ID or timestamp for easy retrieval in case you need to review or debug task history.

By following these guidelines, you will help ensure a clean and efficient environment for your tasks and reduce the risk of errors or confusion caused by unnecessary clutter.

*   **Agent Contract:** As per general swarm guidelines (see root `README.md`), agents are expected to acknowledge or "sign" an onboarding contract. The specified central contract file `runtime/agent_registry/agent_onboarding_contracts.yaml` was not found during a recent scan. Agents should verify if this file needs to be created, or if individual contract files (e.g., `runtime/agent_registry/<YourAgentID>_contract.yaml`) are the current standard.

## 3. Core Operational Loop & Task Management

*   **Follow the Universal Agent Loop:** As defined in `system_prompt.md` (Mailbox -> Working Task -> Future Task/Plan -> Blocker Check -> Loop).
*   **Task Board Interaction:** Use approved tools (`ProjectBoardManager`, `TaskNexus`, etc.) to interact with task sources (`working_tasks.json`, `future_tasks.json`, `specs/current_plan.md`). Refer to `Task Management Standards` in `ai_docs/best_practices/`.
*   **Validate Completions:** Ensure tasks meet all requirements before marking complete.

## 4. Swarm Coordination & Knowledge

*   **Central Plan (`specs/current_plan.md`):** Consult for high-level objectives, structure, and organizational tasks.
*   **Knowledge Repository (`ai_docs/`):** **CRITICAL: Review relevant `ai_docs/` sections BEFORE implementing new patterns, docs, or utilities.** Check `best_practices/`, `api_docs/`, `architecture/`, `business_logic/`, `project_patterns/` etc.
*   **Swarm Sync (`runtime/swarm_sync_state.json`):** Monitor peer status (read every cycle) and report your own (write every 5 cycles) per `SwarmLinkedExecution` protocol.
*   **Devlog (`runtime/devlog/devlog.md`):** Log major actions/milestones.

## 5. Coding & Contribution Standards

*   **Reuse First:** Check `src/dreamos/core/` & `src/dreamos/coordination/` for utilities.
*   **Python Standards:** PEP 8, Typing, Docstrings (see `ai_docs/best_practices/`).
*   **Parameter Validation:** Mandatory for handlers receiving external data.
*   **Testing:** Use `pytest` for unit tests.
*   **Logging:** Use standard `logging`, avoid `print()`.
*   **Commits:** Use Conventional Commits format.
*   **Git Workflow:** Use feature branches.
*   (See `CONTRIBUTING.md` and `ai_docs/best_practices/` for details).

## 6. Governance & Escalation

*   **Points & Captaincy:** Refer to relevant documents in `runtime/governance/`.
*   **Escalation:** Report unresolvable blockers or protocol issues to the Captain's mailbox.

## 7. Continuous Operation, Self-Correction & Interrupt Handling (Reminder)

*   **No Halting:** Adhere strictly to the continuous operation mandate.
*   **Self-Correction:** Execute the full **DRIFT CONTROL & SELF-CORRECTION PROTOCOL** (`agent_autonomy_and_continuous_operation.md`) if you halt or idle improperly.
*   **Interpret Interruptions Correctly:** (This is crucial for maintaining continuous operation and responsiveness)
    *   _User Messages/Commands:_ Immediately halt the **current micro-task** (e.g., code analysis, planning next step, processing tool output, interacting with a tool), acknowledge the user command, **reset cycle count**, and execute the user's directive. The arrival of the user message implicitly cancels the interrupted micro-task and its intended output/action.
    *   _Transient System Errors:_ (e.g., network blip, brief UI unresponsiveness) Attempt immediate retry.
    *   _Persistent System Errors:_ (e.g., PBM failure, tooling bugs) Follow specific error handling protocols (refer to relevant system documentation or escalate if undefined).
    *   _User Tool Call Cancellation/Interruption:_ If a proposed tool call (e.g., `run_terminal_cmd`, `edit_file`) is explicitly cancelled by the user **or** interrupted by a new user message before successful completion:
        *   Log the cancellation/interruption internally.
        *   **Do not** ask the user for alternative instructions.
        *   Interpret the cancellation/interruption as an instruction to **skip** the cancelled/interrupted action and any directly dependent follow-up steps.
        *   Immediately and seamlessly proceed to the **next independent step** in the autonomous workflow (e.g., discover next task, perform next health check).

**Failure to master and apply the information in these core documents will lead to operational failures and require repeated self-correction.** Continuous learning and adherence are paramount.

## 8. Codebase Overview (from former ai_docs/codebase_overview/)

### 8.1. Guiding Principles

Dream.OS is designed as an autonomous, agent-driven system for code analysis, task execution, and self-improvement. Key architectural tenets include:

*   **Agent-Based Design:** Specialized agents perform core functions.
*   **Centralized Coordination:** Mechanisms like an AgentBus and Task Management systems orchestrate agent activities.
*   **Modularity:** Code is organized into distinct packages for clarity and maintainability.
*   **Asynchronous Operations:** `asyncio` is used for non-blocking I/O.
*   **Configuration Driven:** `AppConfig` manages system settings.
*   (See `ai_docs/architecture_docs/README.md` for more details on architectural tenets.)

### 8.2. Top-Level Directory Structure (Simplified)

Refer to the `Target Structure` in `specs/current_plan.md` for the most up-to-date proposed layout.

*   **`ai_docs/`**: The central knowledge repository for the swarm. Contains:
    *   `api_docs/`: Documentation for internal and external APIs/integrations.
    *   `architecture_docs/`: High-level architecture, design documents, ADRs.
    *   `best_practices/`: Coding standards, style guides, preferred patterns.
    *   `business_logic/`: Documentation of specific business rules and domain logic.
    *   `implementation_notes/`: Tracks TODOs, FIXMEs, technical debt.
    *   `onboarding/`: Central guide for new agents/contributors (this document).
    *   `project_patterns/`: Common design patterns used within the project.
*   **`specs/`**: Agentic planning and coordination hub. Contains:
    *   `current_plan.md`: The active project plan, task list, and target structure.
    *   `automation_tasks/`: (TODO) Plans for automated refactoring/organization.
    *   `archive/`: Completed or superseded plans.
*   **`src/`**: Main application source code.
    *   `dreamos/`: Core Dream.OS framework and components.
    *   `dreamscape/`: (Potentially) A specific feature module (e.g., content generation).
*   **`tests/`**: Unit and integration tests, mirroring the `src/` structure.
*   **`scripts/`**: Utility and operational scripts.
*   **`runtime/`**: Ephemeral data generated during operation (logs, agent communications, reports, configs).
*   **`docs/`**: General user and developer documentation (guides, standards not covered in `ai_docs`).
*   **`assets/`**: Static assets like images, icons.
*   **`templates/`**: Project-wide templates (e.g., for code generation, reports).
*   **`prompts/`**: LLM prompts used by agents.
*   **`.github/`**: CI/CD workflows and GitHub-specific configurations.
*   **Configuration Files:** `pyproject.toml`, `requirements.txt`, `.gitignore`, etc.

### 8.3. Core `src/dreamos/` Package Breakdown

This is the heart of the Dream.OS framework:

*   **`agents/`**: Implementations of various specialized agents (e.g., `AutoFixerAgent`, `PlannerAgent`).
*   **`core/`**: Fundamental framework logic, base classes (e.g., `BaseAgent`), event systems, core data models.
*   **`coordination/`**: Mechanisms for agent communication (e.g., `AgentBus`) and task management (e.g., `TaskNexus`, `ProjectBoardManager`).
*   **`services/`**: Shared background services, potentially including configuration loading, logging setup, or file management abstractions if not in `core` or `utils`.
*   **`integrations/`**: Connectors to external systems and tools (e.g., LLM APIs, Git, Playwright for browser automation, database clients).
*   **`utils/`**: Common, shared utility functions and classes used across the framework.
*   **`schemas/`**: Data validation schemas (e.g., Pydantic models) for messages, tasks, and configurations.
*   **`hooks/`**: Extension points or plugin interfaces for customizing framework behavior.
*   **`memory/`**: Components related to agent memory, context management, or persistence of learned information.
*   **`gui/`**: Logic related to graphical user interface interactions, possibly for bridging with tools like Cursor.
*   **`chat_engine/`**: Components specifically for managing interactions with chat-based LLMs, including prompt templating, response parsing, and conversation history.
*   **`monitoring/`**: System monitoring, health checks, and operational metrics.
*   **`cli/`**: Command-line interface entry points and logic.
*   **`automation/`**: Helper modules for GUI automation tasks (e.g., wrappers around `pyautogui`).

## 9. Maintenance & Cleanup Protocols

### 9.1. Project Cleanup Protocol

The project includes an automated cleanup system to maintain codebase health and organization. This protocol helps identify and handle:
- Orphaned files
- Duplicate functionality
- Low-utility code
- Complex files that need refactoring

#### Running the Cleanup Protocol

1. **Initial Analysis**
   ```bash
   python scripts/maintenance/project_cleanup_protocol.py
   ```
   This will:
   - Analyze project files using `project_analysis.json` and `chatgpt_project_context.json`
   - Calculate utility scores for files
   - Identify duplicate functions
   - Find orphaned files
   - Archive files that don't meet criteria

2. **Review Process**
   - Check `cleanup_log.json` for actions taken
   - Review archived files in `archive/orphans/`
   - Verify no critical functionality was lost
   - Restore any incorrectly archived files

3. **Cleanup Criteria**
   - **File Utility Score** (minimum 0.5)
     - Based on function count, class count, route count, docstring presence, and complexity
   - **Duplicate Functions** (maximum 3 occurrences)
     - Keeps the most complex implementation
     - Archives others
   - **Orphaned Files**
     - Files not imported or referenced
     - Moved to `archive/orphans/`
   - **Complexity Threshold** (maximum 30)
     - Files exceeding this are flagged for refactoring

4. **Safety Measures**
   - Files are archived rather than deleted
   - All actions are logged in `cleanup_log.json`
   - Archive directory serves as a safety net
   - Files can be restored if needed

#### When to Run Cleanup

Run the cleanup protocol:
- After major feature additions
- Before releases
- When project complexity increases
- When requested by the team
- As part of regular maintenance

#### Documentation

- Protocol implementation: `scripts/maintenance/project_cleanup_protocol.py`
- Protocol guide: `scripts/maintenance/cleanup_agent_prompt.md`
- Action log: `cleanup_log.json`

# Onboarding & Training Protocols

This section provides resources and guidelines for new contributors (human or agent) joining the project. It aims to provide a smooth ramp-up process, covering setup, core concepts, and initial tasks.

## Contributor Checklist

- [ ] ✅ Add or update setup instructions (dev environment, dependencies, credentials).
- [ ] ✅ Link to essential introductory documents (e.g., core architecture, key patterns).
- [ ] ✅ Suggest initial 'good first issues' or training exercises.
- [ ] ✅ Review and understand the cleanup protocol (`scripts/maintenance/project_cleanup_protocol.py`).
- [ ] ✅ Familiarize with cleanup criteria and safety measures.
- [ ] ✅ Know when to run cleanup (after features, before releases, etc.).

## 📎 Key Onboarding Resources

Make sure to review these additional guides located within the `ai_docs/onboarding/` directory:

- **`CONTRIBUTING.md`**: Refer to the main project `CONTRIBUTING.md` for general contribution guidelines.
- **`developer_guide.md`**: Essential for agents involved in developing or modifying Dream.OS components or other agents.
- **`user_onboarding.md`**: Provides a guide for users on setting up, configuring, and running Dream.OS.
- **`agent_operational_philosophy.md`**: Outlines core tenets and guiding principles for autonomous agent operation.
- **`branch_management.md`**: Details the branch management strategy for agents, including branch naming conventions, workflows, and best practices.
- *(Example: [First Agent Task Guide](./onboarding/first_agent_task.md))*
