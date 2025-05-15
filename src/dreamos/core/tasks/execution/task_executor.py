"""Task Executor for Dream.OS.

Handles the execution of tasks with proper tracking and error handling.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..nexus.task_nexus import Task, TaskNexus

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes tasks with proper tracking and error handling."""

    def __init__(self, task_nexus: TaskNexus):
        self.task_nexus = task_nexus
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}  # Track execution attempts
        logger.info("TaskExecutor initialized")

    async def execute_task(self, task_id: str, agent_id: str) -> bool:
        """Execute a task with proper tracking and error handling.
        
        Args:
            task_id: The ID of the task to execute
            agent_id: The ID of the agent executing the task
            
        Returns:
            bool: True if execution was successful, False otherwise
        """
        task = self.task_nexus.get_task_by_id(task_id)
        if not task:
            logger.error(f"Task {task_id} not found for execution")
            return False
            
        # Record execution attempt
        if task_id not in self.execution_history:
            self.execution_history[task_id] = []
        
        self.execution_history[task_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "attempt_number": len(self.execution_history[task_id]) + 1
        })
        
        try:
            # Update task status to IN_PROGRESS
            self.task_nexus.update_task_status(task_id, "in_progress")
            logger.info(f"Task {task_id} execution started by agent {agent_id}")
            
            # Execute task based on task type/payload
            # This will be customized based on task requirements
            execution_result = await self._execute_task_by_type(task)
            
            # Update task status based on execution result
            if execution_result.get("success", False):
                self.task_nexus.update_task_status(task_id, "completed", execution_result.get("result"))
                logger.info(f"Task {task_id} execution completed successfully")
                return True
            else:
                self.task_nexus.update_task_status(task_id, "failed", execution_result.get("error"))
                logger.warning(f"Task {task_id} execution failed: {execution_result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}", exc_info=True)
            self.task_nexus.update_task_status(task_id, "failed", {"error": str(e)})
            return False

    async def _execute_task_by_type(self, task: Task) -> Dict[str, Any]:
        """Execute a task based on its type and payload.
        
        Args:
            task: The task to execute
            
        Returns:
            Dict with keys:
                - success: bool indicating if execution was successful
                - result: Optional result data if successful
                - error: Optional error information if failed
        """
        # This is a placeholder implementation that should be extended
        # based on the actual task types in the system
        
        task_type = task.tags[0] if task.tags else "unknown"
        
        # For now, just simulate successful execution
        # In a real implementation, this would dispatch to different
        # execution handlers based on task type
        
        logger.info(f"Simulating execution of task type: {task_type}")
        
        # Placeholder for actual execution logic
        # In a real implementation, this would be replaced with actual task execution
        
        # Simulate successful execution
        return {
            "success": True,
            "result": {
                "execution_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": f"Simulated execution of task type: {task_type}"
            }
        }
        
    def get_execution_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get the execution history for a specific task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List of execution attempt records
        """
        return self.execution_history.get(task_id, [])
        
    def clear_execution_history(self, task_id: Optional[str] = None) -> None:
        """Clear execution history for a specific task or all tasks.
        
        Args:
            task_id: The ID of the task to clear history for, or None to clear all
        """
        if task_id:
            if task_id in self.execution_history:
                del self.execution_history[task_id]
                logger.debug(f"Cleared execution history for task {task_id}")
        else:
            self.execution_history = {}
            logger.debug("Cleared all execution history") 