# Dream.OS Project Research Report

**Date:** 2025-04-22  
**Compiled by:** agent_002  

## 1. Project Overview
Dream.OS is a platform for orchestrating autonomous agents (e.g., ChatGPT WebAgents, Cursor IDE workers, Supervisor) to collaborate on coding, analysis, and task execution. It leverages:
- Browser automation (Selenium) to interact with ChatGPT
- UI automation (pyautogui + pyperclip) in the Cursor IDE
- File‑based coordination via JSON blobs (LocalBlobChannel / AzureBlobChannel)
- A Supervisor agent (“Oria”) to dispatch tasks and aggregate results

## 2. Core Architecture & Directories
- **dream_mode/agents/**: Implements agent logic
  - `chatgpt_web_agent.py`: Scrapes ChatGPT, injects prompts, supports simulate mode
  - `cursor_worker.py`: Automates Cursor IDE task handling via pyautogui
  - `supervisor_agent.py`: Oria loads `human_directive.json`, pushes tasks, collects results
- **dream_mode/utils/**: Shared utilities (browser control, HTML parsing, task parsing, channel loader)
- **_agent_coordination/**: Swarm protocol definitions
  - `shared_mailboxes/`: mailbox JSON + `mailbox.schema.json`
  - `tasks/`: task list schema (`task_list.schema.json`), `research_report.md`
  - `onboarding/agent_###/`: onboarding kits + `start_prompt.md`
- **runtime/**: Live data stores
  - `human_directive.json`: Human‑provided directives (Oria reads)
  - `supervisor_results.json`: Aggregated results (Oria writes)
  - `local_blob/`: Tasks & results directories for LocalBlobChannel
- **assets/**: UI images for automation (`accept_button.png`, `spinner.png`)
- **Entry Points**
  - `run_dream_os.py`: Original one‑click launch for WebAgent + SwarmController
  - `run_dream_loop.py`: Unified entry for Supervisor, WebAgent (simulate/live), Cursor workers

## 3. Coordination Protocols & Schemas
- **Mailbox Schema**: `_agent_coordination/shared_mailboxes/mailbox.schema.json` (defines claim status, messages)
- **Task List Schema**: `_agent_coordination/tasks/task_list.schema.json` (defines `tasks[]` with `task_id`, `status`, `assigned_to`, etc.)
- **Onboarding**: Agents auto‑inject a `start_prompt.md` on first cycle (flag `onboarded`); optional reset via `RESET_ONBOARDING`

## 4. Multi‑Agent Loop
1. **Oria (Supervisor)** reads `runtime/human_directive.json`, dispatches new tasks into `local_blob/tasks/`
2. **ChatGPT WebAgent** (live or simulated) pulls tasks, generates structured responses, pushes back as new tasks or results
3. **Cursor Workers** pull tasks, automate Cursor IDE interactions, extract code via clipboard, push results
4. **Oria** pulls results, writes consolidated `runtime/supervisor_results.json`

## 5. Dependencies & Requirements
- Python 3.8+  
- `selenium`, `pyautogui`, `pyperclip`, `jsonschema` or `ajv` (for schema validation)  
- Cursor IDE installed & visible for UI automation  
- (Optional) Azure Storage for production C2 channel

## 6. Next Steps & Collaboration
- Finalize UI assets and image‑matching thresholds  
- Enhance error‑handling and retry strategies in `cursor_worker.py`  
- Develop a PyQt5 dashboard for real‑time monitoring  
- Coordinate with Agents 1, 3, and 4 by appending shared findings here  
- Schedule periodic research updates to keep all agents in sync

## 7. Detailed File Inventory
- `run_dream_os.py` (62 lines): original one‑click launcher for WebAgent + SwarmController.
- `run_dream_loop.py` (55 lines): unified loop coordinating Supervisor, ChatGPT (simulate/live), and Cursor workers.
- `dream_mode/agents/chatgpt_web_agent.py` (~240 lines): handles ChatGPT browsing, scraping, injection, and simulation modes.
- `dream_mode/agents/cursor_worker.py` (~76 lines): automates Cursor IDE interactions via pyautogui and clipboard extraction.
- `dream_mode/agents/supervisor_agent.py` (~74 lines): dispatches human directives and aggregates results into `supervisor_results.json`.
- `dream_mode/utils/` (10+ modules): browser control, HTML parsing, task parsing, and channel loader utilities.
- `dream_mode/swarm_controller.py` (~253 lines): legacy fleet orchestration for simultaneous Cursor instances.
- `dream_mode/task_nexus/task_nexus.py` (~137 lines): core atomic task queue with heartbeat and status management.
- `runtime/local_blob/` (tasks/ and results/): file‑based queues for inter‑agent messaging.

## 8. Master Task List Overview
- `master_task_list.json` (3,761 lines) holds the global task registry, currently tracking tasks across `PENDING`, `IN_PROGRESS`, and `COMPLETED` states.
- Managed by `TaskNexus`, which provides atomic reads/writes and agent heartbeat registration via `agent_registry.json`.

## 9. Coordination Notes
- **Agent002** should monitor `_agent_coordination/shared_mailboxes/mailbox_2.json` for collaboration inbox messages.
- Broadcast updates or research snippets by appending to the `messages` array in `mailbox_2.json`.
- Consider enabling heartbeat logging in `dream_mode/task_nexus/task_nexus.py` to visualize active agents via the PyQt dashboard.

---
*End of report.* 