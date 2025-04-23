# Dream.OS User Onboarding

Welcome to the Dream.OS multi‑agent swarm control system! This guide will walk you through:

1. Environment setup
2. Configuration & credentials
3. Running the ChatGPT WebAgent
4. Running the SwarmController (Cursor fleet)
5. Passing directives and commands
6. One‑Click Launch Script

---

## 1. Prerequisites

- Python 3.8+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- A modern Chrome browser (for ChatGPT WebAgent)
- Azure Storage account (optional for live C2)

---

## 2. Configuration & Credentials

### ChatGPT WebAgent

1. Create `dream_mode/config/dream_mode_config.json` with:
   ```json
   {
     "agents": {
       "agent1": {"conversation_url": "https://chat.openai.com/chat/..."}
     }
   }
   ```
2. Set environment variables for C2 channel:
   ```bash
   export AZURE_STORAGE_CONNECTION_STRING="<your-connection-string>"
   export AZURE_SAS_TOKEN="<your-sas-token>"
   export C2_CONTAINER="dream-os-c2"
   ```
3. (Optional) For local testing without Azure:
   - The channel will use mocks if `azure-storage-blob` is not installed.

### JSON Schemas & Examples

Dream.OS defines JSON schemas to validate core coordination files:

- Mailbox schema: `_agent_coordination/shared_mailboxes/mailbox.schema.json`
- Task list schema: `_agent_coordination/tasks/task_list.schema.json`

Example payloads for Phase 1 onboarding are available under `_agent_coordination/onboarding/agent_002/`:

- `mailbox_example.json`
- `task_list_example.json`
- `phase_1_output.json`

Validate via `ajv` or Python's `jsonschema` package:

```bash
ajv validate -s _agent_coordination/shared_mailboxes/mailbox.schema.json \
  -d _agent_coordination/onboarding/agent_002/mailbox_example.json

ajv validate -s _agent_coordination/tasks/task_list.schema.json \
  -d _agent_coordination/onboarding/agent_002/task_list_example.json
```

---

## 2.5 One‑Click Launch Script

We provide a helper script `run_dream_os.py` that starts both the ChatGPT WebAgent and the SwarmController in local mode. Simply:

```bash
python run_dream_os.py
```

This will:
- Set `USE_LOCAL_BLOB=1`
- Launch the WebAgent (opens your ChatGPT browser session)
- Launch the SwarmController (runs Cursor agents locally)

Press `Ctrl+C` to terminate both.

---

## 3. Running ChatGPT WebAgent

This agent scrapes your ChatGPT conversation, parses tasks, and pushes them to the C2 channel.

```bash
# Use module mode so `dream_mode` is on PYTHONPATH
python -m dream_mode.agents.chatgpt_web_agent
```

**Local mode:** to run without Azure, enable LocalBlobChannel:
```bash
export USE_LOCAL_BLOB=1   # Windows PowerShell: $Env:USE_LOCAL_BLOB='1'
python -m dream_mode.agents.chatgpt_web_agent
```

It will open a browser window, navigate to your ChatGPT conversation, and monitor for new replies.

---

## 4. Running SwarmController

This controller launches a fleet of Cursor instances (visible UI) and headless workers.

```bash
# Use module mode so `dream_mode` is on PYTHONPATH
python -m dream_mode.swarm_controller
```

**Local mode:** to run without Azure, enable LocalBlobChannel:
```bash
export USE_LOCAL_BLOB=1   # Windows PowerShell: $Env:USE_LOCAL_BLOB='1'
python -m dream_mode.swarm_controller
```

It will tile visible Cursor windows, start background workers, and route tasks/results automatically.

---

## 5. Passing Directives

1. **You**: Type a JSON‑structured prompt into ChatGPT, e.g.:
   ```json
   {
     "task_id": "task-123",
     "command": "analyze file core/gui/main_window.py and suggest improvements"
   }
   ```
2. **WebAgent**: Scrapes new assistant replies, extracts `task_id` and `command`, and pushes them to Azure.
3. **SwarmController**: Picks up tasks, fans out to Cursor agents, runs automation, and pushes results back.
4. **WebAgent**: Pulls results and injects them back into ChatGPT as new messages.

**Note**: Always include a unique `task_id` in your prompt JSON to track and avoid duplicates.

---

### Troubleshooting

- Check logs in the console for errors.
- Verify that `AZURE_STORAGE_*` env vars are set correctly.
- Make sure your ChatGPT conversation URL is correct and that you are logged in.

---

Enjoy your autonomous Dream.OS swarm! 🚀 