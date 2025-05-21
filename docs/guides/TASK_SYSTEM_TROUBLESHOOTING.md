# Task System Troubleshooting Guide

## Common Issues and Solutions

### 1. File Lock Issues

#### Symptoms
- `FileLockError` exceptions
- Tasks not being saved
- Concurrent access failures

#### Solutions

1. **Check Lock Timeout**
```python
# Increase lock timeout
task_manager = TaskManager(
    task_dir="tasks",
    lock_timeout=60  # Increase from default 30 seconds
)
```

2. **Verify File Permissions**
```bash
# Check directory permissions
ls -la tasks/

# Fix permissions if needed
chmod 755 tasks/
chmod 644 tasks/*.json
```

3. **Clear Stale Locks**
```python
def clear_stale_locks():
    """Remove stale lock files."""
    import os
    import glob
    
    # Find lock files
    lock_files = glob.glob("tasks/*.lock")
    
    # Remove old locks
    for lock_file in lock_files:
        if os.path.getmtime(lock_file) < time.time() - 3600:  # 1 hour old
            os.remove(lock_file)
```

### 2. Task Validation Errors

#### Symptoms
- `TaskValidationError` exceptions
- Tasks not being saved
- Invalid task data

#### Solutions

1. **Check Task Schema**
```python
# Verify task structure
task = {
    "task_id": "TASK-001",  # Required
    "description": "Task description",  # Required
    "status": "PENDING",  # Must be one of VALID_STATUSES
    "created_at": datetime.now().isoformat()  # Optional
}

# Validate against schema
from jsonschema import validate
validate(instance=task, schema=task_schema)
```

2. **Fix Common Issues**
```python
def fix_task_validation(task: dict) -> dict:
    """Fix common validation issues."""
    # Ensure required fields
    if "task_id" not in task:
        task["task_id"] = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    if "description" not in task:
        task["description"] = "No description provided"
    
    # Fix status
    if "status" not in task or task["status"] not in VALID_STATUSES:
        task["status"] = "PENDING"
    
    return task
```

### 3. Duplicate Tasks

#### Symptoms
- Multiple tasks with same ID
- Inconsistent task states
- Task count mismatches

#### Solutions

1. **Detect Duplicates**
```python
def find_duplicates(tasks: List[dict]) -> Dict[str, List[dict]]:
    """Find duplicate tasks by ID."""
    duplicates = {}
    for task in tasks:
        task_id = task["task_id"]
        if task_id not in duplicates:
            duplicates[task_id] = []
        duplicates[task_id].append(task)
    return {k: v for k, v in duplicates.items() if len(v) > 1}
```

2. **Resolve Duplicates**
```python
def resolve_duplicates(tasks: List[dict]) -> List[dict]:
    """Resolve duplicate tasks keeping most recent."""
    # Group by ID
    task_map = {}
    for task in tasks:
        task_id = task["task_id"]
        if task_id not in task_map:
            task_map[task_id] = task
        else:
            # Keep most recent
            if task["created_at"] > task_map[task_id]["created_at"]:
                task_map[task_id] = task
    
    return list(task_map.values())
```

### 4. Corrupted Task Boards

#### Symptoms
- JSON parsing errors
- Missing or invalid data
- Inconsistent state

#### Solutions

1. **Detect Corruption**
```python
def check_board_integrity(board_name: str) -> bool:
    """Check task board integrity."""
    try:
        # Try to read board
        tasks = task_manager.read_task_board(board_name)
        
        # Validate each task
        for task in tasks:
            if not isinstance(task, dict):
                return False
            if "task_id" not in task or "status" not in task:
                return False
        
        return True
    except Exception:
        return False
```

2. **Repair Corrupted Board**
```python
def repair_board(board_name: str) -> bool:
    """Attempt to repair corrupted board."""
    try:
        # Read raw file
        with open(f"tasks/{board_name}", "r") as f:
            content = f.read()
        
        # Try to fix JSON
        fixed_content = content.replace("'", '"')  # Fix quotes
        fixed_content = re.sub(r',\s*}', '}', fixed_content)  # Fix trailing commas
        
        # Parse and validate
        tasks = json.loads(fixed_content)
        if not isinstance(tasks, list):
            return False
        
        # Write back
        task_manager.write_task_board(board_name, tasks)
        return True
    except Exception:
        return False
```

### 5. Performance Issues

#### Symptoms
- Slow task operations
- High memory usage
- Timeout errors

#### Solutions

1. **Optimize Batch Operations**
```python
def batch_update_tasks(tasks: List[dict], updates: Dict[str, Any]) -> bool:
    """Update multiple tasks efficiently."""
    # Create lookup
    task_map = {t["task_id"]: t for t in tasks}
    
    # Apply updates
    for task_id, update in updates.items():
        if task_id in task_map:
            task_map[task_id].update(update)
    
    # Write back
    return task_manager.write_task_board("active_tasks.json", list(task_map.values()))
```

2. **Implement Caching**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_task_status(task_id: str) -> str:
    """Get task status with caching."""
    tasks = task_manager.read_task_board("active_tasks.json")
    for task in tasks:
        if task["task_id"] == task_id:
            return task["status"]
    return None
