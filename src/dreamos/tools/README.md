# Dream.OS Tools

This directory contains utility tools for the Dream.OS project.

## Task Board Updater

`task_board_updater.py` - Safely updates the task_board.json file using filelock to avoid permission errors and race conditions.

### Installation

Requires the `filelock` package:

```bash
pip install filelock
```

### Usage

```bash
# Update an agent's status
python src/dreamos/tools/task_board_updater.py update-status agent_id status [--status-details DETAILS] [--task-id TASK_ID] [--task-description DESC]

# Add a task to an agent's task list
python src/dreamos/tools/task_board_updater.py add-task agent_id task_id task_json

# Update an existing task
python src/dreamos/tools/task_board_updater.py update-task agent_id task_id updates_json
```

### Examples

```bash
# Update cursor_1's status to IDLE
python src/dreamos/tools/task_board_updater.py update-status cursor_1 IDLE --status-details "Waiting for new tasks"

# Add a new task to cursor_2
python src/dreamos/tools/task_board_updater.py add-task cursor_2 "new-task-001" '{"description": "New task description", "status": "PENDING", "last_updated": "2025-05-18T12:00:00Z"}'

# Update an existing task
python src/dreamos/tools/task_board_updater.py update-task cursor_3 "existing-task-001" '{"status": "COMPLETED", "last_updated": "2025-05-18T15:30:00Z"}'
```

### Key Features

- **File Locking**: Uses filelock to safely handle concurrent access
- **Atomic Writes**: Uses temporary files and atomic replacement to prevent corruption
- **Error Handling**: Robust error handling and cleanup for temp files
- **Command Line Interface**: Easy-to-use CLI with multiple operations 