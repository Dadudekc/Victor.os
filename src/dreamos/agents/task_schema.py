"""
Task Schema Module

This module provides task validation and management functionality.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class TaskHistory(BaseModel):
    """Schema for task history entries."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent: str = Field(..., description="ID of the agent that performed the action")
    action: str = Field(..., description="Action performed (CLAIMED, UPDATED, COMPLETED, etc.)")
    details: Optional[str] = Field(None, description="Additional details about the action")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Task(BaseModel):
    """Schema for tasks in the system."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Short name/identifier for the task")
    description: str = Field(..., description="Detailed description of the task")
    priority: str = Field(..., description="Task priority (CRITICAL, HIGH, MEDIUM, LOW)")
    status: str = Field(default="PENDING", description="Current status of the task")
    assigned_to: Optional[str] = Field(None, description="ID of the agent assigned to the task")
    task_type: str = Field(..., description="Type of task (e.g., REFACTOR, IMPLEMENTATION, TESTING)")
    created_by: str = Field(..., description="ID of the agent that created the task")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the task")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks this task depends on")
    estimated_duration: Optional[str] = Field(None, description="Estimated time to complete")
    deadline: Optional[datetime] = Field(None, description="Task deadline if applicable")
    history: List[TaskHistory] = Field(default_factory=list, description="History of task actions")
    critical: bool = Field(default=False, description="Whether this is a critical task")
    parent_task_id: Optional[str] = Field(None, description="ID of parent task if this is a subtask")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def create_task(
    name: str,
    description: str,
    priority: str,
    task_type: str,
    created_by: str,
    tags: Optional[List[str]] = None,
    dependencies: Optional[List[str]] = None,
    estimated_duration: Optional[str] = None,
    deadline: Optional[datetime] = None,
    critical: bool = False,
    parent_task_id: Optional[str] = None
) -> Task:
    """Helper function to create a new task."""
    return Task(
        name=name,
        description=description,
        priority=priority,
        task_type=task_type,
        created_by=created_by,
        tags=tags or [],
        dependencies=dependencies or [],
        estimated_duration=estimated_duration,
        deadline=deadline,
        critical=critical,
        parent_task_id=parent_task_id
    )

# Task status constants
TASK_STATUS = {
    "PENDING": "PENDING",
    "IN_PROGRESS": "IN_PROGRESS",
    "COMPLETED": "COMPLETED",
    "FAILED": "FAILED",
    "BLOCKED": "BLOCKED"
}

# Task priority levels
TASK_PRIORITY = {
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW"
}

# Task types
TASK_TYPES = {
    "REFACTOR": "REFACTOR",
    "IMPLEMENTATION": "IMPLEMENTATION",
    "TESTING": "TESTING",
    "DOCUMENTATION": "DOCUMENTATION",
    "BUGFIX": "BUGFIX",
    "FEATURE": "FEATURE",
    "MAINTENANCE": "MAINTENANCE",
    "ANALYSIS": "ANALYSIS",
    "PLANNING": "PLANNING",
    "REVIEW": "REVIEW"
}

def update_task_status(task: Task, new_status: str, agent_id: str, details: Optional[str] = None) -> Task:
    """Update a task's status and add to history."""
    task.status = new_status
    task.history.append(TaskHistory(
        agent=agent_id,
        action="UPDATE",
        details=f"Status changed to {new_status}. {details or ''}"
    ))
    return task

def claim_task(task: Task, agent_id: str) -> Task:
    """Claim a task for an agent."""
    task.assigned_to = agent_id
    task.status = TASK_STATUS["IN_PROGRESS"]
    task.history.append(TaskHistory(
        agent=agent_id,
        action="CLAIMED",
        details=f"Task claimed by {agent_id}"
    ))
    return task

def complete_task(task: Task, agent_id: str, details: Optional[str] = None) -> Task:
    """Mark a task as complete."""
    task.status = TASK_STATUS["COMPLETED"]
    task.history.append(TaskHistory(
        agent=agent_id,
        action="COMPLETED",
        details=details or "Task completed successfully"
    ))
    return task

