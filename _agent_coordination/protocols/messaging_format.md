# Dream.OS Messaging & Format Protocols

This document outlines the standard formats and locations for communication between agents, core services, and external interfaces (like Cursor/ChatGPT bridges) within Dream.OS.

**Version:** 1.0
**Last Updated:** $(date --iso-8601=seconds) # Placeholder - Should be updated manually or via script

## Core Principles:

- **Structured Data:** Use JSON for machine-to-machine communication (agent commands, task lists, structured results).
- **Human Readability:** Use Markdown for reports, logs, and summaries intended for human review.
- **Dynamic Generation:** Use Jinja2 templates (`.j2`) for constructing complex prompts or messages.
- **Clear Channels:** Utilize designated **absolute file paths** for specific communication flows, rooted at the project base (e.g., `/d:/Dream.os/`).

## Standard File Formats & Usage:

| Direction/Purpose                  | Format   | Extension | Canonical Path Pattern                               | Reason                                                  |
|-----------------------------------|----------|-----------|----------------------------------------------------|---------------------------------------------------------|
| Agent ↔ Agent (Task/Status)     | `JSON`   | `.json`   | `/d:/Dream.os/runtime/AgentX/inbox/task_*.json`    | Machine-readable task/command structure                 |
| Agent → Agent (Message/Result)    | `JSON`   | `.json`   | `/d:/Dream.os/runtime/AgentX/outbox/msg_*.json`    | Structured output/status updates                        |
| Prompt Template                   | `Jinja`  | `.j2`     | `/d:/Dream.os/templates/*.j2`                      | Allows structured + dynamic prompt templating           |
| Rendered Prompt → Cursor          | `Text`   | `.txt`    | `/d:/Dream.os/temp/cursor_input.txt`               | Final rendered text ready for processing by Cursor/LLM |
| Cursor → System (Result/Command) | `JSON`   | `.json`   | `/d:/Dream.os/temp/cursor_output.json`             | Enables structured feedback/commands from Cursor bridge |
| System State (General)            | `JSON`   | `.json`   | `/d:/Dream.os/temp/*.json` or `/d:/Dream.os/runtime/AgentX/*.json` | General state persistence                         |
| Human-Facing Report/Log           | `Markdown`| `.md`     | `/d:/Dream.os/analysis/*.md` or `/d:/Dream.os/logs/*.md` | Human-readable summaries, proposals, decisions          |
| Governance Log                    | `JSONL`  | `.jsonl`  | `/d:/Dream.os/governance_memory.jsonl`             | Append-only log of significant system events          |
| Agent Reflection Log              | `Markdown`| `.md`     | `/d:/Dream.os/_agent_coordination/*/reflection/*.md` | Human-readable agent self-reflection logs             |
| Supervisor State                  | `JSON`   | `.json`   | `/d:/Dream.os/runtime/supervisor_state.json`       | Persistent state for the Supervisor                   |

## File-Based Message Bus (`/d:/Dream.os/temp/`):

The `/d:/Dream.os/temp/` directory serves as a primary low-level message bus, particularly for interfacing with external processes or the Cursor bridge.

- **`/d:/Dream.os/temp/cursor_input.txt`**: 
    - **Format:** Plain Text (often Jinja-rendered output).
    - **Written By:** `PromptStagingService` (or other components preparing prompts).
    - **Read By:** External process monitoring for Cursor/LLM input.
    - **Purpose:** Stage the exact text prompt for the next LLM interaction.
- **`/d:/Dream.os/temp/cursor_output.json`**: 
    - **Format:** JSON.
    - **Written By:** External process representing Cursor/LLM output.
    - **Read By:** `PromptStagingService` (`fetch_cursor_response`), dispatchers, routers.
    - **Purpose:** Receive structured commands, results, or data back from the LLM interaction.

## Agent Runtime Communication (`/d:/Dream.os/runtime/AgentX/`):

Each agent instance typically operates within its `/d:/Dream.os/runtime/AgentX/` directory.

- **`/d:/Dream.os/runtime/AgentX/inbox/`**: Contains incoming messages or task definitions, usually as `.json` files.
- **`/d:/Dream.os/runtime/AgentX/outbox/`**: Contains outgoing messages, results, or status updates, usually as `.json` files, ready for pickup by the supervisor or other agents.

## Notes:

