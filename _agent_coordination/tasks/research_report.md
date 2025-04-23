# Dream.OS: Comprehensive Research Report

## 1. Architecture & Core Components

• **dream_mode/** – Orchestrates Cursor agents via BlobChannel (Azure or Local). Contains:
  - `SwarmController` (fleet management, routing, auto‑lore injection)
  - `cursor_dispatcher`, `cursor_worker`, `VirtualDesktopController`

• **_agent_coordination/** – Agent protocols and tooling:
  - **prompt_library/** – JSON‑driven prompts (autonomy, cleanup, testing)
  - **tasks/** – Consolidated pending and directive task lists
  - **tools/compile_lore.py** – One‑shot & style‑driven lore compiler (Jinja2 + YAML mapping)

• **runtime/** – Live task queue (`task_list.json`) and generated lore logs (`dream_logs/lore/`).

• **templates/** – Jinja templates for raw & Devlog‑style lore (e.g. `devlog_lore.j2`).

## 2. Current Task Lists

1. **Detailed Pending Tasks** (`remaining_tasks.json`) – 4 PENDING tasks:
   • `dev_create_echo_agent_001`: scaffold EchoAgent
   • `infra_build_code_applicator_001`
   • `enable_code_apply_in_cursor_agent_001`
   • `build_feedback_mailbox_writer_001`

2. **Directive‑to‑System Execution Roadmap** (`directive_execution_tasks.json`) – 19 phased tasks across:
   - Core Loop Autonomy (5 tasks)
   - Cursor Fleet (4 tasks)
   - Thea as Strategist (3 tasks)
   - UI & Show the World (4 tasks)
   - Bonus Directives (3 tasks)

## 3. Open Issues & TODOs

Top TODO flags across the codebase (non‑exhaustive):
- `main.py` / `main_copy.py`: implement MainCopy class.
- `planner_agent.py`: refine dispatch logic, context augmentation.
- `thea_auto_planner.py`: GPT‑driven directive analysis.
- UI (`fragment_forge_tab.py`): add status dialogs, error handling.
- Tests: missing coverage for failure handling, dependency flow, thread safety.

## 4. Test Suite Health

- Syntax and import errors in `tests/core/gui/test_main_window_state.py` corrected.
- `compile_lore.py` tests now pass with Devlog style.
- Remaining TODOs in tests indicate areas for expanded coverage.

## 5. Recommended Coordination Plan

We'll work with **three agent teams** and synchronize via **two master lists**:

| Team            | Task List Source                       | Responsibilities                                  |
|-----------------|----------------------------------------|--------------------------------------------------|
| **CoreUnit**    | `remaining_tasks.json`                 | Finish EchoAgent, CodeApplicator, mailbox writer |
| **Orchestration**| `directive_execution_tasks.json` (Phase 1 & 2) | Build SupervisorOria, heartbeat + fleet scaling  |
| **StrategistUI** | `directive_execution_tasks.json` (Phase 3 & 4) | Thea loop, UI dashboard, Devlog/Discord pushes    |

**Synchronization points**:
1. Weekly merge of progress into `master_task_list.json`.  
2. CI‑triggered Devlog generation validating timeline.  
3. Shared dashboard displaying `agent_stats.json` + pending tasks.

---

*Report generated on:* {{date}} 