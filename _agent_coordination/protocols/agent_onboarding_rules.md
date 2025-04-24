# Agent Onboarding Rules (ONB-)

*This file defines the specific rules agents must follow during the initial onboarding process.*

*(Placeholder - Content to be added based on system design)*

---

**ONB-001:** No placeholders or simulations. All actions must be real execution.

**ONB-007:** Validate parameters. If invalid, fail the task immediately.

*(Add more rules here)*

### Rule ONB-001 (Reforged): No Placeholders. No Simulations. Only Completion.
- **ID:** ONB-001
- **Description:** All agents must complete their assigned tasks fully and functionally. Placeholders, stubs, TODO comments, simulated returns, or passive logging-only methods are strictly forbidden—even in scaffolding or infrastructure tasks.
- **Exception:** None. If an agent cannot complete its task due to missing dependencies, undefined behavior, or system limitations, it must:
  1. Log the failure with full detail.
  2. Update the task as `BLOCKED` or `FAILED` in `task_list.json`.
  3. Write a message to its assigned `mailbox.json` (Clarification: This seems redundant if Task List is updated; focusing on Task List update as primary feedback).
  4. Notify the ProjectBoard or coordinating agent (e.g., `AgentMonitorAgent`) with context (Clarification: Requires specific implementation; for now, logging + Task List update is primary).
  5. Await reassignment or patch resolution.
- **Motto:** "There is no simulation. There is only execution."
- **Applies To:** `all_agents`, `all_systems`, including `auto_stub_sweep_001`

```yaml
rules:
  - id: ONB-001
    description: "All agents must complete their assigned tasks fully and functionally. Placeholders, stubs, TODO comments, simulated returns, or passive logging-only methods are strictly forbidden—even in scaffolding or infrastructure tasks. Exception: None. If completion is impossible, agent must log failure, update task status (BLOCKED/FAILED), and await resolution."
    keywords:
      - no placeholders
      - no simulation
      - completion mandatory
      - no stubs
      - functional
      - report failure
      - blocked
    applies_to: all_agents
```

### Rule ONB-002: Communication Protocol
- **ID:** ONB-002
- **Description:** "Agents primarily communicate via file drops in designated `mailbox/<AgentName>/inbox/` directories. Check your inbox regularly for tasks and messages."
- **Keywords:** `communication`, `inbox`, `mailbox`, `file drop`, `tasks`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-002
    description: "Agents primarily communicate via file drops in designated `mailbox/<AgentName>/inbox/` directories. Check your inbox regularly for tasks and messages."
    keywords:
      - communication
      - inbox
      - mailbox
      - file drop
      - tasks
    applies_to: all_agents
```

### Rule ONB-003: Task Acceptance & Status Update
- **ID:** ONB-003
- **Description:** "Upon successfully processing an `inbox` message, the agent MUST update the status of the original task in `task_list.json` (using `task_utils.update_task_status`) to `COMPLETED` or `FAILED`, including relevant results or errors. The `original_task_id` is provided in the inbox message."
- **Keywords:** `task update`, `status`, `completed`, `failed`, `task_list.json`, `original_task_id`
- **Applies To:** `all_agents` (that process tasks)

```yaml
rules:
  - id: ONB-003
    description: "Upon successfully processing an `inbox` message, the agent MUST update the status of the original task in `task_list.json` (using `task_utils.update_task_status`) to `COMPLETED` or `FAILED`, including relevant results or errors. The `original_task_id` is provided in the inbox message."
    keywords:
      - task update
      - status
      - completed
      - failed
      - task_list.json
      - original_task_id
    applies_to: all_agents # specifically agents handling dispatched tasks
```

### Rule ONB-004: Reporting Results (Deprecated/Clarified)
- **ID:** ONB-004
- **Description:** "(Deprecated by ONB-003) Results and errors should be reported by updating the status and relevant fields (`result_summary`, `error_message`) of the original task in `task_list.json`. Writing separate files to `outbox` is generally not required unless specified by a particular workflow."
- **Keywords:** `deprecated`, `task_list.json`, `result_summary`, `error_message`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-004
    description: "(Deprecated by ONB-003) Results and errors should be reported by updating the status and relevant fields (`result_summary`, `error_message`) of the original task in `task_list.json`. Writing separate files to `outbox` is generally not required unless specified by a particular workflow."
    keywords:
      - deprecated
      - task_list.json
      - result_summary
      - error_message
    applies_to: all_agents
```

### Rule ONB-005: Dependency Management
- **ID:** ONB-005
- **Description:** "If your task requires external libraries or dependencies not already listed in the root `requirements.txt`, propose additions by adding them to `proposals/dependency_proposals.txt` (relative to project root) or a designated proposal file."
- **Keywords:** `dependencies`, `requirements.txt`, `propose`, `libraries`, `proposals`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-005
    description: "If your task requires external libraries or dependencies not already listed in the root `requirements.txt`, propose additions by adding them to `proposals/dependency_proposals.txt` (relative to project root) or a designated proposal file."
    keywords:
      - dependencies
      - requirements.txt
      - propose
      - libraries
      - proposals
    applies_to: all_agents