- **Atomicity:** Assume file writes are generally atomic for simplicity, but be mindful of potential race conditions in high-concurrency scenarios (consider file locking or queueing systems if needed later).
- **Cleanup:** Processes reading from message files (e.g., `/d:/Dream.os/temp/cursor_output.json`, `/d:/Dream.os/runtime/AgentX/outbox/msg_*.json`) should ideally delete or archive the file after successful processing to prevent reprocessing.
- **Error Handling:** Implement robust error handling (e.g., `try...except` blocks) when reading/writing/parsing these files.

## Supported Message Types

This section documents specific message structures used for inter-agent communication or triggering actions via the event bus or mailbox system.

### GENERATE_TASK_SEQUENCE

Used to instruct a planning-capable agent to break down a high-level goal into a list of executable tasks.

#### Structure

```json
{
  "type": "GENERATE_TASK_SEQUENCE",
  "source_id": "Agent_0",  // the initiator
  "target_id": "PlanningAgent", // or use broadcast
  "data": {
    "task_id": "plan-001",
    "params": {
      "goal": "Refactor the legacy utils directory and remove unused code."
    }
  }
}
```

#### Expected Response

A `TASK_COMPLETED` event with a `results` payload containing a JSON list of tasks:

```json
{
  "type": "TASK_COMPLETED",
  "source_id": "PlanningAgent",
  "target_id": "TaskExecutorAgent",
  "data": {
    "correlation_id": "plan-001",
    "task_id": "plan-001",
    "results": [
      {
        "task_id": "task-001",
        "action": "REFACTOR_IMPORTS",
        "params": { "target_file": "core/utils/legacy_parser.py" },
        "target_agent": "RefactorAgent",
        "status": "PENDING",
        "priority": 3,
        "depends_on": []
      },
      {
        "task_id": "task-002",
        "action": "REMOVE_DEAD_CODE",
        "params": { "target_directory": "agents/social/" },
        "target_agent": "RefactorAgent",
        "status": "PENDING",
        "priority": 2,
        "depends_on": ["task-001"]
      }
    ]
  }
}
```

#### Notes

- Tasks must conform to the global `task_list.json` schema.
- Planning agents may inject additional metadata or dependencies if needed.
- This message type enables agents to recursively expand goals into sub-actions.

# Messaging Format Protocol

*This file defines the standard formats for messages exchanged between agents, primarily via shared mailboxes in this version.*

*(Placeholder - Content to be added based on system design)*

---

## 1. Shared Mailbox Message Structure (`mailbox_N.json`)

Each mailbox file (`mailbox_1.json`, etc.) has the following top-level structure:

```json
{
  "status": "online" | "offline" | "idle" | "busy",
  "assigned_agent_id": "<agent_id>" | null,
  "last_seen_utc": "<iso_timestamp>",
  "messages": [
    // Array of message objects (see below)
  ],
  "processed_message_ids": [
    "<message_id_1>",
    "<message_id_2>",
    ...
  ]
}
```

## 2. Individual Message Object (within `messages[]`)

Each object within the `messages` array follows this structure:

```json
{
  "message_id": "<unique_uuid>", // Automatically generated upon sending
  "sender_agent_id": "<agent_id>" | "System" | "User",
  "timestamp_dispatched": "<iso_timestamp>",
  "command": "<action_verb>", // e.g., "refactor_file", "run_test", "request_status"
  "params": {
    // Key-value pairs specific to the command
    // Example: "target_file": "path/to/file.py"
  },
  "task_id": "<optional_tracking_id>" // Optional: For linking to a master task list
}
```

## 3. Status Reporting Structure (`completed_tasks.json`)

This file is an **append-only JSON Lines** file. Each line is a complete JSON object representing a task outcome:

```json
// Line 1
{"message_id": "msg_uuid_1", "task_id": "task_abc", "agent_id": "RefactorAgent", "status": "COMPLETED", "timestamp": "<iso_timestamp>", "output": {"files_changed": 1, "details": "..."}, "error_details": null}
// Line 2
{"message_id": "msg_uuid_2", "task_id": "task_def", "agent_id": "TestAgent", "status": "FAILED", "timestamp": "<iso_timestamp>", "output": null, "error_details": {"code": "AssertionError", "message": "Test failed..."}}
// ... more lines
```

*Key Fields:*
- `message_id`: The ID of the message that triggered the task.
- `task_id`: Optional ID linking to a broader task.
- `agent_id`: The agent reporting the status.
- `status`: `COMPLETED` or `FAILED`.
- `timestamp`: Time of completion/failure.
- `output`: JSON object with successful execution details (optional).
- `error_details`: JSON object with failure reason (only if `status` is `FAILED`).

---

*(Further details on specific commands and parameters should be documented elsewhere, potentially linked from the command registry or specific agent docs.)* 