# `safe_edit_json_list.py` CLI Tool

This command-line tool provides a safe mechanism for modifying JSON files that contain a top-level list of objects. It ensures concurrency safety using file locks and atomicity using temporary files and renaming, preventing data corruption during writes.

## Features

*   **Atomic Operations:** Add, remove, or update items in a JSON list without risking data loss if the script is interrupted.
*   **Concurrency Safe:** Uses file locking (`.lock` files) to prevent race conditions when multiple processes might try to modify the same file simultaneously (requires `filelock` library).
*   **Targeted Modifications:** Identifies items to remove or update based on a specified ID key and value.
*   **Schema Validation:** Optionally validates the entire modified list against a provided JSON schema before writing, ensuring data integrity.
*   **Robust Error Handling:** Provides clear error messages and exits with non-zero status codes on failure.

## Requirements

*   Python 3.x
*   `click` library (`pip install click`)
*   `filelock` library (optional, for full concurrency safety - `pip install filelock`)
*   `jsonschema` library (optional, for schema validation - `pip install jsonschema`)

## Usage

```bash
python src/dreamos/cli/safe_edit_json_list.py --target-file <path_to_json> --action <add|remove|update> [options]
```

### Arguments

*   `--target-file` (Required): Path to the target JSON list file. Must exist and be readable/writable.
*   `--action` (Required): The operation to perform:
    *   `add`: Appends a new item to the list.
    *   `remove`: Removes an item from the list based on its ID.
    *   `update`: Modifies an existing item in the list based on its ID.

### Options

*   `--item-id-key` (Default: `task_id`): The key within each JSON object in the list that serves as the unique identifier.
*   `--item-id`: The specific ID value of the item to target for `remove` or `update` actions. (Required for `remove`/`update`).
*   `--item-data`: A JSON string representing the data for the item.
    *   For `add`: The full JSON object to append.
    *   For `update`: A JSON object containing the key-value pairs to update in the existing item. New keys will be added, existing keys will be overwritten.
    *   (Required for `add`/`update`).
*   `--lock-timeout` (Default: `10`): Timeout in seconds to wait for acquiring the file lock. If the timeout is reached, the script will exit with an error.
*   `--schema-file` (Optional): Path to a JSON schema file. If provided, the entire list data will be validated against this schema *after* modifications but *before* the final write. If validation fails, changes are discarded, and the script exits with an error. Requires the `jsonschema` library.
*   `--help`: Show the help message and exit.

### Examples

**1. Add a new task:**

```bash
python src/dreamos/cli/safe_edit_json_list.py \
  --target-file runtime/agent_comms/project_boards/task_backlog.json \
  --action add \
  --item-data '{"task_id": "NEW-TASK-001", "name": "Implement Feature X", "status": "PENDING", "priority": "MEDIUM"}'
```

**2. Remove a task by ID:**

```bash
python src/dreamos/cli/safe_edit_json_list.py \
  --target-file runtime/agent_comms/project_boards/task_backlog.json \
  --action remove \
  --item-id-key task_id \
  --item-id OLD-TASK-005
```

**3. Update the status of a task:**

```bash
python src/dreamos/cli/safe_edit_json_list.py \
  --target-file runtime/agent_comms/project_boards/working_tasks.json \
  --action update \
  --item-id-key task_id \
  --item-id ACTIVE-TASK-002 \
  --item-data '{"status": "COMPLETED", "timestamp_completed_utc": "2023-10-27T12:00:00Z"}'
```

**4. Add an item and validate against a schema:**

```bash
python src/dreamos/cli/safe_edit_json_list.py \
  --target-file runtime/agent_comms/project_boards/task_backlog.json \
  --action add \
  --item-data '{"task_id": "VALIDATED-TASK-001", "name": "Valid Task", "status": "PENDING"}' \
  --schema-file docs/schemas/task_schema.json
```

## Exit Codes

*   `0`: Success (changes applied or no changes needed).
*   `1`: Error (e.g., invalid arguments, file not found, lock timeout, JSON error, schema validation failure).

## Notes

*   If the `filelock` library is not installed, a warning will be logged, and file operations will not be concurrency-safe.
*   If the `jsonschema` library is not installed and `--schema-file` is provided, a warning will be logged, and validation will be skipped.
*   The script currently assumes it is run relative to the project root directory for path setup.