def fail_task(task: Task, agent_id: str, error_details: str) -> Task:
    """Mark a task as failed."""
    task.status = TASK_STATUS["FAILED"]
    task.history.append(TaskHistory(
        agent=agent_id,
        action="FAILED",
        details=f"Task failed: {error_details}"
    ))
    return task

def block_task(task: Task, agent_id: str, blocker_details: str) -> Task:
    """Mark a task as blocked."""
    task.status = TASK_STATUS["BLOCKED"]
    task.history.append(TaskHistory(
        agent=agent_id,
        action="BLOCKED",
        details=f"Task blocked: {blocker_details}"
    ))
    return task

class TaskSchema:
    """Task schema for validation and management."""
    
    def __init__(self):
        """Initialize task schema."""
        self.logger = logging.getLogger(__name__)
        self.required_fields = {
            'task_id': str,
            'description': str,
            'type': str,
            'priority': str,
            'status': str
        }
        self.valid_types = ['migration', 'automation', 'integration', 'maintenance']
        self.valid_priorities = ['low', 'medium', 'high', 'critical']
        self.valid_statuses = ['pending', 'in_progress', 'completed', 'failed']
        
    def validate_task(self, task: Dict) -> bool:
        """Validate task against schema.
        
        Args:
            task: Task dictionary to validate
            
        Returns:
            bool: True if task is valid
        """
        try:
            # Check required fields
            for field, field_type in self.required_fields.items():
                if field not in task:
                    self.logger.error(f"Missing required field: {field}")
                    return False
                if not isinstance(task[field], field_type):
                    self.logger.error(f"Invalid type for field {field}: expected {field_type}")
                    return False
                    
            # Validate type
            if task['type'] not in self.valid_types:
                self.logger.error(f"Invalid task type: {task['type']}")
                return False
                
            # Validate priority
            if task['priority'] not in self.valid_priorities:
                self.logger.error(f"Invalid priority: {task['priority']}")
                return False
                
            # Validate status
            if task['status'] not in self.valid_statuses:
                self.logger.error(f"Invalid status: {task['status']}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating task: {e}")
            return False
            
    def update_task_status(self, task_id: str, status: str, notes: str = "") -> bool:
        """Update task status in working tasks file.
        
        Args:
            task_id: ID of task to update
            status: New status
            notes: Optional completion notes
            
        Returns:
            bool: True if update was successful
        """
        try:
            # Load working tasks
            tasks_path = Path("runtime/agent_comms/agent_mailboxes/working_tasks.json")
            if not tasks_path.exists():
                self.logger.error("Working tasks file not found")
                return False
                
            with open(tasks_path, 'r') as f:
                tasks = json.load(f)
                
            # Find task in claimed tasks
            for agent_id, agent_tasks in tasks.get('claimed_tasks', {}).items():
                for task in agent_tasks:
                    if task['task_id'] == task_id:
                        # Update status
                        task['status'] = status
                        if status == 'completed':
                            task['completed_at'] = datetime.utcnow().isoformat()
                            task['completion_notes'] = notes
                        return True
                        
            self.logger.error(f"Task {task_id} not found in working tasks")
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating task status: {e}")
            return False
            
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task by ID.
        
        Args:
            task_id: ID of task to get
            
        Returns:
            Optional[Dict]: Task if found, None otherwise
        """
        try:
            # Load working tasks
            tasks_path = Path("runtime/agent_comms/agent_mailboxes/working_tasks.json")
            if not tasks_path.exists():
                self.logger.error("Working tasks file not found")
                return None
                
            with open(tasks_path, 'r') as f:
                tasks = json.load(f)
                
            # Find task in claimed tasks
            for agent_id, agent_tasks in tasks.get('claimed_tasks', {}).items():
                for task in agent_tasks:
                    if task['task_id'] == task_id:
                        return task
                        
            self.logger.error(f"Task {task_id} not found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting task: {e}")
            return None 