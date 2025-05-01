# Dream.OS Runtime Directory

This directory contains files generated or used by Dream.OS during its operation. It should generally be excluded from version control (via `.gitignore`), except for essential configuration or empty directory markers (`.keep` files).

## Standard Structure (Current & Target)

This section describes the standard runtime directory structure. Some directories might need to be created manually or by system initialization if missing.

- **/bus**: State/cache related to the AgentBus (if file-based).
- **/cache**: **(Standard, May Be Missing)** For regeneratable cache data.
- **/config**: Runtime-specific configurations (e.g., generated coordinates, dynamic settings).
- **/cursor**: Artifacts related to Cursor automation.
- **/cursor_processed**: Records or outputs from processed Cursor tasks.
- **/cursor_queue**: Input queue for Cursor tasks.
- **/logs**: Central directory for all operational logs (JSONL, text logs, etc.).
- **/mailboxes**: Default location for file-based agent mailboxes.
- **/memory**: Persisted memory segments managed by `UnifiedMemoryManager`.
- **/queues**: General file-based queues (if not using specific mailboxes).
- **/schemas**: **(Standard, May Be Missing)** Runtime validation schemas (e.g., for task board, events).
- **/state**: General persisted state files for the system or agents.
- **/temp**: **(Current: `temp/`, Standard: `tmp/`)** Temporary files used during processing (should be cleaned up automatically or periodically). Requires rename to `tmp/` for standardization.
- **/local_blob**: **(Likely state/cache)** Local blob storage cache/state.

## Key Files (Observed)

- `task_board.json`: Current status of agent tasks.
- `master_task_list.json`: Persistent store of tasks (may be primary).
- `governance_memory.jsonl`: Log/memory for governance agent.
- `structured_events.jsonl`: Log of structured system events.
- `.gitignore`: Rules specific to ignoring runtime contents (should reference this file).
- `README.md`: This file.

*Note: Other files like `task_list.json`, `human_directive.json` were observed but their necessity is under review.*
