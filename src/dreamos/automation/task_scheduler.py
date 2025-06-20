"""
Task Scheduler module for managing and executing scheduled tasks.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
import json
import uuid
import time
from croniter import croniter


class TaskStatus(Enum):
    """Status of a scheduled task."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    
    task_id: str
    name: str
    description: str
    function: Callable
    schedule: str  # Cron expression or interval
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    max_retries: int = 3
    retry_count: int = 0
    timeout: Optional[int] = None  # seconds
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskExecutor:
    """Executes individual tasks with timeout and retry logic."""
    
    def __init__(self):
        self.logger = logging.getLogger("TaskExecutor")
    
    async def execute_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a task with timeout and error handling."""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.utcnow()
        task.run_count += 1
        
        self.logger.info(f"Executing task {task.task_id}: {task.name}")
        
        try:
            # Execute task with timeout if specified
            if task.timeout:
                result = await asyncio.wait_for(
                    self._execute_with_retry(task),
                    timeout=task.timeout
                )
            else:
                result = await self._execute_with_retry(task)
            
            # Task completed successfully
            task.status = TaskStatus.COMPLETED
            task.result = {
                "status": "success",
                "result": result,
                "execution_time": datetime.utcnow(),
                "run_count": task.run_count
            }
            task.error = None
            task.retry_count = 0
            
            self.logger.info(f"Task {task.task_id} completed successfully")
            return task.result
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = f"Task timed out after {task.timeout} seconds"
            self.logger.error(f"Task {task.task_id} timed out")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.logger.error(f"Task {task.task_id} failed: {e}")
        
        # Handle retries
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            self.logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
        else:
            self.logger.error(f"Task {task.task_id} failed after {task.max_retries} retries")
        
        return {
            "status": "failed",
            "error": task.error,
            "retry_count": task.retry_count,
            "run_count": task.run_count
        }
    
    async def _execute_with_retry(self, task: ScheduledTask) -> Any:
        """Execute task with retry logic."""
        try:
            if asyncio.iscoroutinefunction(task.function):
                return await task.function(**task.parameters)
            else:
                # For synchronous functions, run in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, task.function, **task.parameters
                )
        except Exception as e:
            task.retry_count += 1
            if task.retry_count >= task.max_retries:
                raise
            else:
                # Wait before retry (exponential backoff)
                wait_time = 2 ** task.retry_count
                await asyncio.sleep(wait_time)
                return await self._execute_with_retry(task)


class TaskScheduler:
    """Main task scheduler for managing and executing scheduled tasks."""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.executor = TaskExecutor()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.logger = logging.getLogger("TaskScheduler")
        self.is_running = False
        
        # Statistics
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "running_tasks": 0,
            "pending_tasks": 0
        }
    
    def add_task(self, name: str, function: Callable, schedule: str,
                 description: str = "", priority: TaskPriority = TaskPriority.NORMAL,
                 timeout: Optional[int] = None, max_retries: int = 3,
                 parameters: Optional[Dict[str, Any]] = None,
                 tags: Optional[List[str]] = None) -> str:
        """Add a new scheduled task."""
        task_id = str(uuid.uuid4())
        
        # Validate cron expression
        try:
            croniter(schedule)
        except ValueError as e:
            raise ValueError(f"Invalid cron expression '{schedule}': {e}")
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            description=description,
            function=function,
            schedule=schedule,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
            parameters=parameters or {},
            tags=tags or []
        )
        
        # Calculate next run time
        task.next_run = self._calculate_next_run(task)
        
        self.tasks[task_id] = task
        self.stats["total_tasks"] += 1
        self.stats["pending_tasks"] += 1
        
        self.logger.info(f"Added task {task_id}: {name} (next run: {task.next_run})")
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        # Cancel if running
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        # Update statistics
        if task.status == TaskStatus.RUNNING:
            self.stats["running_tasks"] -= 1
        elif task.status == TaskStatus.PENDING:
            self.stats["pending_tasks"] -= 1
        
        del self.tasks[task_id]
        self.stats["total_tasks"] -= 1
        
        self.logger.info(f"Removed task {task_id}")
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a scheduled task."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.PAUSED
            self.stats["pending_tasks"] -= 1
            self.logger.info(f"Paused task {task_id}")
            return True
        
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.PENDING
            task.next_run = self._calculate_next_run(task)
            self.stats["pending_tasks"] += 1
            self.logger.info(f"Resumed task {task_id}")
            return True
        
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[ScheduledTask]:
        """Get all tasks with a specific status."""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_tag(self, tag: str) -> List[ScheduledTask]:
        """Get all tasks with a specific tag."""
        return [task for task in self.tasks.values() if tag in task.tags]
    
    def get_tasks_by_priority(self, priority: TaskPriority) -> List[ScheduledTask]:
        """Get all tasks with a specific priority."""
        return [task for task in self.tasks.values() if task.priority == priority]
    
    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """Calculate the next run time for a task."""
        if task.status == TaskStatus.PAUSED:
            return task.next_run or datetime.utcnow()
        
        # Use current time as base if no last run
        base_time = task.last_run or datetime.utcnow()
        
        try:
            cron = croniter(task.schedule, base_time)
            return cron.get_next(datetime)
        except Exception as e:
            self.logger.error(f"Error calculating next run for task {task.task_id}: {e}")
            return datetime.utcnow() + timedelta(hours=1)  # Default fallback
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a single task."""
        try:
            result = await self.executor.execute_task(task)
            
            # Update statistics
            if result["status"] == "success":
                self.stats["completed_tasks"] += 1
            else:
                self.stats["failed_tasks"] += 1
            
            # Calculate next run time
            if task.status == TaskStatus.COMPLETED:
                task.next_run = self._calculate_next_run(task)
                task.status = TaskStatus.PENDING
                self.stats["pending_tasks"] += 1
            
        except Exception as e:
            self.logger.error(f"Unexpected error executing task {task.task_id}: {e}")
            self.stats["failed_tasks"] += 1
        finally:
            # Remove from running tasks
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
                self.stats["running_tasks"] -= 1
    
    async def _check_and_execute_tasks(self):
        """Check for tasks that need to be executed."""
        current_time = datetime.utcnow()
        tasks_to_run = []
        
        # Find tasks that should run now
        for task in self.tasks.values():
            if (task.status == TaskStatus.PENDING and 
                task.next_run and 
                task.next_run <= current_time):
                tasks_to_run.append(task)
        
        # Sort by priority (highest first)
        tasks_to_run.sort(key=lambda t: t.priority.value, reverse=True)
        
        # Execute tasks (respecting concurrency limit)
        for task in tasks_to_run:
            if len(self.running_tasks) >= self.max_concurrent_tasks:
                break
            
            if task.task_id not in self.running_tasks:
                # Create async task for execution
                async_task = asyncio.create_task(self._execute_task(task))
                self.running_tasks[task.task_id] = async_task
                self.stats["running_tasks"] += 1
                self.stats["pending_tasks"] -= 1
    
    async def run(self):
        """Main scheduler loop."""
        self.logger.info("Starting Task Scheduler")
        self.is_running = True
        
        while self.is_running:
            try:
                await self._check_and_execute_tasks()
                
                # Clean up completed async tasks
                completed_tasks = []
                for task_id, async_task in self.running_tasks.items():
                    if async_task.done():
                        completed_tasks.append(task_id)
                
                for task_id in completed_tasks:
                    del self.running_tasks[task_id]
                
                # Sleep before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop the scheduler."""
        self.logger.info("Stopping Task Scheduler")
        self.is_running = False
        
        # Cancel all running tasks
        for task_id, async_task in self.running_tasks.items():
            async_task.cancel()
        
        self.running_tasks.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "scheduler_status": "running" if self.is_running else "stopped",
            "stats": self.stats.copy(),
            "task_status_counts": {
                status.value: len(self.get_tasks_by_status(status))
                for status in TaskStatus
            },
            "priority_counts": {
                priority.value: len(self.get_tasks_by_priority(priority))
                for priority in TaskPriority
            },
            "running_tasks": list(self.running_tasks.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_upcoming_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming tasks sorted by next run time."""
        pending_tasks = [task for task in self.tasks.values() 
                        if task.status == TaskStatus.PENDING and task.next_run]
        
        # Sort by next run time
        pending_tasks.sort(key=lambda t: t.next_run)
        
        # Return limited results
        return [
            {
                "task_id": task.task_id,
                "name": task.name,
                "next_run": task.next_run.isoformat(),
                "priority": task.priority.value,
                "tags": task.tags
            }
            for task in pending_tasks[:limit]
        ]
    
    def export_tasks(self) -> Dict[str, Any]:
        """Export all tasks for backup/restore."""
        return {
            "tasks": {
                task_id: {
                    "name": task.name,
                    "description": task.description,
                    "schedule": task.schedule,
                    "priority": task.priority.value,
                    "timeout": task.timeout,
                    "max_retries": task.max_retries,
                    "parameters": task.parameters,
                    "tags": task.tags,
                    "metadata": task.metadata
                }
                for task_id, task in self.tasks.items()
            },
            "export_timestamp": datetime.utcnow().isoformat()
        }
    
    def import_tasks(self, tasks_data: Dict[str, Any], 
                    function_registry: Dict[str, Callable]) -> List[str]:
        """Import tasks from exported data."""
        imported_task_ids = []
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            try:
                # Note: function_registry should map function names to actual functions
                function_name = task_data.get("function_name")
                if function_name not in function_registry:
                    self.logger.warning(f"Function {function_name} not found in registry")
                    continue
                
                function = function_registry[function_name]
                
                # Create task
                new_task_id = self.add_task(
                    name=task_data["name"],
                    function=function,
                    schedule=task_data["schedule"],
                    description=task_data.get("description", ""),
                    priority=TaskPriority(task_data.get("priority", TaskPriority.NORMAL.value)),
                    timeout=task_data.get("timeout"),
                    max_retries=task_data.get("max_retries", 3),
                    parameters=task_data.get("parameters", {}),
                    tags=task_data.get("tags", [])
                )
                
                imported_task_ids.append(new_task_id)
                
            except Exception as e:
                self.logger.error(f"Error importing task {task_id}: {e}")
        
        self.logger.info(f"Imported {len(imported_task_ids)} tasks")
        return imported_task_ids 