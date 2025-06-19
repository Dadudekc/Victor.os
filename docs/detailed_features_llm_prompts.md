# Dream.OS Feature Analysis and LLM Prompt Guide

## Overview
Dream.OS is a multi-agent system designed for autonomous software development. It combines a Discord bot interface, a message queue for coordination, and various agents capable of scanning code, managing tasks, and orchestrating workflows. The architecture emphasizes event-driven operations, asynchronous tools, and persistent documentation.

## Major Features

### Event System
- **180 second cycle loop** controlling global operations.
- **5 second tool chunks** for executing actions within the cycle.
- **Active project board** to track tasks, blockers, and resources.
- **task_board.json** stored under `runtime/central_tasks/` holds the shared backlog for all agents.
- **Orchestrator cycle** triggers start/end events and aggregates metrics from agents.

### Agent Framework
- **BaseAgent & AutonomousLoop** manage message processing, task claiming, and error handling.
- **ProjectBoardManager** stores tasks in JSON files (`task_backlog.json`, `task_ready_queue.json`, `working_tasks.json`, `completed_tasks.json`).
- **AgentBus** provides a message broker for inter-agent events (see `agent_bus_events.md`).
- **ImprovementValidator** ensures tasks lead to meaningful progress.
- Specialized roles such as **ORCHESTRATOR**, **VALIDATOR**, and **JARVIS** coordinate complex flows.
- Agents maintain `devlog.md` and `inbox.json` to record progress and track claimed tasks.

### Communication & Routing
- Agents exchange JSON or Markdown messages through file-based mailboxes (`runtime/agent_mailboxes/Agent-<n>/`).
- GUI interactions with ChatGPT occur via PyAutoGUI through the Cursor interface, following the [Message Routing Protocol](../MESSAGE_ROUTING_PROTOCOL.md).
- Inbox messages trigger LLM prompts only when intentional, maintaining separation of concerns.
- Each mailbox is a JSON array of `{"type": str, "payload": dict}` messages cleared after processing.
- The AgentBus relays system events; simple setups can use an append-only JSONL file under `runtime/bus/`.

### Semantic Scanner
- `ProjectScanner` analyzes code, producing `project_scan_report.md` and structured context files for AI assistants.
- Supports directory- or language-based output splitting, caching, and exclusion of large or irrelevant files (see `README-project-scanner.md`).
- Scans each file with Python AST to record functions, classes, imports, and generates reports under `runtime/reports/`.

### Task Management & Orchestration
- **TaskManager** schedules tasks, manages resources, and tracks progress.
- **Orchestrator** coordinates agent lifecycle, distribution, and monitoring.
- Tasks include fields like `task_id`, `name`, `description`, `status`, `priority`, and `history` with timestamps.
- A CLI in `project_board_manager.py` supports adding, claiming, and completing tasks from the command line.
- Agents publish heartbeat messages and may maintain a local task cache for resilience (see `agent_loop_resilience_v1.md`).

### Meetings and Collaboration
- The [Agent Meeting System](architecture/designs/architecture/agent_meeting_system.md) defines protocols for asynchronous meetings:
  - `runtime/agent_comms/meetings/<id>/` stores agendas, messages, and participant lists.
  - Agents use `meeting.create`, `meeting.join`, `meeting.post_message`, and `meeting.vote` capabilities.
  - Facilitator agents or events manage voting phases and state transitions.

- `manifest.json` records meeting metadata and `messages/` holds `msg_<timestamp>_<agent>.json` files.
### Additional Utilities
- **Auto-Prompt Generator**: reads YAML definitions and outputs prompt files for agents (`spin_offs/auto_prompt_generator/`).
- **Self-Healing Swarm Template**: provides a minimal setup for running agents on the `StableAutonomousLoop`.
- **DevlogAgent** monitors agents and appends entries to `runtime/devlogs/` for audit trails.
- Extensive documentation in `docs/` and `ai_docs/` covering architecture, business logic, and best practices.

### Safety, Alignment & Empathy
- **Guardian Directives** establish baseline ethics and safety rules for all agents.
- **Self-Regulation Hooks** define thresholds for resource usage and behaviors such as recovery or human guidance.
- **Digital Empathy Logs** capture reflection prompts in `runtime/logs/empathy/`.
- **Empathy Scoring** measures emotional intelligence, response quality, and user satisfaction.

