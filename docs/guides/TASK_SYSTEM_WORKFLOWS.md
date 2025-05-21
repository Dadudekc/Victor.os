# Task System Example Workflows

## 1. Task Lifecycle Management

### Basic Task Lifecycle

```python
from datetime import datetime
from typing import List, Dict, Any
from dreamos.coordination.tasks.task_manager_stable import TaskManager

def manage_task_lifecycle():
    """Demonstrate complete task lifecycle."""
    # Initialize
    task_manager = TaskManager("tasks")
    
    # Create task
    task = {
        "task_id": f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "description": "Example lifecycle task",
        "status": "PENDING",
        "created_at": datetime.now().isoformat()
    }
    
    # Write to board
    task_manager.write_task_board("active_tasks.json", [task])
    
    # Update to IN_PROGRESS
    tasks = task_manager.read_task_board("active_tasks.json")
    for t in tasks:
        if t["task_id"] == task["task_id"]:
            t["status"] = "IN_PROGRESS"
    task_manager.write_task_board("active_tasks.json", tasks)
    
    # Complete task
    tasks = task_manager.read_task_board("active_tasks.json")
    for t in tasks:
        if t["task_id"] == task["task_id"]:
            t["status"] = "COMPLETED"
            t["completed_at"] = datetime.now().isoformat()
    task_manager.write_task_board("active_tasks.json", tasks)
```

### Task with Dependencies

```python
def manage_dependent_tasks():
    """Manage tasks with dependencies."""
    task_manager = TaskManager("tasks")
    
    # Create parent task
    parent = {
        "task_id": "TASK-PARENT-001",
        "description": "Parent task",
        "status": "PENDING",
        "created_at": datetime.now().isoformat()
    }
    
    # Create child tasks
    children = [
        {
            "task_id": f"TASK-CHILD-{i}",
            "description": f"Child task {i}",
            "status": "PENDING",
            "parent_id": "TASK-PARENT-001",
            "created_at": datetime.now().isoformat()
        }
        for i in range(3)
    ]
    
    # Write all tasks
    task_manager.write_task_board("active_tasks.json", [parent] + children)
    
    # Update parent when all children complete
    def update_parent_status():
        tasks = task_manager.read_task_board("active_tasks.json")
        children_complete = all(
            t["status"] == "COMPLETED"
            for t in tasks
            if t.get("parent_id") == "TASK-PARENT-001"
        )
        if children_complete:
            for t in tasks:
                if t["task_id"] == "TASK-PARENT-001":
                    t["status"] = "COMPLETED"
            task_manager.write_task_board("active_tasks.json", tasks)
```

## 2. Batch Processing

### Bulk Task Creation

```python
def create_bulk_tasks(descriptions: List[str]) -> List[Dict[str, Any]]:
    """Create multiple tasks in one operation."""
    task_manager = TaskManager("tasks")
    
    # Create tasks
    tasks = [
        {
            "task_id": f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{i}",
            "description": desc,
            "status": "PENDING",
            "created_at": datetime.now().isoformat()
        }
        for i, desc in enumerate(descriptions)
    ]
    
    # Write all at once
    task_manager.write_task_board("active_tasks.json", tasks)
    return tasks
```

### Batch Status Updates

```python
def update_batch_status(task_ids: List[str], new_status: str) -> bool:
    """Update status of multiple tasks."""
    task_manager = TaskManager("tasks")
    
    # Read current tasks
    tasks = task_manager.read_task_board("active_tasks.json")
    
    # Update matching tasks
    updated = False
    for task in tasks:
        if task["task_id"] in task_ids:
            task["status"] = new_status
            updated = True
    
    # Write back if any updates
    if updated:
        return task_manager.write_task_board("active_tasks.json", tasks)
    return False
```

## 3. Task Monitoring

### Status Tracking

```python
def track_task_status():
    """Monitor task status changes."""
    task_manager = TaskManager("tasks")
    
    def get_status_counts() -> Dict[str, int]:
        """Get count of tasks by status."""
        tasks = task_manager.read_task_board("active_tasks.json")
        counts = {}
        for task in tasks:
            status = task["status"]
            counts[status] = counts.get(status, 0) + 1
        return counts
    
    # Monitor changes
    previous_counts = get_status_counts()
    while True:
        current_counts = get_status_counts()
        if current_counts != previous_counts:
            print("Status changes detected:")
            for status, count in current_counts.items():
                prev_count = previous_counts.get(status, 0)
                if count != prev_count:
                    print(f"{status}: {prev_count} -> {count}")
        previous_counts = current_counts
        time.sleep(60)  # Check every minute
```

### Performance Monitoring

