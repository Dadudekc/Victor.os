"""
Enhanced Task Manager with improved stability and reliability.

This module provides a robust task management system with:
- Atomic file operations with file locking
- Comprehensive transaction logging
- JSON schema validation
- Duplicate task detection
- Rollback mechanism
- Conflict detection and resolution
- Performance optimizations and caching
"""

import os
import json
import time
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union
import jsonschema
import platform
import fcntl
import msvcrt
import shutil
from functools import lru_cache
from threading import Lock

from dreamos.utils.resilient_io import read_file, write_file
from dreamos.agents.task_schema import Task, TaskHistory, TASK_STATUS, TASK_PRIORITY, TASK_TYPES
from dreamos.agents.task_schema import TaskSchema

logger = logging.getLogger(__name__)

class TaskManagerError(Exception):
    """Base exception for task manager errors."""
    pass

class TaskBoardError(TaskManagerError):
    """Exception for task board errors."""
    pass

class FileLockError(TaskManagerError):
    """Exception for file locking operations."""
    pass

class TaskValidationError(TaskManagerError):
    """Exception for task validation errors."""
    pass

class TaskManager:
    """Enhanced task manager with improved stability and reliability."""
    
    def __init__(self, task_dir: Union[str, Path], schema_path: Optional[Union[str, Path]] = None):
        """Initialize the task manager.
        
        Args:
            task_dir: Directory containing task boards
            schema_path: Optional path to JSON schema file
        """
        self.task_dir = Path(task_dir)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize schema
        self.task_schema = None
        if schema_path:
            try:
                with open(schema_path) as f:
                    self.task_schema = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load task schema: {str(e)}")
        
        # Initialize transaction log
        self.transaction_log_path = self.task_dir / "transaction_log.jsonl"
        self.transaction_log_path.touch(exist_ok=True)
        
        # Lock timeout (seconds)
        self.lock_timeout = 30
        
        # Create backup directory
        self.backup_dir = self.task_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize cache
        self._task_cache = {}
        self._cache_lock = Lock()
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_update = 0
        
        # Initialize performance metrics
        self._metrics = {
            'read_operations': 0,
            'write_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_errors': 0,
            'lock_timeouts': 0
        }
        
    def _update_cache(self, board_name: str, tasks: List[Dict[str, Any]]):
        """Update the task cache for a board.
        
        Args:
            board_name: Name of the task board
            tasks: List of tasks to cache
        """
        with self._cache_lock:
            self._task_cache[board_name] = {
                'tasks': tasks,
                'timestamp': time.time()
            }
            self._last_cache_update = time.time()
            
    def _get_from_cache(self, board_name: str) -> Optional[List[Dict[str, Any]]]:
        """Get tasks from cache if available and not expired.
        
        Args:
            board_name: Name of the task board
            
        Returns:
            List of tasks if in cache and not expired, None otherwise
        """
        with self._cache_lock:
            if board_name in self._task_cache:
                cache_entry = self._task_cache[board_name]
                if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                    self._metrics['cache_hits'] += 1
                    return cache_entry['tasks']
                else:
                    # Cache expired
                    del self._task_cache[board_name]
            self._metrics['cache_misses'] += 1
            return None
            
    def _invalidate_cache(self, board_name: str):
        """Invalidate cache for a board.
        
        Args:
            board_name: Name of the task board
        """
        with self._cache_lock:
            if board_name in self._task_cache:
                del self._task_cache[board_name]
                
    def _acquire_lock(self, path: Path, exclusive: bool = True) -> int:
        """Acquire a file lock.
        
        Args:
            path: Path to file to lock
            exclusive: Whether to acquire an exclusive lock
            
        Returns:
            File descriptor
            
        Raises:
            TaskBoardError: If lock cannot be acquired
        """
        try:
            # Open file for locking
            fd = os.open(path, os.O_RDWR | os.O_CREAT)
            
            # Acquire lock
            if platform.system() == 'Windows':
                if exclusive:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    msvcrt.locking(fd, msvcrt.LK_NBRLCK, 1)
            else:
                if exclusive:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            
            logger.debug(f"Lock acquired for {path}")
            return fd
            
        except Exception as e:
            logger.error(f"Failed to acquire lock for {path}: {str(e)}")
            self._metrics['lock_timeouts'] += 1
            try:
                os.close(fd)
            except:
                pass
            raise TaskBoardError(f"Could not acquire lock for {path}: {str(e)}")
    
    def _release_lock(self, fd: int):
        """Release a file lock.
        
        Args:
            fd: File descriptor
        """
        try:
            if platform.system() == 'Windows':
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            logger.debug(f"Lock released for file descriptor {fd}")
        except Exception as e:
            logger.error(f"Error releasing lock: {str(e)}")
            try:
                os.close(fd)
            except:
                pass
    
    def _log_transaction(self, operation: str, task_board: str, task_id: Optional[str] = None, 
                        details: Dict[str, Any] = None, status: str = "success"):
        """Log a transaction to the transaction log with resilient IO.
        
        Args:
            operation: Operation type (e.g., "read", "write", "update")
            task_board: Task board file name
            task_id: Optional task ID for task-specific operations
            details: Additional details about the operation
            status: Operation status ("success", "failed", "rollback")
        """
        try:
            # Create transaction entry
            transaction = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": operation,
                "task_board": task_board,
                "status": status
            }
            
            if task_id:
                transaction["task_id"] = task_id
                
            if details:
                transaction["details"] = details
            
            # Read existing log if it exists
            if os.path.exists(self.transaction_log_path):
                try:
                    with open(self.transaction_log_path, 'a') as f:
                        f.write(json.dumps(transaction) + '\n')
                except Exception as e:
                    logger.error(f"Failed to append to transaction log: {str(e)}")
                    # Use resilient fallback
                    content = read_file(str(self.transaction_log_path)) + json.dumps(transaction) + '\n'
                    write_file(str(self.transaction_log_path), content)
            else:
                # Create new log file
                write_file(str(self.transaction_log_path), json.dumps(transaction) + '\n')
                
            logger.debug(f"Logged transaction: {operation} on {task_board}")
            
        except Exception as e:
            logger.error(f"Failed to log transaction: {str(e)}")
            # Continue execution even if logging fails
    
    def _validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate a task against the schema.
        
        Args:
            task: Task data to validate
            
        Returns:
            True if valid
            
        Raises:
            TaskValidationError: If validation fails
        """
        try:
            # Use TaskSchema for validation
            task_schema = TaskSchema()
            is_valid, errors = task_schema.validate_task(task)
            
            if not is_valid:
                self._metrics['validation_errors'] += 1
                raise TaskValidationError(f"Task validation failed: {', '.join(errors)}")
            
            # Validate task dependencies if we have access to all tasks
            if hasattr(self, '_task_cache'):
                task_obj = Task(**task)
                is_valid, errors = task_schema.validate_task_dependencies(task_obj, self._task_cache)
                if not is_valid:
                    self._metrics['validation_errors'] += 1
                    raise TaskValidationError(f"Dependency validation failed: {', '.join(errors)}")
            
            return True
            
        except Exception as e:
            self._metrics['validation_errors'] += 1
            raise TaskValidationError(f"Task validation failed: {str(e)}")
    
    def _validate_task_transition(self, task_id: str, new_status: str) -> bool:
        """Validate a task status transition.
        
        Args:
            task_id: ID of the task to validate
            new_status: New status to validate
            
        Returns:
            True if valid
            
        Raises:
            TaskValidationError: If validation fails
        """
        try:
            # Get current task
            task = self._get_task(task_id)
            
            if not task:
                raise TaskValidationError(f"Task {task_id} not found")
            
            # Use TaskSchema for validation
            task_schema = TaskSchema()
            is_valid, errors = task_schema.validate_task_transition(task['status'], new_status)
            
            if not is_valid:
                self._metrics['validation_errors'] += 1
                raise TaskValidationError(f"Status transition validation failed: {', '.join(errors)}")
            
            return True
            
        except Exception as e:
            self._metrics['validation_errors'] += 1
            raise TaskValidationError(f"Status transition validation failed: {str(e)}")
    
    def _check_duplicate_task_id(self, task_id: str, tasks: List[Dict[str, Any]]) -> bool:
        """Check if a task ID already exists.
        
        Args:
            task_id: Task ID to check
            tasks: List of tasks to check against
            
        Returns:
            True if duplicate found
        """
        return any(task.get('task_id') == task_id for task in tasks)
    
    def detect_corruption(self, board_name: str) -> bool:
        """Detect if a task board is corrupted.
        
        Args:
            board_name: Name of the task board file
            
        Returns:
            True if corruption detected
        """
        board_path = self.task_dir / board_name
        
        if not board_path.exists():
            return False
            
        try:
            # Try to read and parse the file
            content = read_file(str(board_path))
            if not content.strip():
                return False
                
            tasks = json.loads(content)
            
            # Validate structure
            if not isinstance(tasks, list):
                return True
                
            # Validate each task
            for task in tasks:
                if not isinstance(task, dict):
                    return True
                if not self._validate_task(task):
                    return True
                    
            return False
            
        except Exception:
            return True
    
    def backup_task_board(self, board_name: str) -> Path:
        """Create a backup of a task board.
        
        Args:
            board_name: Name of the task board file
            
        Returns:
            Path to backup file
        """
        board_path = self.task_dir / board_name
        if not board_path.exists():
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{board_name}.{timestamp}.bak"
        
        try:
            shutil.copy2(board_path, backup_path)
            logger.info(f"Created backup of {board_name} at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup of {board_name}: {str(e)}")
            return None
    
    def restore_from_backup(self, board_name: str, backup_path: Optional[Path] = None) -> bool:
        """Restore a task board from backup.
        
        Args:
            board_name: Name of the task board file
            backup_path: Optional specific backup to restore from
            
        Returns:
            True if restore was successful
        """
        board_path = self.task_dir / board_name
        
        if not backup_path:
            # Find most recent backup
            backups = sorted(self.backup_dir.glob(f"{board_name}.*.bak"))
            if not backups:
                logger.error(f"No backups found for {board_name}")
                return False
            backup_path = backups[-1]
            
        try:
            shutil.copy2(backup_path, board_path)
            logger.info(f"Restored {board_name} from {backup_path}")
            # Invalidate cache after restore
            self._invalidate_cache(board_name)
            return True
        except Exception as e:
            logger.error(f"Failed to restore {board_name} from {backup_path}: {str(e)}")
            return False
    
    def read_task_board(self, board_name: str) -> List[Dict[str, Any]]:
        """Read a task board with file locking and corruption detection.
        
        Args:
            board_name: Name of the task board file
            
        Returns:
            List of tasks
            
        Raises:
            TaskBoardError: If the task board cannot be read
        """
        # Try to get from cache first
        cached_tasks = self._get_from_cache(board_name)
        if cached_tasks is not None:
            return cached_tasks
            
        board_path = self.task_dir / board_name
        
        # Log the transaction start
        self._log_transaction("read", board_name, status="started")
        
        # Check for corruption first
        if self.detect_corruption(board_name):
            logger.warning(f"Corruption detected in {board_name}, attempting repair")
            if not self.repair_task_board(board_name):
                error_message = f"Failed to repair corrupted task board {board_name}"
                logger.error(error_message)
                self._log_transaction("read", board_name, details={"error": error_message}, status="failed")
                raise TaskBoardError(error_message)
        
        # Acquire a shared lock (read-only)
        fd = None
        try:
            fd = self._acquire_lock(board_path, exclusive=False)
            
            # Read the file
            if not board_path.exists():
                # If the file doesn't exist, return an empty list
                logger.warning(f"Task board {board_name} does not exist, returning empty list")
                return []
            
            content = read_file(str(board_path))
            
            # Parse JSON
            if not content.strip():
                # Empty file, return empty list
                tasks = []
            else:
                try:
                    tasks = json.loads(content)
                    
                    # Ensure it's a list
                    if not isinstance(tasks, list):
                        raise TaskBoardError(f"Invalid task board format: expected list, got {type(tasks).__name__}")
                    
                except json.JSONDecodeError as e:
                    # Create a backup of the corrupted file
                    backup_path = self.backup_task_board(board_name)
                    
                    error_message = f"Corrupted task board {board_name} (backed up to {backup_path}): {str(e)}"
                    logger.error(error_message)
                    
                    self._log_transaction("read", board_name, details={"error": error_message}, status="failed")
                    raise TaskBoardError(error_message)
            
            # Update cache
            self._update_cache(board_name, tasks)
            
            # Log successful transaction
            self._log_transaction("read", board_name, details={"task_count": len(tasks)}, status="success")
            
            self._metrics['read_operations'] += 1
            return tasks
            
        except Exception as e:
            if not isinstance(e, TaskBoardError):
                error_message = f"Error reading task board {board_name}: {str(e)}"
                logger.error(error_message)
                self._log_transaction("read", board_name, details={"error": str(e)}, status="failed")
                raise TaskBoardError(error_message)
            raise
        
        finally:
            # Release the lock
            if fd is not None:
                self._release_lock(fd)
    
    def write_task_board(self, board_name: str, tasks: List[Dict[str, Any]]) -> bool:
        """Write to a task board with file locking and validation.
        
        Args:
            board_name: Name of the task board file
            tasks: List of tasks to write
            
        Returns:
            True if write was successful
            
        Raises:
            TaskBoardError: If the task board cannot be written
            TaskValidationError: If task validation fails
        """
        board_path = self.task_dir / board_name
        
        # Log the transaction start
        self._log_transaction("write", board_name, status="started")
        
        # Validate all tasks
        for task in tasks:
            try:
                self._validate_task(task)
            except TaskValidationError as e:
                error_message = f"Task validation failed: {str(e)}"
                logger.error(error_message)
                self._log_transaction("write", board_name, details={"error": error_message}, status="failed")
                raise
        
        # Create backup before writing
        backup_path = self.backup_task_board(board_name)
        
        # Acquire an exclusive lock
        fd = None
        temp_path = None
        try:
            fd = self._acquire_lock(board_path, exclusive=True)
            
            # Create temporary file
            temp_path = board_path.with_suffix('.tmp')
            
            # Write to temporary file
            write_file(str(temp_path), json.dumps(tasks, indent=2))
            
            # Atomic rename
            temp_path.replace(board_path)
            
            # Update cache
            self._update_cache(board_name, tasks)
            
            # Log successful transaction
            self._log_transaction("write", board_name, details={"task_count": len(tasks)}, status="success")
            
            self._metrics['write_operations'] += 1
            return True
            
        except Exception as e:
            error_message = f"Error writing task board {board_name}: {str(e)}"
            logger.error(error_message)
            self._log_transaction("write", board_name, details={"error": error_message}, status="failed")
            raise TaskBoardError(error_message)
            
        finally:
            # Release the lock
            if fd is not None:
                self._release_lock(fd)
            
            # Clean up temporary file if it exists
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
    
    def repair_task_board(self, board_name: str) -> bool:
        """Attempt to repair a corrupted task board.
        
        Args:
            board_name: Name of the task board file
            
        Returns:
            True if repair was successful
        """
        board_path = self.task_dir / board_name
        
        # Create backup of corrupted file
        backup_path = self.backup_task_board(board_name)
        if not backup_path:
            logger.error(f"Failed to create backup of corrupted board {board_name}")
            return False
            
        try:
            # Try to read the corrupted file
            content = read_file(str(board_path))
            if not content.strip():
                # Empty file, create new empty board
                write_file(str(board_path), "[]")
                return True
                
            # Try to parse JSON
            try:
                tasks = json.loads(content)
            except json.JSONDecodeError:
                # Invalid JSON, create new empty board
                write_file(str(board_path), "[]")
                return True
                
            # Validate structure
            if not isinstance(tasks, list):
                # Invalid structure, create new empty board
                write_file(str(board_path), "[]")
                return True
                
            # Filter out invalid tasks
            valid_tasks = []
            for task in tasks:
                if isinstance(task, dict):
                    try:
                        if self._validate_task(task):
                            valid_tasks.append(task)
                    except TaskValidationError:
                        continue
                        
            # Write repaired board
            write_file(str(board_path), json.dumps(valid_tasks, indent=2))
            
            # Update cache
            self._update_cache(board_name, valid_tasks)
            
            logger.info(f"Repaired task board {board_name}, kept {len(valid_tasks)} valid tasks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to repair task board {board_name}: {str(e)}")
            return False
            
    def get_metrics(self) -> Dict[str, int]:
        """Get performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self._metrics.copy()
        
    def reset_metrics(self):
        """Reset performance metrics."""
        self._metrics = {
            'read_operations': 0,
            'write_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'validation_errors': 0,
            'lock_timeouts': 0
        }

    def update_task_status(self, task_id: str, new_status: str, agent_id: str, details: Optional[str] = None) -> bool:
        """Update a task's status.
        
        Args:
            task_id: ID of the task to update
            new_status: New status
            agent_id: ID of the agent making the update
            details: Optional details about the update
            
        Returns:
            True if update was successful
            
        Raises:
            TaskValidationError: If validation fails
            TaskBoardError: If task board operations fail
        """
        try:
            # Validate status transition
            self._validate_task_transition(task_id, new_status)
            
            # Get task board
            task_board = self._get_task_board(task_id)
            if not task_board:
                raise TaskBoardError(f"Task board not found for task {task_id}")
                
            # Find task
            task = self._get_task(task_id)
            if not task:
                raise TaskBoardError(f"Task {task_id} not found")
                
            # Update status
            task['status'] = new_status
            task['history'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'agent': agent_id,
                'action': 'UPDATE',
                'details': f"Status changed to {new_status}. {details or ''}"
            })
            
            # Write updated task board
            self._write_task_board(task_board, task)
            
            return True
            
        except Exception as e:
            raise TaskBoardError(f"Failed to update task status: {str(e)}")
            
    def claim_task(self, task_id: str, agent_id: str) -> bool:
        """Claim a task for an agent.
        
        Args:
            task_id: ID of the task to claim
            agent_id: ID of the agent claiming the task
            
        Returns:
            True if claim was successful
            
        Raises:
            TaskValidationError: If validation fails
            TaskBoardError: If task board operations fail
        """
        try:
            # Validate status transition to IN_PROGRESS
            self._validate_task_transition(task_id, TASK_STATUS["IN_PROGRESS"])
            
            # Get task board
            task_board = self._get_task_board(task_id)
            if not task_board:
                raise TaskBoardError(f"Task board not found for task {task_id}")
                
            # Find task
            task = self._get_task(task_id)
            if not task:
                raise TaskBoardError(f"Task {task_id} not found")
                
            # Check if task is already claimed
            if task.get('assigned_to'):
                raise TaskValidationError(f"Task {task_id} is already claimed by {task['assigned_to']}")
                
            # Update task
            task['assigned_to'] = agent_id
            task['status'] = TASK_STATUS["IN_PROGRESS"]
            task['history'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'agent': agent_id,
                'action': 'CLAIMED',
                'details': f"Task claimed by {agent_id}"
            })
            
            # Write updated task board
            self._write_task_board(task_board, task)
            
            return True
            
        except Exception as e:
            raise TaskBoardError(f"Failed to claim task: {str(e)}")
            
    def complete_task(self, task_id: str, agent_id: str, details: Optional[str] = None) -> bool:
        """Mark a task as complete.
        
        Args:
            task_id: ID of the task to complete
            agent_id: ID of the agent completing the task
            details: Optional completion details
            
        Returns:
            True if completion was successful
            
        Raises:
            TaskValidationError: If validation fails
            TaskBoardError: If task board operations fail
        """
        try:
            # Validate status transition to COMPLETED
            self._validate_task_transition(task_id, TASK_STATUS["COMPLETED"])
            
            # Get task board
            task_board = self._get_task_board(task_id)
            if not task_board:
                raise TaskBoardError(f"Task board not found for task {task_id}")
                
            # Find task
            task = self._get_task(task_id)
            if not task:
                raise TaskBoardError(f"Task {task_id} not found")
                
            # Check if task is assigned to the agent
            if task.get('assigned_to') != agent_id:
                raise TaskValidationError(f"Task {task_id} is not assigned to agent {agent_id}")
                
            # Update task
            task['status'] = TASK_STATUS["COMPLETED"]
            task['history'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'agent': agent_id,
                'action': 'COMPLETED',
                'details': details or "Task completed successfully"
            })
            
            # Write updated task board
            self._write_task_board(task_board, task)
            
            return True
            
        except Exception as e:
            raise TaskBoardError(f"Failed to complete task: {str(e)}")
            
    def fail_task(self, task_id: str, agent_id: str, error_details: str) -> bool:
        """Mark a task as failed.
        
        Args:
            task_id: ID of the task to fail
            agent_id: ID of the agent failing the task
            error_details: Details about the failure
            
        Returns:
            True if failure was successful
            
        Raises:
            TaskValidationError: If validation fails
            TaskBoardError: If task board operations fail
        """
        try:
            # Validate status transition to FAILED
            self._validate_task_transition(task_id, TASK_STATUS["FAILED"])
            
            # Get task board
            task_board = self._get_task_board(task_id)
            if not task_board:
                raise TaskBoardError(f"Task board not found for task {task_id}")
                
            # Find task
            task = self._get_task(task_id)
            if not task:
                raise TaskBoardError(f"Task {task_id} not found")
                
            # Check if task is assigned to the agent
            if task.get('assigned_to') != agent_id:
                raise TaskValidationError(f"Task {task_id} is not assigned to agent {agent_id}")
                
            # Update task
            task['status'] = TASK_STATUS["FAILED"]
            task['history'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'agent': agent_id,
                'action': 'FAILED',
                'details': f"Task failed: {error_details}"
            })
            
            # Write updated task board
            self._write_task_board(task_board, task)
            
            return True
            
        except Exception as e:
            raise TaskBoardError(f"Failed to mark task as failed: {str(e)}")
            
    def block_task(self, task_id: str, agent_id: str, blocker_details: str) -> bool:
        """Mark a task as blocked.
        
        Args:
            task_id: ID of the task to block
            agent_id: ID of the agent blocking the task
            blocker_details: Details about what is blocking the task
            
        Returns:
            True if blocking was successful
            
        Raises:
            TaskValidationError: If validation fails
            TaskBoardError: If task board operations fail
        """
        try:
            # Validate status transition to BLOCKED
            self._validate_task_transition(task_id, TASK_STATUS["BLOCKED"])
            
            # Get task board
            task_board = self._get_task_board(task_id)
            if not task_board:
                raise TaskBoardError(f"Task board not found for task {task_id}")
                
            # Find task
            task = self._get_task(task_id)
            if not task:
                raise TaskBoardError(f"Task {task_id} not found")
                
            # Check if task is assigned to the agent
            if task.get('assigned_to') != agent_id:
                raise TaskValidationError(f"Task {task_id} is not assigned to agent {agent_id}")
                
            # Update task
            task['status'] = TASK_STATUS["BLOCKED"]
            task['history'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'agent': agent_id,
                'action': 'BLOCKED',
                'details': f"Task blocked: {blocker_details}"
            })
            
            # Write updated task board
            self._write_task_board(task_board, task)
            
            return True
            
        except Exception as e:
            raise TaskBoardError(f"Failed to block task: {str(e)}")

# Example implementation for testing
if __name__ == "__main__":
    # Initialize task manager
    manager = TaskManager("runtime/agent_comms/project_boards")
    
    # Example task
    test_task = {
        "task_id": "TEST-001",
        "description": "Test task",
        "status": "pending",
        "priority": "medium"
    }
    
    # Test adding a task
    try:
        result = manager.add_task("test_board.json", test_task)
        print(f"Add task result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test reading a task board
    try:
        tasks = manager.read_task_board("test_board.json")
        print(f"Read {len(tasks)} tasks")
    except Exception as e:
        print(f"Error: {e}")
    
    # Verify boards
    report = manager.verify_all_boards()
    print(f"Verification report: {report}") 