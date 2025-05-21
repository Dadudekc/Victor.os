from datetime import datetime, timezone
from typing import Dict, Any
import logging
import uuid

from ..nexus.task_nexus import TaskNexus

logger = logging.getLogger(__name__)

class PendingTaskMonitor:
    def __init__(self, task_nexus: TaskNexus, config: Dict[str, Any]):
        self.task_nexus = task_nexus
        self.config = config
        self.last_check_time = datetime.now(timezone.utc)
        
    async def check_pending_tasks(self) -> None:
        """Check for tasks that have been in PENDING state for too long."""
        current_time = datetime.now(timezone.utc)
        pending_tasks = self.task_nexus.get_all_tasks(status="pending")
        
        for task in pending_tasks:
            # Parse the created_at timestamp
            try:
                created_at = datetime.fromisoformat(task.created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid timestamp format for task {task.task_id}")
                continue
                
            # Calculate time in PENDING state
            time_pending = current_time - created_at
            
            # Check if task has been pending for too long
            if time_pending.total_seconds() > self.config.get("pending_timeout_seconds", 3600):
                self._handle_stalled_task(task)
                
        self.last_check_time = current_time
        
    def _handle_stalled_task(self, task) -> None:
        """Handle a task that has been in PENDING state for too long."""
        escalation_strategy = self.config.get("escalation_strategy", "log_only")
        
        if escalation_strategy == "log_only":
            logger.warning(f"Task {task.task_id} has been PENDING for too long")
        elif escalation_strategy == "mark_stalled":
            self.task_nexus.update_task_status(task.task_id, "stalled")
        elif escalation_strategy == "reassign":
            # Logic to reassign the task to another agent
            self.task_nexus.update_task_status(task.task_id, "pending")  # Reset to pending
            # Clear claimed_by field if it exists
        elif escalation_strategy == "escalate":
            # Create a new escalation task
            escalation_task = {
                "task_id": f"escalation_{task.task_id}_{uuid.uuid4().hex[:8]}",
                "description": f"Investigate stalled task: {task.task_id}",
                "priority": "high",
                "tags": ["escalation", "stalled_task"],
                "related_task_id": task.task_id
            }
            self.task_nexus.add_task(escalation_task) 