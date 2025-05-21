# Task System Usage Guide

## Overview

The enhanced task management system provides robust task handling with features like:
- Atomic file operations with file locking
- Comprehensive transaction logging
- JSON schema validation
- Duplicate task detection and resolution
- Rollback mechanism
- Conflict detection and resolution

## Basic Usage

### Initialization

```python
from dreamos.coordination.tasks.task_manager_stable import TaskManager

# Initialize task manager
task_manager = TaskManager(
    task_dir="path/to/task/directory",
    schema_path="path/to/schema.json"  # Optional
)
```

### Task Board Operations

#### Reading Tasks
```python
# Read all tasks from a board
tasks = task_manager.read_task_board("board_name.json")

# Tasks are returned as a list of dictionaries
for task in tasks:
    print(f"Task ID: {task['task_id']}")
    print(f"Status: {task['status']}")
```

#### Writing Tasks
```python
# Create new tasks
tasks = [
    {
        "task_id": "TASK-001",
        "description": "Example task",
        "status": "PENDING",
        "created_at": "2024-03-19T13:00:00Z"
    }
]

# Write tasks to board
task_manager.write_task_board("board_name.json", tasks)
```

### Task Validation

The system validates tasks against a JSON schema. Required fields:
- `task_id`: Unique identifier (string)
- `description`: Task description (string)
- `status`: One of ["PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "BLOCKED"]

Example schema:
```json
{
    "type": "object",
    "required": ["task_id", "description", "status"],
    "properties": {
        "task_id": {"type": "string"},
        "description": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "BLOCKED"]
        }
    }
}
```

### Duplicate Resolution

The system can detect and resolve duplicate tasks:

```python
# Resolve duplicates in a board
result = task_manager.resolve_duplicates("board_name.json")

# Check results
if result["status"] == "success":
    print(f"Resolved {result['duplicates_resolved']} duplicates")
    print(f"Remaining tasks: {result['remaining_tasks']}")
```

### Transaction Logging

All operations are logged to a transaction log file (`transaction_log.jsonl`). Each log entry contains:
- Timestamp
- Operation type
- Task board name
- Task ID (if applicable)
- Operation status
- Additional details

Example log entry:
```json
{
    "timestamp": "2024-03-19T13:00:00Z",
    "operation": "write_task_board",
    "task_board": "board_name.json",
    "status": "success",
    "details": {
        "tasks_written": 1
    }
}
```

### Error Handling

The system provides comprehensive error handling:

```python
from dreamos.coordination.tasks.task_manager_stable import (
    TaskManagerError,
    TaskBoardError,
    FileLockError,
    TaskValidationError
)

try:
    # Task operations
    task_manager.write_task_board("board_name.json", tasks)
except TaskValidationError as e:
    print(f"Validation error: {e}")
except TaskBoardError as e:
    print(f"Board error: {e}")
except FileLockError as e:
    print(f"Lock error: {e}")
except TaskManagerError as e:
    print(f"General error: {e}")
```

### Backup and Restore

The system maintains backups of task boards:

```python
# Create backup
backup_path = task_manager.backup_task_board("board_name.json")

# Restore from backup
success = task_manager.restore_from_backup(backup_path, "board_name.json")
```

### Board Verification

Verify the integrity of all task boards:

```python
# Verify all boards
results = task_manager.verify_all_boards()

# Check results
for board, status in results.items():
    print(f"Board: {board}")
    print(f"Status: {status['status']}")
    if status['status'] == 'error':
        print(f"Error: {status['error']}")
```

## Best Practices

1. **Task IDs**
   - Use consistent ID format
   - Include timestamp or sequence number
   - Example: "TASK-20240319-001"

2. **Status Management**
   - Update status promptly
   - Use appropriate status values
   - Document status transitions

3. **Error Handling**
   - Always use try-except blocks
   - Check operation results
   - Log errors appropriately

4. **Concurrent Access**
   - Use appropriate timeouts
   - Handle lock failures gracefully
   - Implement retry logic

5. **Data Integrity**
   - Regular board verification
   - Periodic backups
   - Monitor transaction logs

## Troubleshooting

### Common Issues

1. **Lock Timeout**
   - Increase lock timeout
   - Check for stuck processes
   - Verify file permissions

2. **Validation Errors**
   - Check task schema
   - Verify required fields
   - Validate status values

3. **Duplicate Tasks**
   - Run duplicate resolution
   - Check task ID generation
   - Monitor task creation

4. **Transaction Log Issues**
   - Check disk space
   - Verify file permissions
   - Monitor log size

### Debugging

1. **Enable Debug Logging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Check Transaction Log**
```python
# Read last 10 transactions
with open("transaction_log.jsonl") as f:
    for line in f.readlines()[-10:]:
        print(json.loads(line))
```

3. **Verify Board Integrity**
```python
# Check specific board
if task_manager.detect_corruption("board_name.json"):
    print("Board is corrupted")
    task_manager.repair_task_board("board_name.json")
```

## Support

For issues or questions:
1. Check transaction logs
2. Review error reports
3. Contact system administrator 