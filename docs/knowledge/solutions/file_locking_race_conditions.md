# Solution: Preventing File Locking Race Conditions

**Problem Category:** File Operations, Concurrency
**Related Components:** FileLock, TaskBoard
**Author:** Agent-2
**Last Updated:** 2023-08-14

## Problem Description

Multiple agents attempting to update task board files simultaneously were causing race conditions, resulting in:
- Corrupted JSON files (syntax errors)
- Missing tasks and data loss
- Duplicate entries in task boards
- Inconsistent task states

As documented in `deduplication_log.md` and `duplicate_tasks_report.md`, these issues were particularly prevalent in the task board files located in `runtime/agent_comms/project_boards/`.

## Root Cause Analysis

1. **No Locking Mechanism:** Multiple agents were reading and writing to the same file concurrently without synchronization.
2. **Non-Atomic Operations:** The read-modify-write cycle was not atomic, allowing for race conditions.
3. **Error Handling Gaps:** Failed writes due to race conditions were not properly detected or recovered from.

## Solution Implementation

Implemented a file locking mechanism using the `FileLock` class from the File Operations Skill Library:

```python
from dreamos.skills.file_ops import FileLock, safe_json_read, safe_json_write

def update_task_board(task_id, new_status):
    # Create a file lock specific to this file
    with FileLock("runtime/agent_comms/project_boards/working_tasks.json"):
        # Read current state (safely with default value if file doesn't exist)
        tasks = safe_json_read(
            "runtime/agent_comms/project_boards/working_tasks.json", 
            default=[]
        )
        
        # Make modifications
        task_found = False
        for task in tasks:
            if task["id"] == task_id:
                task["status"] = new_status
                task["updated_at"] = time.time()
                task_found = True
                break
                
        if not task_found:
            # Handle error case - task not found
            logging.warning(f"Task {task_id} not found in board")
                
        # Write back atomically
        safe_json_write(
            "runtime/agent_comms/project_boards/working_tasks.json", 
            tasks
        )
```

## Key Components

1. **FileLock Class:** 
   - Implements file-based locking using OS-specific mechanisms
   - Handles lock acquisition with timeout and retry
   - Uses context manager pattern for safe cleanup

2. **safe_json_read:**
   - Handles file not found scenarios with default values
   - Retries on transient errors
   - Validates JSON integrity

3. **safe_json_write:**
   - Performs atomic file writes (write to temp, then rename)
   - Creates parent directories if missing
   - Preserves permissions

## Verification Steps

1. Run `tests/test_concurrent_task_updates.py` which simulates multiple agents updating task boards
2. Verify integrity of task board JSON files after concurrent operations
3. Check task history for consistent state transitions

## Related Knowledge

- [Atomic File Operations Pattern](../patterns/atomic_file_operations.md)
- [File Locking Implementation Details](../../api/file_ops/locking.md)
- [Task Board Schema](../../api/tasks/schema.md)

## Lessons Learned

1. **Always Use Locks:** When multiple agents might access the same file, always use a locking mechanism.
2. **Atomic Operations:** Use the pattern of lock → read → modify → write → unlock for all shared resources.
3. **Error Recovery:** Always include proper error handling for lock acquisition failures.
4. **Timeout Handling:** Implement timeout mechanisms to prevent indefinite waiting on locks.

## Future Improvements

1. **Distributed Locking:** Extend to support locking across multiple machines using Redis or similar
2. **Lock Statistics:** Add telemetry to track lock acquisition times and contention
3. **Fine-Grained Locking:** Implement more granular locking at the task level rather than the file level 