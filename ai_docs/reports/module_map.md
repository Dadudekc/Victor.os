# Dream.OS · Module Map & Upgrade Plan  
*Task ID — `TASK‑SYS‑001·P2` • Autogen by Agent-5 • Last run: {{Manually updated by Agent-5: AGENT_TIMESTAMP}}*

---

## 📋 Index
1. [Legend](#legend)
2. [Directory Tree](./directory_tree.md) (Separate File)
3. [Core Modules Table](#core)
4. Module Categories:
    - [Agents Modules](#agents-modules)
    - [Tools Modules](#tools-modules)
    - [Automation Modules](#automation-modules)
    - [Services Modules](#services-modules)
    - [Integrations Modules](#integrations-modules)
    - [CLI Modules](#cli-modules)
    - [Utilities Modules](#utilities-modules)
5. [Backlog Tickets](#backlog)

---

## <a name="legend"></a>🔑 Legend

| Emoji | Meaning | Refactor Maturity |
| :--: | --- | --- |
| ✅ | **Keep** – leave as‑is | **Stable** |
| ♻️ | **Refactor** – minor/major polish | **Minor / Major** |
| ⚠️ | **Deprecated** – migrate, then remove | **Legacy / Fragile** |
| 🔍 | **Review** – timed‑out / not yet parsed | **Review** |

_Statefulness_ abbreviations → **SL** Stateless, **IM** In‑Mem, **PS** Persistent Store, **LP** Looped Svc.

---

## <a name="tree"></a>📂 Directory Tree

The main Dream.OS directory tree has been moved to its own file: [./directory_tree.md](./directory_tree.md)

---

## <a name="core"></a>🧩 Core Modules

<!-- BEGIN CORE -->
| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | Maturity | Recommendation | Notes |
|---|---|---|---|---|---|---|---|---|
| `src/dreamos/core/coordination/base_agent.py` | Core | Class: BaseAgent, Func: __init__, Func: register_command_handler, … | Core Component: BaseAgent. Purpose: Base class for all Dream.OS agents providing common functionality. | N/A | IM, uses PS | N/A | N/A |  |
| `src/dreamos/core/coordination/message_patterns.py` | Core | Class: TaskStatus, Class: TaskPriority, Func: create_task_message, Func: update_task_status, … | Core Component: TaskStatus. Purpose: Task execution status. | N/A | SL | N/A | N/A |  |
| `src/dreamos/core/coordination/schemas/voting_patterns.py` | Core | Class: VoteQuestion, Class: VoteInitiated, Func: validate_vote_message, … | Core Component: VoteQuestion. Purpose: Structure for a single question within a vote. | N/A | SL | N/A | N/A |  |
| `src/dreamos/core/identity/agent_identity.py` | Core | Class: AgentIdentity, Class: Config, Func: ensure_datetime_obj, Func: update | Core Component: AgentIdentity. Purpose: Represents the persistent identity and metadata of an agent. | N/A | SL | N/A | N/A |  |
| `src/dreamos/core/identity/agent_identity_manager.py` | Core | Class: AgentIdentityError, Class: AgentIdentityManager, Func: get_agent_identity_manager, Func: __new__, … | Core Component: AgentIdentityError. Purpose: Custom exception for Agent Identity Manager errors. | N/A | IM, uses PS | N/A | N/A |  |
| `src/dreamos/core/identity/agent_identity_store.py` | Core | Class: AgentIdentityStore, Func: __init__, Func: _ensure_store_exists, … | Core Component: AgentIdentityStore. Purpose: Handles persistence of AgentIdentity objects to a JSON file. | N/A | PS | N/A | N/A |  |
| `src/dreamos/core/coordination/event_payloads.py` | Core | Class: RouteInjectPayload, Class: TaskEventPayload, … | Core Component: RouteInjectPayload. Purpose: Payload for ROUTE_INJECTION_REQUEST event. | N/A | SL | N/A | N/A |  |
| `src/dreamos/core/coordination/event_types.py` | Core | Class: EventType, Class: AgentStatus | Core Component: EventType. Purpose: Standardized event types for the Dream.OS AgentBus. | N/A | SL | N/A | N/A |  |
| `src/dreamos/core/health_checks/cursor_window_check.py` | Core | Func: _load_coordinates, Func: check_cursor_window_reachability | Core Functions: _load_coordinates. Purpose: Core system operations | N/A | IM, uses PS | N/A | N/A |  |
| `src/dreamos/core/health_checks/cursor_status_check.py` | Core | N/A | N/A | N/A | IM | N/A | N/A |  |
| `src/dreamos/core/eventing/publishers.py` | Core | N/A | N/A | N/A | N/A | N/A | N/A | File not found in workspace. |
| `src/dreamos/core/logging/swarm_logger.py` | Core | Func: _get_log_path, Func: log_agent_event | Core Functions: _get_log_path. Purpose: Core system operations | N/A | IM, uses PS | N/A | N/A |  |
| `src/dreamos/core/feedback/thea_feedback_ingestor.py` | Core | Func: load_recent_feedback, Func: inject_feedback_to_thea | Core Functions: load_recent_feedback. Purpose: Core system operations | N/A | PS | N/A | N/A |  |
| `src/dreamos/core/tasks/nexus/task_nexus.py` | Core | Class: TaskNexus, Func: __init__, Func: _load, … | Core Component: TaskNexus. Purpose: Core system functionality | N/A | N/A | N/A | N/A |  |
| `src/dreamos/core/config_utils.py` | Core | Func: load_config, Func: get_config_value, … | Configuration Helper | N/A | N/A | N/A | N/A |  |
| `src/dreamos/core/comms/mailbox.py` | Core | Class: MailboxError, Class: MailboxHandler, Func: __init__, Func: _get_target_inbox, … | Core Component: MailboxError. Purpose: Custom exception for mailbox operations. | N/A | N/A | N/A | N/A |  |
| `src/dreamos/core/bots/orchestrator_bot.py` | Core | Class: NewMsgHandler, Func: handle_message, Func: on_created | Core Component: NewMsgHandler. Purpose: Core system functionality | N/A | N/A | N/A | N/A |  |
| `src/dreamos/core/comms/project_board.py` | Core | Class: ProjectBoardError, Class: ProjectBoardManager, Func: __init__, Func: update_task_status, … | Core Component: ProjectBoardError. Purpose: Custom exception for project board operations. | N/A | N/A | N/A | N/A |  |
<!-- END CORE -->

<sub>Full table autogen via `devtools/module_mapper.py`.</sub>

---

## <a name="agents-modules"></a>🤖 Agents Modules

<!-- BEGIN AGENTS -->
| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | Maturity | Recommendation | Notes |
|---|---|---|---|---|---|---|---|---|
<!-- END AGENTS -->

---

## <a name="tools-modules"></a>🛠️ Tools Modules

<!-- BEGIN TOOLS -->
| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | Maturity | Recommendation | Notes |
|---|---|---|---|---|---|---|---|---|
<!-- END TOOLS -->

---

## <a name="automation-modules"></a>⚙️ Automation Modules

<!-- BEGIN AUTOMATION -->
| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | Maturity | Recommendation | Notes |
|---|---|---|---|---|---|---|---|---|
<!-- END AUTOMATION -->

---

## <a name="services-modules"></a>🌐 Services Modules

<!-- BEGIN SERVICES -->
| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | Maturity | Recommendation | Notes |
|---|---|---|---|---|---|---|---|---|
<!-- END SERVICES -->

---

## <a name="integrations-modules"></a>🔌 Integrations Modules

<!-- BEGIN INTEGRATIONS -->
| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | Maturity | Recommendation | Notes |
|---|---|---|---|---|---|---|---|---|
<!-- END INTEGRATIONS -->

---

## <a name="cli-modules"></a>💻 CLI Modules

<!-- BEGIN CLI -->
| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | Maturity | Recommendation | Notes |
|---|---|---|---|---|---|---|---|---|
<!-- END CLI -->

---

## <a name="utilities-modules"></a>��️ Utilities Modules

<!-- BEGIN UTIL -->
| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | Maturity | Recommendation | Notes |
|---|---|---|---|---|---|---|---|---|
<!-- END UTIL -->

---

## <a name="backlog"></a>🚀 Backlog Tickets

| ID                              | Title                           | Owner | Pts | Emoji |
| ------------------------------- | ------------------------------- | ----- | --- | :---: |
| `PHASE2-MAP-AUTOGEN-001`        | Integrate auto‑mapper & CI step | A‑5   | 200 |   ♻️  |
| `COORD-ENUM-CONSOLIDATE-002`    | Unify coordination enums        | A‑4   | 150 |   ♻️  |
| `VALIDATION-UTILS-REFACTOR-003` | Drop legacy dict validation     | A‑3   | 250 |   ♻️  |
| `TASK-NEXUS-DEPRECATE-004`      | Retire file‑based TaskNexus     | A‑2   | 300 |   ⚠️  |

---

### Usage

* Run `python devtools/module_mapper.py > ai_docs/reports/module_map.md`
* CI gate fails if diff detected → **zero‑drift guarantee**.

---

> *Phase‑2 scanning continues (agents → cli). Doc expands automatically — no manual upkeep.* 💨
