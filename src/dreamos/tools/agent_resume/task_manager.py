"""
Task Manager Module

Handles task tracking, status updates, and task lifecycle management.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
import json

logger = logging.getLogger('task_manager')

class TaskManager:
    def __init__(self, status_dir: Path):
        self.status_dir = status_dir
        self.current_task = "RESUME-001"
        self.task_status = {
            "onboarding": False,
            "organization": False,
            "monitoring": False,
            "maintenance": False,
            "feedback": False
        }
        self.last_update = datetime.now(timezone.utc)
        
    def update_task_status(self, agent_id: str, component: str, status: bool) -> dict:
        """Update task status and return status message."""
        self.task_status[component] = status
        self.last_update = datetime.now(timezone.utc)
        
        # Update status file
        self._update_status_file(agent_id)
        
        return {
            "task_id": self.current_task,
            "component": component,
            "status": status,
            "timestamp": self.last_update.isoformat()
        }
        
    def get_task_status(self, agent_id: str) -> dict:
        """Get current task status for an agent."""
        return {
            "task_id": self.current_task,
            "status": self.task_status,
            "last_update": self.last_update.isoformat()
        }
        
    def _update_status_file(self, agent_id: str):
        """Update agent's status file with task information."""
        try:
            status_file = self.status_dir / agent_id / "status.json"
            status_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing status or create new
            if status_file.exists():
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
            else:
                status_data = {
                    "agent_id": agent_id,
                    "status": "inactive",
                    "last_update": None,
                    "task_status": {}
                }
            
            # Update task status
            status_data["task_status"] = self.task_status
            status_data["last_update"] = self.last_update.isoformat()
            
            # Write updated status
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to update status file for {agent_id}: {e}") 