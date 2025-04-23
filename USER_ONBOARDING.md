# Dream.OS Quickstart Guide

## Overview
Dream.OS orchestrates Cursor‐based agents under a ChatGPT Web UI loop:
- **WebAgent** scrapes JSON directives from your ChatGPT conversation.
- **SwarmController** launches a fleet of Cursor agents (GUI + headless) and routes tasks/results.
- **LocalBlobChannel** (default) or AzureBlobChannel handles task exchange.
- **TaskNexus** centralizes tasks; **StatsLoggingHook** emits periodic snapshots.

## Prerequisites
- Python 3.8+ and a modern Chrome browser.
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
**WebAgent (Terminal 1):**
```bash
export USE_LOCAL_BLOB=1
python -m dream_mode.agents.chatgpt_web_agent
```
**SwarmController (Terminal 2):**
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
- `runtime/task_list.json` – live task statuses
- `_agent_coordination/tasks/` – master task manifest & schemas
- `dream_mode/` – agent implementations & channels
- `dream_logs/feedback/` – automated failure analyses

## Tips & Support
- Console logs include heartbeat snapshots every interval (default 60s).
- Adjust stats interval with `--stats-interval N` or `STATS_INTERVAL=N`.
- Ensure Chrome is installed and configured for WebAgent.
- For Azure C2 use `AZURE_STORAGE_CONNECTION_STRING`/`AZURE_SAS_TOKEN`.
- Questions or issues? Open an issue in the repo or chat with the team.

Enjoy building with Dream.OS! 🚀