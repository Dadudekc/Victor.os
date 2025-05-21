# Task Manager API Reference

## TaskManager

The main class for managing tasks and task boards.

### Initialization

```python
TaskManager(task_dir: str, schema_path: Optional[str] = None)
```

**Parameters:**
- `task_dir` (str): Path to the directory containing task boards
- `schema_path` (Optional[str]): Path to JSON schema for task validation

**Example:**
```python
task_manager = TaskManager(
    task_dir="path/to/tasks",
    schema_path="path/to/schema.json"
)
```

### Methods

#### read_task_board

```python
read_task_board(board_name: str) -> List[Dict[str, Any]]
```

Reads all tasks from a task board.

**Parameters:**
- `board_name` (str): Name of the task board file

**Returns:**
- List[Dict[str, Any]]: List of task dictionaries

**Raises:**
- `TaskBoardError`: If board doesn't exist or is invalid
- `FileLockError`: If board is locked
- `TaskManagerError`: For other errors

**Example:**
```python
tasks = task_manager.read_task_board("active_tasks.json")
```

#### write_task_board

```python
write_task_board(board_name: str, tasks: List[Dict[str, Any]]) -> bool
```

Writes tasks to a task board.

**Parameters:**
- `board_name` (str): Name of the task board file
- `tasks` (List[Dict[str, Any]]): List of task dictionaries

**Returns:**
- bool: True if successful

**Raises:**
- `TaskValidationError`: If tasks don't match schema
- `TaskBoardError`: If board is invalid
- `FileLockError`: If board is locked
- `TaskManagerError`: For other errors

**Example:**
```python
success = task_manager.write_task_board("active_tasks.json", tasks)
```

#### resolve_duplicates

```python
resolve_duplicates(board_name: str) -> Dict[str, Any]
```

Resolves duplicate tasks in a board.

**Parameters:**
- `board_name` (str): Name of the task board file

**Returns:**
- Dict[str, Any]: Result containing:
  - `status` (str): "success" or "error"
  - `duplicates_resolved` (int): Number of duplicates resolved
  - `remaining_tasks` (int): Number of tasks after resolution
  - `error` (str): Error message if status is "error"

**Raises:**
- `TaskBoardError`: If board doesn't exist
- `FileLockError`: If board is locked
- `TaskManagerError`: For other errors

**Example:**
```python
result = task_manager.resolve_duplicates("active_tasks.json")
```

#### backup_task_board

```python
backup_task_board(board_name: str) -> str
```

Creates a backup of a task board.

**Parameters:**
- `board_name` (str): Name of the task board file

**Returns:**
- str: Path to backup file

**Raises:**
- `TaskBoardError`: If board doesn't exist
- `FileLockError`: If board is locked
- `TaskManagerError`: For other errors

**Example:**
```python
backup_path = task_manager.backup_task_board("active_tasks.json")
```

#### restore_from_backup

```python
restore_from_backup(backup_path: str, board_name: str) -> bool
```

Restores a task board from backup.

**Parameters:**
- `backup_path` (str): Path to backup file
- `board_name` (str): Name of the task board file

**Returns:**
- bool: True if successful

**Raises:**
- `TaskBoardError`: If backup is invalid
- `FileLockError`: If board is locked
- `TaskManagerError`: For other errors

**Example:**
```python
success = task_manager.restore_from_backup(backup_path, "active_tasks.json")
```

#### verify_all_boards

```python
verify_all_boards() -> Dict[str, Dict[str, Any]]
```

Verifies integrity of all task boards.

**Returns:**
- Dict[str, Dict[str, Any]]: Results for each board:
  - `status` (str): "ok" or "error"
  - `error` (str): Error message if status is "error"

**Example:**
```python
results = task_manager.verify_all_boards()
```

#### detect_corruption

```python
detect_corruption(board_name: str) -> bool
```

Detects corruption in a task board.

**Parameters:**
- `board_name` (str): Name of the task board file

**Returns:**
- bool: True if corruption detected

**Raises:**
- `TaskBoardError`: If board doesn't exist
- `FileLockError`: If board is locked
- `TaskManagerError`: For other errors

**Example:**
```python
is_corrupted = task_manager.detect_corruption("active_tasks.json")
```

#### repair_task_board

```python
repair_task_board(board_name: str) -> bool
```

Attempts to repair a corrupted task board.

**Parameters:**
- `board_name` (str): Name of the task board file

**Returns:**
- bool: True if repair successful

**Raises:**
- `TaskBoardError`: If board doesn't exist
- `FileLockError`: If board is locked
- `TaskManagerError`: For other errors

**Example:**
```python
success = task_manager.repair_task_board("active_tasks.json")
```

### Properties

#### task_dir

```python
task_dir: str
```

Path to the task directory.

#### schema_path

```python
schema_path: Optional[str]
```

Path to the task validation schema.

### Exceptions

#### TaskManagerError

Base exception for task manager errors.

#### TaskBoardError

Raised for task board related errors.

#### FileLockError

Raised when file locking fails.

#### TaskValidationError

Raised when task validation fails.

### Constants

#### VALID_STATUSES

```python
VALID_STATUSES: List[str] = [
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    "BLOCKED"
]
```

Valid task status values.

#### LOCK_TIMEOUT

```python
LOCK_TIMEOUT: int = 30
```

Default file lock timeout in seconds.

#### MAX_RETRIES

```python
MAX_RETRIES: int = 3
```

Maximum number of operation retries.

### Type Definitions

#### Task

```python
Task = Dict[str, Any]
```

Type alias for task dictionary.

#### TaskBoard

```python
TaskBoard = List[Task]
```

Type alias for task board list.

#### TaskResult

```python
TaskResult = Dict[str, Any]
```

Type alias for task operation result. 