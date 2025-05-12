"""
Task Management Module
Handles task distribution, execution, and monitoring.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Any] = {}
        self.inboxes: Dict[str, List[Dict[str, Any]]] = {}

    def initialize_tasks(self, task_board: Dict[str, Any]) -> bool:
        """Initialize tasks from task board."""
        try:
            self.tasks = task_board
            return self._create_inboxes()
        except Exception as e:
            logger.error(f"Error initializing tasks: {str(e)}")
            return False

    def _create_inboxes(self) -> bool:
        """Create agent inboxes for task distribution."""
        try:
            # Group tasks by owner
            tasks_by_owner = {}
            for task_id, task_data in self.tasks.items():
                owner = task_data['owner']
                if owner not in tasks_by_owner:
                    tasks_by_owner[owner] = []
                tasks_by_owner[owner].append({
                    'id': task_id,
                    **task_data
                })

            # Create inboxes
            for owner, tasks in tasks_by_owner.items():
                inbox_path = Path(f"runtime/inboxes/{owner}/inbox.json")
                inbox_path.parent.mkdir(parents=True, exist_ok=True)

                inbox_data = {
                    "agent_id": owner,
                    "tasks": tasks,
                    "last_updated": datetime.now().isoformat()
                }

                with open(inbox_path, 'w', encoding='utf-8') as f:
                    json.dump(inbox_data, f, indent=2)
                
                self.inboxes[owner] = tasks
                logger.info(f"Created inbox for {owner} with {len(tasks)} tasks")

            return True
        except Exception as e:
            logger.error(f"Error creating inboxes: {str(e)}")
            return False

    def get_agent_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get tasks assigned to an agent."""
        return self.inboxes.get(agent_id, [])

    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status in both task board and inbox."""
        try:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return False

            # Update task board
            self.tasks[task_id]['status'] = status

            # Update inbox
            owner = self.tasks[task_id]['owner']
            inbox_path = Path(f"runtime/inboxes/{owner}/inbox.json")
            
            if inbox_path.exists():
                with open(inbox_path, 'r', encoding='utf-8') as f:
                    inbox_data = json.load(f)
                
                for task in inbox_data['tasks']:
                    if task['id'] == task_id:
                        task['status'] = status
                        break
                
                with open(inbox_path, 'w', encoding='utf-8') as f:
                    json.dump(inbox_data, f, indent=2)

            logger.info(f"Updated task {task_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return False

    def start_execution(self) -> bool:
        """Start task execution."""
        try:
            # Log execution start
            logger.info("Starting task execution")
            
            # Initialize execution tracking
            execution_log = {
                "start_time": datetime.now().isoformat(),
                "tasks": {}
            }

            # Save execution log
            log_path = Path("runtime/logs/execution")
            log_path.mkdir(parents=True, exist_ok=True)
            
            with open(log_path / "current_execution.json", 'w', encoding='utf-8') as f:
                json.dump(execution_log, f, indent=2)

            return True
        except Exception as e:
            logger.error(f"Error starting execution: {str(e)}")
            return False

    def check_completion(self) -> bool:
        """Check if all tasks are completed."""
        try:
            for task_id, task in self.tasks.items():
                if task['status'] != "Done":
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking completion: {str(e)}")
            return False 