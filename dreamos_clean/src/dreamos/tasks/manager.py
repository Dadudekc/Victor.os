"""
Task Manager implementation for Dream.OS.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path
import json
import uuid
from queue import PriorityQueue
from threading import Lock

class TaskManager:
    """
    Manages task execution and scheduling in the Dream.OS system.
    """
    
    def __init__(
        self,
        state_dir: Optional[Path] = None,
        log_level: int = logging.INFO
    ):
        """
        Initialize the task manager.
        
        Args:
            state_dir: Directory to store task state (optional)
            log_level: Logging level for the manager
        """
        self.state_dir = state_dir or Path("runtime/tasks")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger("dreamos.task_manager")
        self.logger.setLevel(log_level)
        
        # Initialize task queue
        self.task_queue: PriorityQueue = PriorityQueue()
        self.task_lock = Lock()
        
        # Task state
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.completed_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Load existing tasks
        self._load_tasks()
        
        self.logger.info("Task Manager initialized")
    
    def add_task(
        self,
        task_type: str,
        parameters: Dict[str, Any],
        priority: int = 0,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        Add a new task to the queue.
        
        Args:
            task_type: Type of task to add
            parameters: Task parameters
            priority: Task priority (lower number = higher priority)
            dependencies: List of task IDs this task depends on
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        task = {
            "id": task_id,
            "type": task_type,
            "parameters": parameters,
            "priority": priority,
            "dependencies": dependencies or [],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        with self.task_lock:
            self.tasks[task_id] = task
            self.task_queue.put((priority, task_id))
            self._save_tasks()
        
        self.logger.info(f"Added task {task_id} of type {task_type}")
        return task_id
    
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Get the next task to process.
        
        Returns:
            Next task to process, or None if no tasks available
        """
        with self.task_lock:
            if self.task_queue.empty():
                return None
                
            _, task_id = self.task_queue.get()
            task = self.tasks.get(task_id)
            
            if not task:
                return None
                
            # Check dependencies
            if task["dependencies"]:
                for dep_id in task["dependencies"]:
                    dep_task = self.completed_tasks.get(dep_id)
                    if not dep_task or dep_task["status"] != "completed":
                        # Put task back in queue
                        self.task_queue.put((task["priority"], task_id))
                        return None
            
            return task
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update the status of a task.
        
        Args:
            task_id: ID of task to update
            status: New status
            result: Task result (optional)
        """
        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                self.logger.warning(f"Task {task_id} not found")
                return
                
            task["status"] = status
            task["updated_at"] = datetime.utcnow().isoformat()
            
            if result:
                task["result"] = result
            
            if status == "completed":
                self.completed_tasks[task_id] = task
                del self.tasks[task_id]
            
            self._save_tasks()
            
        self.logger.info(f"Updated task {task_id} status to {status}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: ID of task to get
            
        Returns:
            Task if found, None otherwise
        """
        return self.tasks.get(task_id) or self.completed_tasks.get(task_id)
    
    def _save_tasks(self) -> None:
        """
        Save tasks to disk.
        """
        state = {
            "tasks": self.tasks,
            "completed_tasks": self.completed_tasks
        }
        
        state_file = self.state_dir / "tasks.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    def _load_tasks(self) -> None:
        """
        Load tasks from disk.
        """
        state_file = self.state_dir / "tasks.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                state = json.load(f)
                self.tasks = state.get("tasks", {})
                self.completed_tasks = state.get("completed_tasks", {})
                
            # Rebuild task queue
            for task in self.tasks.values():
                self.task_queue.put((task["priority"], task["id"])) 