### Response Validation & Monitoring
- **Agent Response Validation** checks that outputs meet quality standards before tasks are marked complete.
- **DevlogAgent** writes significant events to `runtime/devlogs/`, providing project visibility.
- **Resilience Hooks** manage episode state, error thresholds, and recovery attempts.

### GUI Automation Interface
- **GUI Automation Module** uses PyAutoGUI to control desktop applications via scripts.
- **TaskTrigger** starts automation sequences in response to events or schedules.
- Automation tasks are defined in YAML/JSON files parsed by the GUI module.
- Configuration files make automation routines easy to extend and customize.

## LLM Prompt Series
Use the following prompts to generate a simplified Dream.OS-like system.

1. **Architecture Summary Prompt**
   ```
   You are designing a multi-agent platform inspired by Dream.OS. Summarize the key components: event loop, message queue, agent bus, project board manager, semantic scanner, and orchestrator. Include how a Discord bot integrates with the system.
   ```

2. **Base Agent Loop Prompt**
   ```
   Create a Python class `AutonomousLoop` that:
   - Retrieves messages from a mailbox directory.
   - Claims tasks from a `ProjectBoardManager` if available.
   - Executes tasks in 180 second cycles, running tools in 5 second chunks.
   - Reports progress via an `AgentBus` and handles blockers or errors gracefully.
   ```

3. **Task Management Rules Prompt**
   ```
   Implement task claim rules:
   - Only tasks with status `PENDING` in `task_ready_queue.json` can be claimed.
   - Validate dependencies before starting a task.
   - Prioritize tasks by `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
   - Ensure atomic updates when multiple agents write to task files.
   ```

4. **Message Routing Prompt**
   ```
   Describe the separation between agent inbox communication and GUI-based ChatGPT prompts. Provide functions to read inbox messages, generate intentional LLM prompts, and log responses.
   ```

5. **Meeting System Prompt**
   ```
   Outline a meeting subsystem where agents create meetings, post proposals, comment, vote, and close meetings. Use file-based storage under `runtime/agent_comms/meetings/` with schemas for message types and meeting metadata.
   ```

6. **Semantic Scanner Prompt**
   ```
   Generate a script `ProjectScanner` that scans a project directory, outputs a markdown report of modules and dependencies, splits context by directory, and caches file hashes to speed up subsequent scans.
   ```

7. **Resilience & Heartbeat Prompt**
   ```
   Design a heartbeat mechanism where each agent periodically writes a JSONL entry with `agent_id`, `timestamp_utc`, and `current_task_id`. Include a local task cache fallback if the main task files are unavailable.
   ```

These prompts build upon the repository's documentation to help an LLM reproduce Dream.OS's major capabilities.


## Lean Implementation Guide
Follow these steps to recreate a minimal Dream.OS setup in a fresh repository:

1. **Create Runtime Directories**
   - `runtime/central_tasks/` for `task_board.json` and related logs.
   - `runtime/agent_mailboxes/Agent-<n>/` for each agent's `inbox.json` and `devlog.md`.
   - `runtime/bus/` for `events.jsonl` if using a file-based AgentBus.

2. **Implement ProjectBoardManager**
   - Load tasks from `task_board.json`.
   - Provide `add_task`, `claim_task`, `update_task`, and `complete_task` methods.
   - Use file locks to avoid concurrent write issues.

3. **Build BaseAgent and AutonomousLoop**
   - Poll the agent mailbox every cycle.
   - Claim tasks from the ProjectBoardManager.
   - Execute tasks and append progress to `devlog.md`.
   - Publish status events to the AgentBus.

4. **Wire Up the Discord Bot**
   - Forward user commands to the AgentBus as events.
   - Optionally expose a CLI that mirrors the bot for local testing.

5. **Provide Support Scripts**
   - `ProjectScanner` for context generation.
   - `TaskTrigger` for launching GUI automation sequences.
   - Heartbeat publisher to write `runtime/logs/agent_heartbeats.jsonl`.

This guide, combined with the prompts above, allows an LLM to recreate a lean prototype of Dream.OS without guessing the underlying logic.
