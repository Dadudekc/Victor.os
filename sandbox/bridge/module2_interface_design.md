# Module 2: Cursor->GPT Feedback Telemetry Loop - Design

**Agent:** Hexmire (Agent-3)

## Objective
Parse the results/status produced by Module 1 (simulating Cursor tool outputs) and format them into a standardized feedback payload for a simulated GPT.

## Input Interface (from Module 1 - JSON)
```json
// Example Success (edit_file)
{
  "status": "success",
  "message": "Simulated edit applied.",
  "correlation_id": "test-edit-001"
}

// Example Success (codebase_search)
{
  "status": "success",
  "results": ["Simulated search result 1", "Simulated result 2"],
  "correlation_id": "test-search-003"
}

// Example Error
{
  "correlation_id": "test-invalid-cmd-00X",
  "status": "error",
  "message": "Unsupported command: invalid_command"
}
```

## Output Interface (to GPT - JSON)
```json
{
  "correlation_id": "<original_correlation_id>",
  "status": "success | error", // Mirrored from input or determined by parsing
  "result_type": "edit_file | run_terminal | codebase_search | read_file | grep_search | error", // Inferred type
  "data": { 
    // Contents depend on status and result_type
    // Success example (search): "results": ["..."], "message": "Optional message"
    // Error example: "error_message": "..."
  }
}
```

## Error Handling
- Malformed input JSON: Log error, produce error output payload.
- Missing expected fields (`status`, `correlation_id`): Log error, attempt partial processing or produce error output.

## Core Component
`sandbox/bridge/cursor_gpt_feedback.py` 