```

### 6. Transaction Log Issues

#### Symptoms
- Missing transaction records
- Log file errors
- Inconsistent state

#### Solutions

1. **Verify Transaction Log**
```python
def verify_transaction_log():
    """Verify transaction log integrity."""
    try:
        with open("transaction_log.jsonl", "r") as f:
            for line in f:
                # Validate each entry
                entry = json.loads(line)
                required_fields = ["timestamp", "operation", "status"]
                if not all(field in entry for field in required_fields):
                    print(f"Invalid entry: {entry}")
    except Exception as e:
        print(f"Log verification failed: {e}")
```

2. **Repair Transaction Log**
```python
def repair_transaction_log():
    """Repair corrupted transaction log."""
    # Read all entries
    entries = []
    try:
        with open("transaction_log.jsonl", "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    
    # Write back valid entries
    with open("transaction_log.jsonl", "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
```

## Debugging Tools

### 1. Task Board Inspector

```python
def inspect_task_board(board_name: str):
    """Inspect task board contents and structure."""
    try:
        # Read board
        tasks = task_manager.read_task_board(board_name)
        
        # Print statistics
        print(f"Total tasks: {len(tasks)}")
        print("\nStatus distribution:")
        status_counts = {}
        for task in tasks:
            status = task["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in status_counts.items():
            print(f"{status}: {count}")
        
        # Check for issues
        print("\nPotential issues:")
        for task in tasks:
            if "task_id" not in task:
                print(f"Missing task_id: {task}")
            if "status" not in task:
                print(f"Missing status: {task}")
            if task["status"] not in VALID_STATUSES:
                print(f"Invalid status: {task}")
    except Exception as e:
        print(f"Inspection failed: {e}")
```

### 2. Performance Profiler

```python
def profile_task_operations():
    """Profile task manager operations."""
    import cProfile
    import pstats
    
    # Create profiler
    profiler = cProfile.Profile()
    
    # Profile operations
    profiler.enable()
    
    # Run test operations
    task_manager.read_task_board("active_tasks.json")
    task_manager.write_task_board("active_tasks.json", [])
    task_manager.resolve_duplicates("active_tasks.json")
    
    profiler.disable()
    
    # Print results
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")
    stats.print_stats()
```

### 3. State Validator

```python
def validate_system_state():
    """Validate overall system state."""
    # Check task boards
    board_files = glob.glob("tasks/*.json")
    for board_file in board_files:
        board_name = os.path.basename(board_file)
        if not check_board_integrity(board_name):
            print(f"Corrupted board: {board_name}")
    
    # Check transaction log
    verify_transaction_log()
    
    # Check for stale locks
    lock_files = glob.glob("tasks/*.lock")
    for lock_file in lock_files:
        if os.path.getmtime(lock_file) < time.time() - 3600:
            print(f"Stale lock: {lock_file}")
    
    # Check file permissions
    for file in board_files + lock_files:
        if not os.access(file, os.R_OK | os.W_OK):
            print(f"Permission issue: {file}")
```

## Recovery Procedures

### 1. Board Recovery

```python
def recover_task_board(board_name: str) -> bool:
    """Recover corrupted task board."""
    # Try repair first
    if repair_board(board_name):
        return True
    
    # Try backup
    backup_path = task_manager.backup_task_board(board_name)
    if task_manager.restore_from_backup(backup_path, board_name):
        return True
    
    # Create new board
    task_manager.write_task_board(board_name, [])
    return True
```

### 2. Transaction Log Recovery

```python
def recover_transaction_log() -> bool:
    """Recover corrupted transaction log."""
    # Backup current log
    if os.path.exists("transaction_log.jsonl"):
        os.rename("transaction_log.jsonl", "transaction_log.jsonl.bak")
    
    # Create new log
    with open("transaction_log.jsonl", "w") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "operation": "log_recovery",
            "status": "success"
        }) + "\n")
    
    return True
```

### 3. System Recovery

```python
def recover_system_state() -> bool:
    """Recover from system-wide issues."""
    # Stop all operations
    task_manager.stop()
    
    # Clear stale locks
    clear_stale_locks()
    
    # Recover boards
    board_files = glob.glob("tasks/*.json")
    for board_file in board_files:
        board_name = os.path.basename(board_file)
        recover_task_board(board_name)
    
    # Recover transaction log
    recover_transaction_log()
    
    # Verify recovery
    validate_system_state()
    
    return True
```

## Prevention Measures

### 1. Regular Maintenance

```python
def perform_maintenance():
    """Perform regular system maintenance."""
    # Archive old tasks
    archive_old_tasks(days=30)
    
    # Resolve duplicates
    task_manager.resolve_duplicates("active_tasks.json")
    
    # Verify system state
    validate_system_state()
    
    # Clean up old backups
    cleanup_old_backups(days=7)
```

### 2. Monitoring

```python
def monitor_system_health():
    """Monitor system health metrics."""
    # Track performance
    profile_task_operations()
    
    # Check for issues
    validate_system_state()
    
    # Monitor resource usage
    import psutil
    process = psutil.Process()
    print(f"Memory usage: {process.memory_info().rss / 1024 / 1024} MB")
    print(f"CPU usage: {process.cpu_percent()}%")
```

### 3. Backup Strategy

```python
def implement_backup_strategy():
    """Implement comprehensive backup strategy."""
    # Daily backups
    for board_name in glob.glob("tasks/*.json"):
        task_manager.backup_task_board(board_name)
    
    # Weekly archives
    if datetime.now().weekday() == 0:  # Monday
        archive_old_tasks(days=7)
    
    # Monthly cleanup
    if datetime.now().day == 1:
        cleanup_old_backups(days=30)
``` 