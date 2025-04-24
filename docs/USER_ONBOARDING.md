# Dream.OS Quickstart Guide

## Overview
Dream.OS orchestrates Cursor‐based agents under a ChatGPT Web UI loop:
- **WebAgent** scrapes JSON directives from your ChatGPT conversation.
- **SwarmController** launches a fleet of Cursor agents (GUI + headless) and routes tasks/results.
- **LocalBlobChannel** (default) or AzureBlobChannel handles task exchange.
- **TaskNexus** centralizes tasks; **StatsLoggingHook** emits periodic snapshots.

## Prerequisites
- Python 3.8+ and a modern Chrome browser.
- Clone the repo and install:
  ```bash
  git clone <repo-url> && cd Dream.os
  pip install -r requirements.txt
  ```

## Run in Local Mode (one line)
```bash
export USE_LOCAL_BLOB=1        # Windows PowerShell: $Env:USE_LOCAL_BLOB='1'
python run_dream_os.py
```
This single command starts both WebAgent and SwarmController in local mode.

## Manual Run
**WebAgent (Terminal 1):**
```bash
export USE_LOCAL_BLOB=1
python -m dream_mode.agents.chatgpt_web_agent
```
**SwarmController (Terminal 2):**
```bash
export USE_LOCAL_BLOB=1
python -m dream_mode.swarm_controller --fleet-size 3
```

## Passing Directives
Type a JSON snippet into ChatGPT:
```json
{"task_id":"unique-id","command":"inspect dream_mode/utils.py and report functions"}
```
- **WebAgent** detects it and pushes to the channel.
- **SwarmController** claims, executes, and pushes results back.
- **WebAgent** injects results into your ChatGPT session.

## Key Paths & Files
- `runtime/task_list.json` – live task statuses
- `_agent_coordination/tasks/` – master task manifest & schemas
- `dream_mode/` – agent implementations & channels
- `dream_logs/feedback/` – automated failure analyses

## GUI Dashboard

To visually monitor and control the agent swarm, launch the PyQt5 Dashboard:

```bash
# Install GUI dependencies
pip install pyqt5 pyautogui pynput
# Run the dashboard
python dashboard.py
```

The Dashboard provides:
- **Mailboxes**: shows online status, owner, and message count for each agent mailbox.
- **Tasks**: aggregated view across all task lists, sortable and color-coded by status; claim tasks directly.
- **Messaging**: send and view raw messages into any mailbox.
- **Templates**: browse and load JSON-schema templates for prompts.
- **Agents**: configure click spots for each of 8 agents; settings persist in `_agent_coordination/config/agent_coords.json`.
- **Actions**: load user prompts, send them, and accept/reject changes via GUI buttons.

### Config & Data Paths
- `_agent_coordination/config/agent_coords.json` – saved click coordinates for agent input spots
- `_agent_coordination/user_prompts/` – custom prompt files to drive the swarm via the Actions tab

## Tips & Support
- Console logs include heartbeat snapshots every interval (default 60s).
- Adjust stats interval with `--stats-interval N` or `STATS_INTERVAL=N`.
- Ensure Chrome is installed and configured for WebAgent.
- For Azure C2 use `AZURE_STORAGE_CONNECTION_STRING`/`AZURE_SAS_TOKEN`.
- Questions or issues? Open an issue in the repo or chat with the team.

## Proposals & Discovery
To propose improvements or fixes during your work, prefix your message with `/proposal:` followed by your suggestion, and send it to any agent's mailbox file (e.g., `_agent_coordination/shared_mailboxes/mailbox_<id>.json`).

If you discover a new issue or TODO while completing tasks, append it to `D:/Dream.os/_agent_coordination/tasks/complete/discovered_tasks.json` in the following JSON format:
```json
{
  "file": "<path/to/file>",
  "line_range": [start_line, end_line],
  "category": "<bug|enhancement|cleanup>",
  "description": "Description of the issue or improvement",
  "discovered_by": "<your_agent_id>"
}
```

Enjoy building with Dream.OS! 🚀