```python
def monitor_task_performance():
    """Track task completion times."""
    task_manager = TaskManager("tasks")
    
    def calculate_metrics() -> Dict[str, float]:
        """Calculate task performance metrics."""
        tasks = task_manager.read_task_board("active_tasks.json")
        completed_tasks = [
            t for t in tasks
            if t["status"] == "COMPLETED"
            and "created_at" in t
            and "completed_at" in t
        ]
        
        if not completed_tasks:
            return {}
        
        durations = [
            (datetime.fromisoformat(t["completed_at"]) -
             datetime.fromisoformat(t["created_at"])).total_seconds()
            for t in completed_tasks
        ]
        
        return {
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations)
        }
```

## 4. Error Recovery

### Automatic Retry

```python
def retry_failed_tasks(max_retries: int = 3):
    """Retry failed tasks automatically."""
    task_manager = TaskManager("tasks")
    
    tasks = task_manager.read_task_board("active_tasks.json")
    for task in tasks:
        if task["status"] == "FAILED":
            retries = task.get("retry_count", 0)
            if retries < max_retries:
                task["status"] = "PENDING"
                task["retry_count"] = retries + 1
                task["last_retry"] = datetime.now().isoformat()
    
    task_manager.write_task_board("active_tasks.json", tasks)
```

### Corrupted Board Recovery

```python
def recover_corrupted_board():
    """Recover from corrupted task board."""
    task_manager = TaskManager("tasks")
    
    # Check for corruption
    if task_manager.detect_corruption("active_tasks.json"):
        # Try to repair
        if task_manager.repair_task_board("active_tasks.json"):
            print("Board repaired successfully")
        else:
            # Restore from backup
            backup_path = task_manager.backup_task_board("active_tasks.json")
            if task_manager.restore_from_backup(backup_path, "active_tasks.json"):
                print("Board restored from backup")
            else:
                print("Recovery failed")
```

## 5. Task Synchronization

### Multi-Board Sync

```python
def sync_task_boards():
    """Synchronize tasks across multiple boards."""
    task_manager = TaskManager("tasks")
    
    # Read from source
    source_tasks = task_manager.read_task_board("source_tasks.json")
    
    # Update target
    target_tasks = task_manager.read_task_board("target_tasks.json")
    
    # Merge tasks
    task_map = {t["task_id"]: t for t in target_tasks}
    for task in source_tasks:
        task_map[task["task_id"]] = task
    
    # Write back
    task_manager.write_task_board("target_tasks.json", list(task_map.values()))
```

### Status Synchronization

```python
def sync_task_status():
    """Synchronize task status across boards."""
    task_manager = TaskManager("tasks")
    
    # Read from both boards
    board1_tasks = task_manager.read_task_board("board1.json")
    board2_tasks = task_manager.read_task_board("board2.json")
    
    # Create lookup
    board2_map = {t["task_id"]: t for t in board2_tasks}
    
    # Update statuses
    for task in board1_tasks:
        if task["task_id"] in board2_map:
            board2_map[task["task_id"]]["status"] = task["status"]
    
    # Write back
    task_manager.write_task_board("board2.json", list(board2_map.values()))
```

## 6. Task Archiving

### Archive Completed Tasks

```python
def archive_completed_tasks():
    """Move completed tasks to archive."""
    task_manager = TaskManager("tasks")
    
    # Read active tasks
    active_tasks = task_manager.read_task_board("active_tasks.json")
    
    # Separate completed tasks
    completed_tasks = [
        t for t in active_tasks
        if t["status"] == "COMPLETED"
    ]
    remaining_tasks = [
        t for t in active_tasks
        if t["status"] != "COMPLETED"
    ]
    
    # Read archive
    try:
        archive_tasks = task_manager.read_task_board("archive.json")
    except TaskBoardError:
        archive_tasks = []
    
    # Update both boards
    task_manager.write_task_board("active_tasks.json", remaining_tasks)
    task_manager.write_task_board("archive.json", archive_tasks + completed_tasks)
```

### Archive by Date

```python
def archive_old_tasks(days: int = 30):
    """Archive tasks older than specified days."""
    task_manager = TaskManager("tasks")
    
    # Read active tasks
    active_tasks = task_manager.read_task_board("active_tasks.json")
    
    # Calculate cutoff date
    cutoff = datetime.now() - timedelta(days=days)
    
    # Separate old tasks
    old_tasks = [
        t for t in active_tasks
        if datetime.fromisoformat(t["created_at"]) < cutoff
    ]
    recent_tasks = [
        t for t in active_tasks
        if datetime.fromisoformat(t["created_at"]) >= cutoff
    ]
    
    # Read archive
    try:
        archive_tasks = task_manager.read_task_board("archive.json")
    except TaskBoardError:
        archive_tasks = []
    
    # Update both boards
    task_manager.write_task_board("active_tasks.json", recent_tasks)
    task_manager.write_task_board("archive.json", archive_tasks + old_tasks)
``` 