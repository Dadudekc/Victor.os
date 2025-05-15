"""
ProjectBoardManager - Centralized Task Management System

This module provides a unified interface for managing tasks in the Dream.OS centralized task system.
It replaces the previous multi-file approach with a single task_board.json file.
"""

import json
import logging
import os
import sys
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# --- Configuration ---
CENTRAL_TASK_DIR = "runtime/central_tasks"
CENTRAL_TASK_FILE = "task_board.json"

# --- Exceptions ---
class ProjectBoardError(Exception):
    """Base exception for ProjectBoardManager errors."""
    pass

class TaskNotFoundError(ProjectBoardError):
    """Raised when a task cannot be found."""
    pass

class InvalidTaskDataError(ProjectBoardError):
    """Raised when task data is invalid."""
    pass

class FileOperationError(ProjectBoardError):
    """Raised when a file operation fails."""
    pass

# --- Logger Setup ---
logger = logging.getLogger(__name__)

class ProjectBoardManager:
    """
    Manages the centralized task board for Dream.OS.
    
    This class provides methods for:
    - Loading and saving tasks from/to the central task board
    - Adding, updating, claiming, and completing tasks
    - Filtering and searching tasks
    """
    
    def __init__(self, task_board_path: Optional[Path] = None):
        """
        Initialize the ProjectBoardManager.
        
        Args:
            task_board_path: Optional path to the task board file. If not provided,
                             the default path will be used.
        """
        self.task_board_path = task_board_path or Path(CENTRAL_TASK_DIR) / CENTRAL_TASK_FILE
        
        # Ensure the directory exists
        self.task_board_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty task board if it doesn't exist
        if not self.task_board_path.exists():
            try:
                with open(self.task_board_path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
                logger.info(f"Created new task board at {self.task_board_path}")
            except Exception as e:
                logger.error(f"Failed to create task board: {e}")
                raise FileOperationError(f"Failed to create task board: {e}")
    
    def _load_tasks(self) -> List[Dict[str, Any]]:
        """
        Load tasks from the task board file.
        
        Returns:
            List of task dictionaries.
        
        Raises:
            FileOperationError: If the file cannot be read or parsed.
        """
        try:
            if not self.task_board_path.exists():
                logger.warning(f"Task board file not found: {self.task_board_path}")
                return []
            
            with open(self.task_board_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
            
            if not isinstance(tasks, list):
                logger.error(f"Invalid task board format: expected list, got {type(tasks)}")
                return []
            
            return tasks
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task board: {e}")
            raise FileOperationError(f"Failed to parse task board: {e}")
        except Exception as e:
            logger.error(f"Failed to load task board: {e}")
            raise FileOperationError(f"Failed to load task board: {e}")
    
    def _save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        """
        Save tasks to the task board file.
        
        Args:
            tasks: List of task dictionaries to save.
        
        Returns:
            True if successful, False otherwise.
        
        Raises:
            FileOperationError: If the file cannot be written.
        """
        try:
            # Ensure the directory exists
            self.task_board_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write tasks to file
            with open(self.task_board_path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save task board: {e}")
            raise FileOperationError(f"Failed to save task board: {e}")
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        Get a task by ID.
        
        Args:
            task_id: The ID of the task to get.
        
        Returns:
            The task dictionary.
        
        Raises:
            TaskNotFoundError: If the task cannot be found.
        """
        tasks = self._load_tasks()
        
        for task in tasks:
            if task.get("task_id") == task_id:
                return task
        
        raise TaskNotFoundError(f"Task ID '{task_id}' not found.")
    
    def add_task(self, task_data: Dict[str, Any]) -> str:
        """
        Add a new task to the task board.
        
        Args:
            task_data: Dictionary containing task data.
        
        Returns:
            The ID of the newly added task.
        
        Raises:
            InvalidTaskDataError: If the task data is invalid.
            FileOperationError: If the task board cannot be updated.
        """
        # Validate required fields
        required_fields = ["task_id", "name", "description", "status", "priority"]
        for field in required_fields:
            if field not in task_data:
                raise InvalidTaskDataError(f"Missing required field: {field}")
        
        # Load existing tasks
        tasks = self._load_tasks()
        
        # Check for duplicate task_id
        if any(task.get("task_id") == task_data["task_id"] for task in tasks):
            raise InvalidTaskDataError(f"Task ID '{task_data['task_id']}' already exists.")
        
        # Add timestamp if not present
        if "created_at" not in task_data:
            task_data["created_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Add history entry if not present
        if "history" not in task_data or not isinstance(task_data["history"], list):
            task_data["history"] = []
        
        # Add creation history entry if not present
        if not any(entry.get("action") == "CREATED" for entry in task_data["history"]):
            task_data["history"].append({
                "timestamp": task_data["created_at"],
                "agent": task_data.get("created_by", "SYSTEM"),
                "action": "CREATED",
                "details": "Task created"
            })
        
        # Add task to board
        tasks.append(task_data)
        
        # Save updated task board
        self._save_tasks(tasks)
        
        return task_data["task_id"]
    
    def update_task(self, task_id: str, updates: Dict[str, Any], agent_id: Optional[str] = None) -> bool:
        """
        Update an existing task.
        
        Args:
            task_id: The ID of the task to update.
            updates: Dictionary containing fields to update.
            agent_id: Optional ID of the agent making the update.
        
        Returns:
            True if successful, False otherwise.
        
        Raises:
            TaskNotFoundError: If the task cannot be found.
            FileOperationError: If the task board cannot be updated.
        """
        # Load existing tasks
        tasks = self._load_tasks()
        
        # Find the task to update
        for i, task in enumerate(tasks):
            if task.get("task_id") == task_id:
                # Update task fields
                for key, value in updates.items():
                    # Don't update history directly
                    if key != "history":
                        task[key] = value
                
                # Add history entry for the update
                if "history" not in task or not isinstance(task["history"], list):
                    task["history"] = []
                
                # Add update history entry
                task["history"].append({
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "agent": agent_id or "SYSTEM",
                    "action": "UPDATED",
                    "details": f"Task updated: {', '.join(updates.keys())}"
                })
                
                # Update timestamp
                task["timestamp_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                
                # Save updated task board
                self._save_tasks(tasks)
                
                return True
        
        raise TaskNotFoundError(f"Task ID '{task_id}' not found.")
    
    def claim_task(self, task_id: str, agent_id: str) -> bool:
        """
        Claim a task for an agent.
        
        Args:
            task_id: The ID of the task to claim.
            agent_id: The ID of the agent claiming the task.
        
        Returns:
            True if successful, False otherwise.
        
        Raises:
            TaskNotFoundError: If the task cannot be found.
            FileOperationError: If the task board cannot be updated.
        """
        # Load existing tasks
        tasks = self._load_tasks()
        
        # Find the task to claim
        for task in tasks:
            if task.get("task_id") == task_id:
                # Update task status and assigned agent
                task["status"] = "WORKING"
                task["assigned_agent"] = agent_id
                task["claimed_by"] = agent_id
                task["timestamp_claimed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                task["timestamp_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                
                # Add history entry
                if "history" not in task or not isinstance(task["history"], list):
                    task["history"] = []
                
                task["history"].append({
                    "timestamp": task["timestamp_claimed_utc"],
                    "agent": agent_id,
                    "action": "CLAIMED",
                    "details": f"Task claimed by {agent_id}"
                })
                
                # Save updated task board
                self._save_tasks(tasks)
                
                return True
        
        raise TaskNotFoundError(f"Task ID '{task_id}' not found.")
    
    def complete_task(self, task_id: str, agent_id: str, result_summary: Optional[str] = None) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_id: The ID of the task to complete.
            agent_id: The ID of the agent completing the task.
            result_summary: Optional summary of the task result.
        
        Returns:
            True if successful, False otherwise.
        
        Raises:
            TaskNotFoundError: If the task cannot be found.
            FileOperationError: If the task board cannot be updated.
        """
        # Load existing tasks
        tasks = self._load_tasks()
        
        # Find the task to complete
        for task in tasks:
            if task.get("task_id") == task_id:
                # Update task status
                task["status"] = "COMPLETED"
                task["timestamp_completed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                task["timestamp_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                
                # Add result summary if provided
                if result_summary:
                    task["result_summary"] = result_summary
                
                # Add history entry
                if "history" not in task or not isinstance(task["history"], list):
                    task["history"] = []
                
                task["history"].append({
                    "timestamp": task["timestamp_completed_utc"],
                    "agent": agent_id,
                    "action": "COMPLETED",
                    "details": f"Task completed by {agent_id}" + (f": {result_summary}" if result_summary else "")
                })
                
                # Save updated task board
                self._save_tasks(tasks)
                
                return True
        
        raise TaskNotFoundError(f"Task ID '{task_id}' not found.")
    
    def list_tasks(self, status: Optional[str] = None, agent_id: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering.
        
        Args:
            status: Optional status to filter by.
            agent_id: Optional agent ID to filter by.
            priority: Optional priority to filter by.
        
        Returns:
            List of task dictionaries matching the filters.
        """
        tasks = self._load_tasks()
        filtered_tasks = tasks
        
        # Apply status filter
        if status:
            filtered_tasks = [t for t in filtered_tasks if t.get("status", "").upper() == status.upper()]
        
        # Apply agent filter
        if agent_id:
            filtered_tasks = [
                t for t in filtered_tasks 
                if t.get("assigned_agent") == agent_id or t.get("claimed_by") == agent_id
            ]
        
        # Apply priority filter
        if priority:
            filtered_tasks = [t for t in filtered_tasks if t.get("priority", "").upper() == priority.upper()]
        
        return filtered_tasks
    
    def list_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        List all pending tasks.
        
        Returns:
            List of pending task dictionaries.
        """
        return self.list_tasks(status="PENDING")
    
    def list_working_tasks(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all working tasks, optionally filtered by agent.
        
        Args:
            agent_id: Optional agent ID to filter by.
        
        Returns:
            List of working task dictionaries.
        """
        return self.list_tasks(status="WORKING", agent_id=agent_id)
    
    def list_completed_tasks(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all completed tasks, optionally filtered by agent.
        
        Args:
            agent_id: Optional agent ID to filter by.
        
        Returns:
            List of completed task dictionaries.
        """
        return self.list_tasks(status="COMPLETED", agent_id=agent_id)
    
    def search_tasks(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Search tasks for a query string in name, description, or notes.
        
        Args:
            query: The query string to search for.
            case_sensitive: Whether the search should be case-sensitive.
        
        Returns:
            List of task dictionaries matching the query.
        """
        tasks = self._load_tasks()
        results = []
        
        for task in tasks:
            # Fields to search in
            searchable_fields = [
                task.get("name", ""),
                task.get("description", ""),
                task.get("notes", ""),
                task.get("result_summary", "")
            ]
            
            # Convert to lowercase if case-insensitive search
            if not case_sensitive:
                query = query.lower()
                searchable_fields = [field.lower() if isinstance(field, str) else "" for field in searchable_fields]
            
            # Check if query is in any of the fields
            if any(query in field for field in searchable_fields):
                results.append(task)
        
        return results
    
    def delete_task(self, task_id: str, agent_id: Optional[str] = None) -> bool:
        """
        Delete a task from the task board.
        
        Args:
            task_id: The ID of the task to delete.
            agent_id: Optional ID of the agent deleting the task.
        
        Returns:
            True if successful, False otherwise.
        
        Raises:
            TaskNotFoundError: If the task cannot be found.
            FileOperationError: If the task board cannot be updated.
        """
        # Load existing tasks
        tasks = self._load_tasks()
        
        # Find the task to delete
        for i, task in enumerate(tasks):
            if task.get("task_id") == task_id:
                # Remove the task
                deleted_task = tasks.pop(i)
                
                # Save updated task board
                self._save_tasks(tasks)
                
                logger.info(f"Task {task_id} deleted by {agent_id or 'SYSTEM'}")
                
                return True
        
        raise TaskNotFoundError(f"Task ID '{task_id}' not found.")
    
    def generate_task_id(self, prefix: str = "TASK") -> str:
        """
        Generate a unique task ID.
        
        Args:
            prefix: Prefix for the task ID.
        
        Returns:
            A unique task ID.
        """
        import uuid
        return f"{prefix}-{uuid.uuid4().hex[:8]}"

# CLI Interface
def main():
    """CLI entry point for the ProjectBoardManager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage the Dream.OS centralized task board")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add task command
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("--task-id", help="Task ID (generated if not provided)")
    add_parser.add_argument("--name", required=True, help="Task name")
    add_parser.add_argument("--description", required=True, help="Task description")
    add_parser.add_argument("--status", default="PENDING", help="Task status")
    add_parser.add_argument("--priority", default="MEDIUM", help="Task priority")
    add_parser.add_argument("--agent", help="Assigned agent ID")
    add_parser.add_argument("--created-by", help="Creator agent ID")
    
    # Update task command
    update_parser = subparsers.add_parser("update", help="Update an existing task")
    update_parser.add_argument("task_id", help="Task ID to update")
    update_parser.add_argument("--name", help="Task name")
    update_parser.add_argument("--description", help="Task description")
    update_parser.add_argument("--status", help="Task status")
    update_parser.add_argument("--priority", help="Task priority")
    update_parser.add_argument("--agent", help="Assigned agent ID")
    update_parser.add_argument("--agent-id", help="Agent ID making the update")
    
    # Claim task command
    claim_parser = subparsers.add_parser("claim", help="Claim a task")
    claim_parser.add_argument("task_id", help="Task ID to claim")
    claim_parser.add_argument("agent_id", help="Agent ID claiming the task")
    
    # Complete task command
    complete_parser = subparsers.add_parser("complete", help="Mark a task as completed")
    complete_parser.add_argument("task_id", help="Task ID to complete")
    complete_parser.add_argument("agent_id", help="Agent ID completing the task")
    complete_parser.add_argument("--summary", help="Result summary")
    
    # Get task command
    get_parser = subparsers.add_parser("get", help="Get a task by ID")
    get_parser.add_argument("task_id", help="Task ID to get")
    
    # List tasks command
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--agent", help="Filter by agent ID")
    list_parser.add_argument("--priority", help="Filter by priority")
    
    # Search tasks command
    search_parser = subparsers.add_parser("search", help="Search tasks")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--case-sensitive", action="store_true", help="Case-sensitive search")
    
    # Delete task command
    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("task_id", help="Task ID to delete")
    delete_parser.add_argument("--agent-id", help="Agent ID deleting the task")
    
    args = parser.parse_args()
    
    # Initialize ProjectBoardManager
    pbm = ProjectBoardManager()
    
    try:
        if args.command == "add":
            task_data = {
                "task_id": args.task_id or pbm.generate_task_id(),
                "name": args.name,
                "description": args.description,
                "status": args.status,
                "priority": args.priority,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            
            if args.agent:
                task_data["assigned_agent"] = args.agent
            
            if args.created_by:
                task_data["created_by"] = args.created_by
            
            task_id = pbm.add_task(task_data)
            print(f"Task added with ID: {task_id}")
        
        elif args.command == "update":
            updates = {}
            
            if args.name:
                updates["name"] = args.name
            
            if args.description:
                updates["description"] = args.description
            
            if args.status:
                updates["status"] = args.status
            
            if args.priority:
                updates["priority"] = args.priority
            
            if args.agent:
                updates["assigned_agent"] = args.agent
            
            if updates:
                pbm.update_task(args.task_id, updates, args.agent_id)
                print(f"Task {args.task_id} updated")
            else:
                print("No updates specified")
        
        elif args.command == "claim":
            pbm.claim_task(args.task_id, args.agent_id)
            print(f"Task {args.task_id} claimed by {args.agent_id}")
        
        elif args.command == "complete":
            pbm.complete_task(args.task_id, args.agent_id, args.summary)
            print(f"Task {args.task_id} completed by {args.agent_id}")
        
        elif args.command == "get":
            task = pbm.get_task(args.task_id)
            print(json.dumps(task, indent=2))
        
        elif args.command == "list":
            tasks = pbm.list_tasks(args.status, args.agent, args.priority)
            print(json.dumps(tasks, indent=2))
        
        elif args.command == "search":
            tasks = pbm.search_tasks(args.query, args.case_sensitive)
            print(json.dumps(tasks, indent=2))
        
        elif args.command == "delete":
            pbm.delete_task(args.task_id, args.agent_id)
            print(f"Task {args.task_id} deleted")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()