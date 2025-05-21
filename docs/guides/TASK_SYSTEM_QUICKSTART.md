# Task System Quick Start Guide

## Installation

1. Install the package:
```bash
pip install dreamos-task-manager
```

2. Create a task directory:
```bash
mkdir tasks
```

## Basic Usage

### 1. Initialize Task Manager

```python
from dreamos.coordination.tasks.task_manager_stable import TaskManager

# Create task manager instance
task_manager = TaskManager(
    task_dir="tasks",
    schema_path="schema.json"  # Optional
)
```

### 2. Create a Task Board

```python
# Create initial tasks
tasks = [
    {
        "task_id": "TASK-20240319-001",
        "description": "Example task",
        "status": "PENDING",
        "created_at": "2024-03-19T14:00:00Z"
    }
]

# Write to board
task_manager.write_task_board("active_tasks.json", tasks)
```

### 3. Read Tasks

```python
# Read all tasks
tasks = task_manager.read_task_board("active_tasks.json")

# Print task details
for task in tasks:
    print(f"Task ID: {task['task_id']}")
    print(f"Status: {task['status']}")
```

### 4. Update Task Status

```python
# Read tasks
tasks = task_manager.read_task_board("active_tasks.json")

# Update status
for task in tasks:
    if task["task_id"] == "TASK-20240319-001":
        task["status"] = "IN_PROGRESS"

# Write back
task_manager.write_task_board("active_tasks.json", tasks)
```

### 5. Handle Duplicates

```python
# Resolve duplicates
result = task_manager.resolve_duplicates("active_tasks.json")

# Check result
if result["status"] == "success":
    print(f"Resolved {result['duplicates_resolved']} duplicates")
```

## Common Patterns

### 1. Task Creation

```python
def create_task(description: str) -> dict:
    """Create a new task with unique ID."""
    return {
        "task_id": f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "description": description,
        "status": "PENDING",
        "created_at": datetime.now().isoformat()
    }

# Usage
new_task = create_task("New task description")
tasks = task_manager.read_task_board("active_tasks.json")
tasks.append(new_task)
task_manager.write_task_board("active_tasks.json", tasks)
```

### 2. Status Updates

```python
def update_task_status(task_id: str, new_status: str) -> bool:
    """Update status of a specific task."""
    tasks = task_manager.read_task_board("active_tasks.json")
    for task in tasks:
        if task["task_id"] == task_id:
            task["status"] = new_status
            return task_manager.write_task_board("active_tasks.json", tasks)
    return False

# Usage
success = update_task_status("TASK-20240319-001", "COMPLETED")
```

### 3. Task Filtering

```python
def get_tasks_by_status(status: str) -> List[dict]:
    """Get all tasks with specific status."""
    tasks = task_manager.read_task_board("active_tasks.json")
    return [task for task in tasks if task["status"] == status]

# Usage
pending_tasks = get_tasks_by_status("PENDING")
```

### 4. Error Handling

```python
from dreamos.coordination.tasks.task_manager_stable import (
    TaskManagerError,
    TaskBoardError,
    FileLockError,
    TaskValidationError
)

def safe_task_operation(operation):
    """Execute task operation with error handling."""
    try:
        return operation()
    except TaskValidationError as e:
        print(f"Validation error: {e}")
    except TaskBoardError as e:
        print(f"Board error: {e}")
    except FileLockError as e:
        print(f"Lock error: {e}")
    except TaskManagerError as e:
        print(f"General error: {e}")
    return False

# Usage
success = safe_task_operation(
    lambda: task_manager.write_task_board("active_tasks.json", tasks)
)
```

## Best Practices

1. **Task IDs**
   - Use consistent format
   - Include timestamp
   - Make them unique

2. **Status Management**
   - Update promptly
   - Use valid statuses
   - Document transitions

3. **Error Handling**
   - Always use try-except
   - Check operation results
   - Log errors

4. **Concurrent Access**
   - Use appropriate timeouts
   - Handle lock failures
   - Implement retries

## Next Steps

1. Read the [System Usage Guide](TASK_SYSTEM_USAGE.md)
2. Check the [API Reference](TASK_MANAGER_API.md)
3. Review [Example Workflows](TASK_SYSTEM_WORKFLOWS.md)
4. See [Troubleshooting Guide](TASK_SYSTEM_TROUBLESHOOTING.md) 