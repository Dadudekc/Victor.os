"""
Task management system for agent bootstrap runner.
Handles task lifecycle, validation, and atomic operations.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from filelock import FileLock
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class TaskStatus(BaseModel):
    """Task status model."""
    state: Literal["pending", "ready", "working", "completed", "failed"]
    last_updated: str
    assigned_to: Optional[str] = None
    progress: float = 0.0
    error: Optional[str] = None

class TaskMetadata(BaseModel):
    """Task metadata model."""
    created_by: str
    created_at: str
    priority: int = Field(default=1, ge=1, le=5)
    tags: List[str] = Field(default_factory=list)
    points: int = Field(default=1, ge=1)

class Task(BaseModel):
    """Task model with full validation."""
    task_id: str
    title: str
    description: str
    status: TaskStatus
    metadata: TaskMetadata
    requirements: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)

class TaskManager:
    """
    Manages task lifecycle with atomic operations and validation.
    Handles task state transitions, persistence, and concurrent access.
    """

    def __init__(self, workspace_path: Path):
        """Initialize the task manager."""
        self.workspace_path = workspace_path
        self.tasks_dir = workspace_path / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
        # Create task state directories
        self.pending_dir = self.tasks_dir / "pending"
        self.ready_dir = self.tasks_dir / "ready"
        self.working_dir = self.tasks_dir / "working"
        self.completed_dir = self.tasks_dir / "completed"
        
        for dir_path in [self.pending_dir, self.ready_dir, self.working_dir, self.completed_dir]:
            dir_path.mkdir(exist_ok=True)
            
        # Create locks directory
        self.locks_dir = self.tasks_dir / "locks"
        self.locks_dir.mkdir(exist_ok=True)
        
        logger.info(f"TaskManager initialized at {workspace_path}")

    def _get_lock_path(self, task_id: str) -> Path:
        """Get the lock file path for a task."""
        return self.locks_dir / f"{task_id}.lock"

    def _get_task_path(self, task_id: str, state: str) -> Path:
        """Get the task file path based on its state."""
        state_dir = getattr(self, f"{state}_dir")
        return state_dir / f"{task_id}.json"

    def _atomic_read(self, file_path: Path) -> Dict[str, Any]:
        """Read a file atomically with locking."""
        if not file_path.exists():
            raise FileNotFoundError(f"Task file not found: {file_path}")
            
        lock = FileLock(self._get_lock_path(file_path.stem))
        try:
            with lock:
                with open(file_path, "r") as f:
                    return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task file {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading task file {file_path}: {e}")
            raise

    def _atomic_write(self, file_path: Path, data: Dict[str, Any]):
        """Write data atomically with locking."""
        lock = FileLock(self._get_lock_path(file_path.stem))
        try:
            with lock:
                # Write to temporary file first
                temp_path = file_path.with_suffix(".tmp")
                with open(temp_path, "w") as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Atomic rename
                temp_path.replace(file_path)
        except Exception as e:
            logger.error(f"Error writing task file {file_path}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise

    def create_task(
        self,
        title: str,
        description: str,
        created_by: str,
        priority: int = 1,
        tags: List[str] = None,
        points: int = 1,
        requirements: Dict[str, Any] = None
    ) -> Task:
        """
        Create a new task in pending state.
        
        Args:
            title: Task title
            description: Task description
            created_by: ID of creating agent
            priority: Task priority (1-5)
            tags: List of task tags
            points: Task points value
            requirements: Task requirements
            
        Returns:
            Task: The created task
        """
        task_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            status=TaskStatus(
                state="pending",
                last_updated=now
            ),
            metadata=TaskMetadata(
                created_by=created_by,
                created_at=now,
                priority=priority,
                tags=tags or [],
                points=points
            ),
            requirements=requirements or {},
            artifacts={}
        )
        
        # Validate and save
        task_dict = task.model_dump()
        task_path = self._get_task_path(task_id, "pending")
        self._atomic_write(task_path, task_dict)
        
        logger.info(f"Created new task {task_id}: {title}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID from any state."""
        for state in ["pending", "ready", "working", "completed"]:
            try:
                task_path = self._get_task_path(task_id, state)
                if task_path.exists():
                    data = self._atomic_read(task_path)
                    return Task(**data)
            except Exception as e:
                logger.error(f"Error reading task {task_id} from {state}: {e}")
                
        return None

    def list_tasks(self, state: Optional[str] = None) -> List[Task]:
        """
        List tasks, optionally filtered by state.
        
        Args:
            state: Optional state filter
            
        Returns:
            List[Task]: List of matching tasks
        """
        tasks = []
        states = [state] if state else ["pending", "ready", "working", "completed"]
        
        for s in states:
            state_dir = getattr(self, f"{s}_dir")
            for task_file in state_dir.glob("*.json"):
                try:
                    data = self._atomic_read(task_file)
                    task = Task(**data)
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"Error reading task file {task_file}: {e}")
                    
        return tasks

    def update_task(
        self,
        task_id: str,
        updates: Dict[str, Any],
        agent_id: str
    ) -> Optional[Task]:
        """
        Update a task with validation.
        
        Args:
            task_id: Task ID
            updates: Update dictionary
            agent_id: ID of updating agent
            
        Returns:
            Task: Updated task or None if not found
        """
        task = self.get_task(task_id)
        if not task:
            return None
            
        # Validate updates
        if "status" in updates:
            updates["status"]["last_updated"] = datetime.now(timezone.utc).isoformat()
            
        # Update task
        task_dict = task.model_dump()
        task_dict.update(updates)
        
        # Validate updated task
        updated_task = Task(**task_dict)
        
        # Handle state transition
        old_state = task.status.state
        new_state = updated_task.status.state
        
        if old_state != new_state:
            # Move task file
            old_path = self._get_task_path(task_id, old_state)
            new_path = self._get_task_path(task_id, new_state)
            
            # Write to new location
            self._atomic_write(new_path, task_dict)
            
            # Remove from old location
            try:
                old_path.unlink()
            except Exception as e:
                logger.error(f"Error removing old task file {old_path}: {e}")
        else:
            # Update in place
            task_path = self._get_task_path(task_id, old_state)
            self._atomic_write(task_path, task_dict)
            
        logger.info(f"Updated task {task_id} by {agent_id}")
        return updated_task

    def transition_task(
        self,
        task_id: str,
        new_state: str,
        agent_id: str,
        updates: Dict[str, Any] = None
    ) -> Optional[Task]:
        """
        Transition a task to a new state.
        
        Args:
            task_id: Task ID
            new_state: Target state
            agent_id: ID of transitioning agent
            updates: Optional additional updates
            
        Returns:
            Task: Updated task or None if not found
        """
        updates = updates or {}
        updates["status"] = {
            "state": new_state,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "assigned_to": agent_id if new_state == "working" else None
        }
        
        return self.update_task(task_id, updates, agent_id)

    def delete_task(self, task_id: str, agent_id: str) -> bool:
        """
        Delete a task.
        
        Args:
            task_id: Task ID
            agent_id: ID of deleting agent
            
        Returns:
            bool: True if deleted
        """
        task = self.get_task(task_id)
        if not task:
            return False
            
        # Remove task file
        task_path = self._get_task_path(task_id, task.status.state)
        try:
            task_path.unlink()
            logger.info(f"Deleted task {task_id} by {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False

    def claim_task(self, task_id: str, agent_id: str) -> Optional[Task]:
        """
        Claim a ready task for work.
        
        Args:
            task_id: Task ID
            agent_id: ID of claiming agent
            
        Returns:
            Task: Claimed task or None if not available
        """
        task = self.get_task(task_id)
        if not task or task.status.state != "ready":
            return None
            
        return self.transition_task(
            task_id,
            "working",
            agent_id,
            {
                "status": {
                    "progress": 0.0
                }
            }
        )

    def complete_task(
        self,
        task_id: str,
        agent_id: str,
        artifacts: Dict[str, Any] = None
    ) -> Optional[Task]:
        """
        Mark a task as completed.
        
        Args:
            task_id: Task ID
            agent_id: ID of completing agent
            artifacts: Optional task artifacts
            
        Returns:
            Task: Completed task or None if not found
        """
        updates = {}
        if artifacts:
            updates["artifacts"] = artifacts
            
        return self.transition_task(task_id, "completed", agent_id, updates)

    def fail_task(
        self,
        task_id: str,
        agent_id: str,
        error: str,
        artifacts: Dict[str, Any] = None
    ) -> Optional[Task]:
        """
        Mark a task as failed.
        
        Args:
            task_id: Task ID
            agent_id: ID of failing agent
            error: Error message
            artifacts: Optional task artifacts
            
        Returns:
            Task: Failed task or None if not found
        """
        updates = {
            "status": {
                "error": error
            }
        }
        if artifacts:
            updates["artifacts"] = artifacts
            
        return self.transition_task(task_id, "failed", agent_id, updates) 