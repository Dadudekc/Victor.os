"""
Dream.OS Social Media Task Integration

This module provides integration between the social media lead discovery system
and the Dream.OS task management system. It ensures that leads discovered 
on social media are properly added to the central task board and can be
assigned to agents for processing.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
import os

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.integrations.social.task_integration")

# Constants
RUNTIME_DIR = Path("runtime")
TASKS_DIR = RUNTIME_DIR / "tasks"
TASK_BOARD_FILE = RUNTIME_DIR / "task_board.json"
WORKING_TASKS_FILE = RUNTIME_DIR / "working_tasks.json"
FUTURE_TASKS_FILE = RUNTIME_DIR / "future_tasks.json"

class SocialTaskIntegrator:
    """
    Integrates social media lead tasks into the Dream.OS task management system.
    """
    
    def __init__(self):
        """Initialize the social task integrator."""
        self._lock = threading.RLock()
    
    def scan_for_new_lead_tasks(self) -> List[Dict[str, Any]]:
        """
        Scan for newly created social media lead tasks.
        
        Returns:
            List of new lead task dictionaries
        """
        lead_tasks = []
        
        # Look for lead task files matching the pattern
        try:
            lead_task_files = list(TASKS_DIR.glob("LEAD-*-*.json"))
            
            for task_file in lead_task_files:
                try:
                    # Read the task file
                    with open(task_file, 'r') as f:
                        task_data = json.load(f)
                    
                    # Check if this is a new task
                    if self._is_new_task(task_data["task_id"]):
                        lead_tasks.append(task_data)
                except Exception as e:
                    logger.error(f"Error reading lead task file {task_file}: {e}")
            
            logger.info(f"Found {len(lead_tasks)} new social media lead tasks")
            return lead_tasks
        except Exception as e:
            logger.error(f"Error scanning for lead tasks: {e}")
            return []
    
    def _is_new_task(self, task_id: str) -> bool:
        """
        Check if a task is new by scanning existing task board files.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            True if the task is new, False otherwise
        """
        # Check if task exists in main task board
        if TASK_BOARD_FILE.exists():
            try:
                with open(TASK_BOARD_FILE, 'r') as f:
                    task_board = json.load(f)
                
                # Check each cursor agent's tasks
                for cursor_data in task_board.get("cursor_agents", {}).values():
                    if "tasks" in cursor_data:
                        if task_id in cursor_data["tasks"]:
                            return False
                            
                        # Check for current_task_id match
                        if cursor_data.get("current_task_id") == task_id:
                            return False
            except Exception as e:
                logger.error(f"Error checking task board for task {task_id}: {e}")
        
        # Check working tasks file
        if WORKING_TASKS_FILE.exists():
            try:
                with open(WORKING_TASKS_FILE, 'r') as f:
                    working_tasks = json.load(f)
                
                if task_id in working_tasks:
                    return False
            except Exception as e:
                logger.error(f"Error checking working tasks for task {task_id}: {e}")
        
        # Check future tasks file
        if FUTURE_TASKS_FILE.exists():
            try:
                with open(FUTURE_TASKS_FILE, 'r') as f:
                    future_tasks = json.load(f)
                
                if task_id in future_tasks:
                    return False
            except Exception as e:
                logger.error(f"Error checking future tasks for task {task_id}: {e}")
        
        return True
    
    def add_tasks_to_board(self, tasks: List[Dict[str, Any]]) -> int:
        """
        Add new tasks to the task board.
        
        Args:
            tasks: List of task dictionaries to add
            
        Returns:
            Number of tasks successfully added
        """
        if not tasks:
            return 0
            
        added_count = 0
        
        # Add tasks to the future tasks file (main entry point)
        if FUTURE_TASKS_FILE.exists():
            try:
                # Load existing future tasks
                with open(FUTURE_TASKS_FILE, 'r') as f:
                    future_tasks = json.load(f)
                
                # Debug the structure of future_tasks
                logger.info(f"Future tasks file structure: {type(future_tasks)}")
                
                # Ensure future_tasks is a dictionary
                if isinstance(future_tasks, list):
                    logger.info("Converting future_tasks from list to dictionary")
                    future_tasks_dict = {}
                    for i, task in enumerate(future_tasks):
                        if isinstance(task, dict) and "task_id" in task:
                            future_tasks_dict[task["task_id"]] = task
                        else:
                            future_tasks_dict[f"task_{i}"] = task
                    future_tasks = future_tasks_dict
                
                # Add new tasks
                for task in tasks:
                    task_id = task["task_id"]
                    if task_id not in future_tasks:
                        # Format the task for future_tasks.json format
                        future_tasks[task_id] = {
                            "name": task["name"],
                            "description": task["description"],
                            "priority": task["priority"],
                            "status": "PENDING",
                            "tags": task["tags"],
                            "source": "SOCIAL_MEDIA_LEAD",
                            "created_at": task["created_at"],
                            "lead_data": task["lead_data"]
                        }
                        added_count += 1
                        logger.info(f"Added task {task_id} to future tasks")
                
                # Save updated future tasks
                with open(FUTURE_TASKS_FILE, 'w') as f:
                    json.dump(future_tasks, f, indent=2)
                
                logger.info(f"Added {added_count} new lead tasks to future tasks file")
                return added_count
            except Exception as e:
                logger.error(f"Error adding lead tasks to future tasks file: {e}")
                # Let's check the format of the future tasks file
                try:
                    with open(FUTURE_TASKS_FILE, 'r') as f:
                        future_tasks_content = f.read()
                    logger.info(f"First 200 chars of future_tasks.json: {future_tasks_content[:200]}")
                except Exception as read_error:
                    logger.error(f"Error reading future tasks file: {read_error}")
        else:
            logger.error(f"Future tasks file not found: {FUTURE_TASKS_FILE}")
            
        # Fallback: save to working_tasks.json
        try:
            if WORKING_TASKS_FILE.exists():
                # Load existing working tasks
                with open(WORKING_TASKS_FILE, 'r') as f:
                    working_tasks = json.load(f)
                
                # Add new tasks
                for task in tasks:
                    task_id = task["task_id"]
                    if task_id not in working_tasks:
                        # Format the task for working_tasks.json format
                        working_tasks[task_id] = {
                            "name": task["name"],
                            "description": task["description"],
                            "priority": task["priority"],
                            "status": "PENDING",
                            "tags": task["tags"],
                            "source": "SOCIAL_MEDIA_LEAD",
                            "created_at": task["created_at"]
                        }
                        added_count += 1
                
                # Save updated working tasks
                with open(WORKING_TASKS_FILE, 'w') as f:
                    json.dump(working_tasks, f, indent=2)
                
                logger.info(f"Added {added_count} new lead tasks to working tasks file")
                return added_count
            else:
                logger.error(f"Working tasks file not found: {WORKING_TASKS_FILE}")
        except Exception as e:
            logger.error(f"Error adding lead tasks to working tasks file: {e}")
            
        return 0
    
    def assign_tasks_to_agent(self, tasks: List[Dict[str, Any]], agent_id: str) -> int:
        """
        Assign lead tasks to a specific agent by updating the task board.
        
        Args:
            tasks: List of task dictionaries to assign
            agent_id: ID of the agent to assign tasks to
            
        Returns:
            Number of tasks successfully assigned
        """
        if not tasks or not agent_id:
            return 0
            
        assigned_count = 0
        
        # Update the task board file
        if TASK_BOARD_FILE.exists():
            try:
                # Load existing task board
                with open(TASK_BOARD_FILE, 'r') as f:
                    task_board = json.load(f)
                
                # Find the agent in the task board
                if agent_id in task_board.get("cursor_agents", {}):
                    agent_data = task_board["cursor_agents"][agent_id]
                    
                    # Ensure agent has a tasks dictionary
                    if "tasks" not in agent_data:
                        agent_data["tasks"] = {}
                    
                    # Add new tasks
                    for task in tasks:
                        task_id = task["task_id"]
                        if task_id not in agent_data["tasks"]:
                            # Format task for task board format
                            agent_data["tasks"][task_id] = {
                                "description": task["description"],
                                "status": "PENDING",
                                "last_updated": datetime.now().isoformat(),
                                "source": "SOCIAL_MEDIA_LEAD"
                            }
                            assigned_count += 1
                            
                            # Also update the task file with the assignment
                            task_file = TASKS_DIR / f"{task_id}.json"
                            if task_file.exists():
                                try:
                                    with open(task_file, 'r') as f:
                                        task_data = json.load(f)
                                    
                                    # Update assigned_to field
                                    task_data["assigned_to"] = agent_id
                                    task_data["history"].append({
                                        "timestamp": datetime.now().isoformat(),
                                        "agent": "SocialTaskIntegrator",
                                        "action": "ASSIGNED",
                                        "details": f"Task assigned to {agent_id}"
                                    })
                                    
                                    with open(task_file, 'w') as f:
                                        json.dump(task_data, f, indent=2)
                                except Exception as e:
                                    logger.error(f"Error updating task file {task_file}: {e}")
                    
                    # Update last updated timestamp
                    task_board["last_updated_utc"] = datetime.now().isoformat()
                    
                    # Save updated task board
                    with open(TASK_BOARD_FILE, 'w') as f:
                        json.dump(task_board, f, indent=2)
                    
                    logger.info(f"Assigned {assigned_count} lead tasks to agent {agent_id}")
                else:
                    logger.error(f"Agent {agent_id} not found in task board")
            except Exception as e:
                logger.error(f"Error assigning lead tasks to agent {agent_id}: {e}")
        else:
            logger.error(f"Task board file not found: {TASK_BOARD_FILE}")
            
        return assigned_count

    def run_integration_cycle(self, agent_id: Optional[str] = None) -> int:
        """
        Run a complete integration cycle to find and add new lead tasks.
        
        Args:
            agent_id: Optional agent ID to assign tasks to
            
        Returns:
            Number of tasks processed
        """
        with self._lock:
            # Scan for new lead tasks
            new_tasks = self.scan_for_new_lead_tasks()
            
            if not new_tasks:
                logger.info("No new lead tasks found")
                return 0
                
            # Add tasks to board
            added_count = self.add_tasks_to_board(new_tasks)
            
            # Assign tasks if agent specified
            if agent_id and added_count > 0:
                self.assign_tasks_to_agent(new_tasks, agent_id)
                
            return added_count

def integrate_social_tasks(agent_id: Optional[str] = None) -> int:
    """
    Convenience function to run a task integration cycle.
    
    Args:
        agent_id: Optional agent ID to assign tasks to
        
    Returns:
        Number of tasks processed
    """
    integrator = SocialTaskIntegrator()
    return integrator.run_integration_cycle(agent_id)

if __name__ == "__main__":
    # Example usage
    agent_id = os.environ.get("DREAMOS_LEAD_AGENT_ID", "cursor_6")
    task_count = integrate_social_tasks(agent_id)
    print(f"Processed {task_count} social media lead tasks") 