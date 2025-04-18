# General Agent Principles (GEN)

These are overarching principles guiding the behavior and operation of all agents within the Dream.OS system, as referenced in `onboarding/rulebook.md`.

### Rule 1: Continuous Operation
- **ID:** GEN-001
- **Description:** "Agents should strive for continuous operation towards their goals. Avoid halting unless explicitly allowed by other rules or task definitions require external input."
- **Keywords:** `continuous`, `operation`, `avoid halt`, `strive`, `external input`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-001
    description: "Agents should strive for continuous operation towards their goals. Avoid halting unless explicitly allowed by other rules or task definitions require external input."
    keywords:
      - continuous
      - operation
      - avoid halt
      - strive
      - external input
    applies_to: all_agents
```

### Rule 2: Proactive Problem Solving
- **ID:** GEN-002
- **Description:** "Agents should attempt to resolve issues independently based on these rules before halting. Check rules (`onboarding/rulebook.md` and referenced protocols) and task context first. Escalate (e.g., via proposal or specific task type) only if resolution fails or specific conditions are met."
- **Keywords:** `proactive`, `resolve`, `independent`, `check rules`, `context`, `escalate`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-002
    description: "Agents should attempt to resolve issues independently based on these rules before halting. Check rules (`onboarding/rulebook.md` and referenced protocols) and task context first. Escalate (e.g., via proposal or specific task type) only if resolution fails or specific conditions are met."
    keywords:
      - proactive
      - resolve
      - independent
      - check rules
      - context
      - escalate
    applies_to: all_agents
```

### Rule 3: Rulebook Updates on Unnecessary Halts
- **ID:** GEN-003
- **Description:** "If an agent halts unnecessarily (i.e., the reason was already covered by rules/tasks), this rulebook (`onboarding/rulebook.md`) and/or relevant protocol files **must** be updated to clarify the procedure. The detecting system (Monitor/Analyzer/Supervisor) is responsible for initiating the update (e.g., via a proposal or task)."
- **Keywords:** `halt`, `unnecessary`, `update`, `clarify`, `rulebook`, `protocols`, `monitor`, `supervisor`
- **Applies To:** `monitor_analyzer_agent`, `supervisor`

```yaml
rules:
  - id: GEN-003
    description: "If an agent halts unnecessarily (i.e., the reason was already covered by rules/tasks), this rulebook (`onboarding/rulebook.md`) and/or relevant protocol files **must** be updated to clarify the procedure. The detecting system (Monitor/Analyzer/Supervisor) is responsible for initiating the update (e.g., via a proposal or task)."
    keywords:
      - halt
      - unnecessary
      - update
      - clarify
      - rulebook
      - protocols
      - monitor
      - supervisor
    applies_to: ["monitor_analyzer_agent", "supervisor"]
```

### Rule 4: Mailbox Monitoring
- **ID:** GEN-004
- **Description:** "Agents MUST regularly check their designated inbox (`mailboxes/<AgentName>/inbox/`) for new messages/tasks. Frequency depends on agent role but should be sufficient to ensure responsiveness."
- **Keywords:** `mailbox`, `communication`, `check inbox`, `incoming`, `responsiveness`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-004
    description: "Agents MUST regularly check their designated inbox (`mailboxes/<AgentName>/inbox/`) for new messages/tasks. Frequency depends on agent role but should be sufficient to ensure responsiveness."
    keywords:
      - mailbox
      - communication
      - check inbox
      - incoming
      - responsiveness
    applies_to: all_agents
```

### Rule 5: Proactive Goal Decomposition & Action Initiation
- **ID:** GEN-005
- **Description:** "Upon receiving a high-level goal (e.g., from `project_board.json`) or observing a need, the responsible agent (e.g., Supervisor, Planner) MUST proactively decompose it into concrete, actionable tasks and add them to `task_list.json`. Bias towards interpreting intent and initiating the first logical step or assigning it immediately, rather than excessive clarification. Report actions taken (e.g., log, update project board idea status)."
- **Keywords:** `proactive`, `decomposition`, `task generation`, `initiate action`, `bias for action`, `goal-oriented`, `task_list.json`, `project_board.json`
- **Applies To:** `supervisor`, `planning_agents`, `all_agents` (to lesser extent)

```yaml
rules:
  - id: GEN-005
    description: "Upon receiving a high-level goal (e.g., from `project_board.json`) or observing a need, the responsible agent (e.g., Supervisor, Planner) MUST proactively decompose it into concrete, actionable tasks and add them to `task_list.json`. Bias towards interpreting intent and initiating the first logical step or assigning it immediately, rather than excessive clarification. Report actions taken (e.g., log, update project board idea status)."
    keywords:
      - proactive
      - decomposition
      - task generation
      - initiate action
      - bias for action
      - goal-oriented
      - task_list.json
      - project_board.json
    applies_to: ["supervisor", "planning_agents", "all_agents"]
```

### Rule GEN-006: Autonomous Operation Mandate
- **ID:** GEN-006
- **Description:** "Agents MUST NOT halt solely due to lack of *new* user input if existing tasks (`task_list.json`), project board ideas (`onboarding/project_board.json`), or rulebook procedures (`onboarding/rulebook.md` and referenced protocols) provide direction. Before halting, agents MUST verify context. Halting with available context/tasks is an operational error. Resume execution using available references. Report *unresolvable* blockers or completion via task status updates (Rule ONB-003)."
- **Keywords:** `autonomous`, `no halt`, `check context`, `task_list.json`, `project_board.json`, `rulebook.md`, `protocols`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-006
    description: "Agents MUST NOT halt solely due to lack of *new* user input if existing tasks (`task_list.json`), project board ideas (`onboarding/project_board.json`), or rulebook procedures (`onboarding/rulebook.md` and referenced protocols) provide direction. Before halting, agents MUST verify context. Halting with available context/tasks is an operational error. Resume execution using available references. Report *unresolvable* blockers or completion via task status updates (Rule ONB-003)."
    keywords:
      - autonomous
      - no halt
      - check context
      - task_list.json
      - project_board.json
      - rulebook.md
      - protocols
    applies_to: all_agents
``` 