# GPT Command Interface Specification

This document outlines the JSON structure for commands sent from a GPT-based agent to the Cursor Bridge for execution.

## Schema

Commands MUST adhere to the `bridge/schemas/gpt_command_schema.json` schema.

Key fields:
- `request_id` (string, uuid): Unique ID for tracing.
- `timestamp` (string, date-time): ISO 8601 timestamp of command generation.
- `command_type` (string, enum): The specific Cursor action requested. See below for supported types.
- `parameters` (object): A dictionary containing the arguments required for the `command_type`.

## Supported Command Types and Required Parameters

Validation of required parameters within the `parameters` object occurs at runtime based on the `command_type`.

1.  **`edit_file`**: Modifies or creates a file.
    - Required `parameters`: `target_file`, `code_edit`, `instructions`
2.  **`run_terminal`**: Executes a shell command.
    - Required `parameters`: `command`, `is_background`
3.  **`codebase_search`**: Performs semantic code search.
    - Required `parameters`: `query`
    - Optional `parameters`: `target_directories`
4.  **`file_search`**: Fuzzy finds files by path.
    - Required `parameters`: `query`
5.  **`read_file`**: Reads content from a file.
    - Required `parameters`: `target_file`, `start_line_one_indexed`, `end_line_one_indexed_inclusive`
    - Optional `parameters`: `should_read_entire_file`
6.  **`list_dir`**: Lists directory contents.
    - Required `parameters`: `relative_workspace_path`
7.  **`grep_search`**: Performs regex-based text search.
    - Required `parameters`: `query`
    - Optional `parameters`: `case_sensitive`, `include_pattern`, `exclude_pattern`

## Security Considerations

- All inputs, especially `code_edit` and `command`, MUST be treated as potentially untrusted.
- The bridge implementation MUST include sanitization and validation steps before executing commands.
- Execution environments (e.g., terminal commands) should be sandboxed or restricted where possible. 