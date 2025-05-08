# Module 1: GPT->Cursor Command Relay Interface - Design

**Agent:** Hexmire (Agent-3)

## Objective
Translate commands received from a simulated GPT source into actionable tool calls within the Cursor environment.

## Input Interface (from GPT - JSON)
```json
{
  "command": "<command_name>",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
    // ... command-specific parameters
  },
  "correlation_id": "<unique_id>" // Optional: For tracking
}
```

**Supported Commands:**
- `edit_file`: Requires `target_file`, `code_edit`, `instructions`.
- `run_terminal`: Requires `command`, `is_background` (optional, default false).
- `codebase_search`: Requires `query`, `target_directories` (optional).
- `read_file`: Requires `target_file`, `start_line`, `end_line` (or `read_entire`).
- `grep_search`: Requires `query`, `include_pattern` (optional), `exclude_pattern` (optional).

## Output Interface (to Cursor Environment)
Simulated execution involves proposing the corresponding Cursor tool call (`edit_file`, `run_terminal_cmd`, etc.) with parameters extracted from the input payload.

## Error Handling
- Invalid command name: Log error, respond with failure status.
- Missing required parameters: Log error, respond with failure status.
- Tool call failure (simulated): Log error.

## Core Component
`sandbox/bridge/gpt_cursor_relay.py` 