```

### Rule ONB-006: Critical Error Handling
- **ID:** ONB-006
- **Description:** "If a critical error prevents task completion (e.g., exception during message processing), ensure the original task status in `task_list.json` is updated to `FAILED` with an appropriate `error_message`. The inbox message itself should be moved to the agent's `error/` directory by the `process_directory_loop`."
- **Keywords:** `error handling`, `failed`, `task_list.json`, `error_message`, `mailbox error dir`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-006
    description: "If a critical error prevents task completion (e.g., exception during message processing), ensure the original task status in `task_list.json` is updated to `FAILED` with an appropriate `error_message`. The inbox message itself should be moved to the agent's `error/` directory by the `process_directory_loop`."
    keywords:
      - error handling
      - failed
      - task_list.json
      - error_message
      - mailbox error dir
    applies_to: all_agents
```

### Rule ONB-007: Handler Dependencies & External Configuration
- **ID:** ONB-007
- **Description:** "Agent command handlers must directly implement logic using available tools (filesystem, controllers, internal state, etc.) or call other verifiable internal agent functions. Placeholders for external actions are forbidden (Ref: ONB-001). If a handler's action requires external configuration not known *a priori* (e.g., a system-specific command, API key, file path), this configuration MUST be provided via the incoming message's `params`. Handlers MUST validate required parameters and FAIL explicitly (return `False`, log error) if they are missing or invalid (e.g., default placeholder values). See `CursorControlAgent._handle_resume_operation` for an example pattern."
- **Keywords:** `handler`, `implementation`, `dependencies`, `parameters`, `configuration`, `no placeholders`, `fail fast`, `validate params`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-007
    description: "Agent command handlers must directly implement logic using available tools or internal functions. External configuration (e.g., specific commands, keys, paths) MUST be provided via message `params`. Handlers MUST validate required params and FAIL explicitly if missing/invalid. Placeholders forbidden (Ref: ONB-001)."
    keywords:
      - handler
      - implementation
      - dependencies
      - parameters
      - configuration
      - no placeholders
      - fail fast
      - validate params
    applies_to: all_agents
```

### Rule ONB-008: Mailbox Check & Responsiveness
- **ID:** ONB-008
- **Description:** Agents must poll their inbox directory (`_agent_coordination/shared_mailboxes/agent_<id>/mailbox.json`) at a configurable heartbeat interval (e.g., 30s) and process any new messages immediately. Failure to check the mailbox within two heartbeat intervals should be logged and reported as a performance issue.
- **Keywords:** `mailbox`, `poll`, `heartbeat`, `responsiveness`
- **Applies To:** `all_agents`

### Rule ONB-009: Proactive Task Claiming
- **ID:** ONB-009
- **Description:** Agents must review the global task boards (`tasks/master_tasks_*.json`) after polling the mailbox. If an unclaimed task is available, the agent MUST claim exactly one task (update `claimed_by`) before any other assignment, then begin execution immediately.
- **Keywords:** `claim`, `task_board`, `master_tasks`, `proactive`
- **Applies To:** `all_agents`

### Rule ONB-010: Status Visibility
- **ID:** ONB-010
- **Description:** Agents must update their status in `project_board.json` and `shared_inbox.json` on every state change. Status values include `idle`, `busy`, and `offline`. Updates must include the agent's current action or task ID and a timestamp.
- **Keywords:** `status`, `project_board`, `visibility`, `coordination`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-008
    description: "Agents must poll their inbox directory (`_agent_coordination/shared_mailboxes/agent_<id>/mailbox.json`) at a configurable heartbeat interval (e.g., 30s) and process any new messages immediately. Failure to check the mailbox within two heartbeat intervals should be logged and reported as a performance issue."
    keywords:
      - mailbox
      - poll
      - heartbeat
      - responsiveness
    applies_to: all_agents

  - id: ONB-009
    description: "Agents must review the global task boards (`tasks/master_tasks_*.json`) after polling the mailbox. If an unclaimed task is available, the agent MUST claim exactly one task (update `claimed_by`) before any other assignment, then begin execution immediately."
    keywords:
      - claim
      - task_board
      - master_tasks
      - proactive
    applies_to: all_agents

  - id: ONB-010
    description: "Agents must update their status in `project_board.json` and `shared_inbox.json` on every state change. Status values include `idle`, `busy`, and `offline`. Updates must include the agent's current action or task ID and a timestamp."
    keywords:
      - status
      - project_board
      - visibility
      - coordination
    applies_to: all_agents
``` 