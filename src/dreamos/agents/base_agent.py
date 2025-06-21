from abc import ABC
from typing import Dict, Any
from datetime import datetime
import os
import json

class BaseAgent(ABC):
    def __init__(self, config: Dict[str, Any] = None, pbm=None):
        self.config = config or {}
        self.pbm = pbm
        self.agent_id = getattr(config, 'agent_id', None) if config else "default_agent"
        self.mailbox_path = getattr(config, 'mailbox_path', None) if config else None
        self.episode_path = getattr(config, 'episode_path', None) if config else None
        
        # Validate configuration
        self._validate_config()
        
        self.name = self.agent_id
        self.status = "idle"
        self.current_task = None
        self.error_count = 0
        self.retry_count = 0
        self.is_processing = False
        self.last_activity = datetime.utcnow()
        self._active_tasks: Dict[str, Any] = {}
        
        # Create mailbox files if mailbox_path is provided
        if self.mailbox_path:
            self._create_mailbox_files()
    
    def _validate_config(self):
        """Validate the configuration."""
        if not self.agent_id:
            raise ValueError("agent_id is required")
        
        if not self.mailbox_path:
            raise ValueError("mailbox_path is required")
        
        if not self.episode_path:
            raise ValueError("episode_path is required")
        
        # Check if paths are accessible - raise OSError for invalid paths
        if self.mailbox_path:
            try:
                os.makedirs(os.path.dirname(self.mailbox_path), exist_ok=True)
            except OSError:
                raise OSError(f"Cannot create mailbox directory: {self.mailbox_path}")
        
        if self.episode_path:
            try:
                os.makedirs(os.path.dirname(self.episode_path), exist_ok=True)
            except OSError:
                raise OSError(f"Cannot create episode directory: {self.episode_path}")
    
    def _create_mailbox_files(self):
        """Create mailbox files (inbox.json and outbox.json)."""
        try:
            # Ensure directory exists
            os.makedirs(self.mailbox_path, exist_ok=True)
            
            # Create inbox.json
            inbox_path = os.path.join(self.mailbox_path, "inbox.json")
            if not os.path.exists(inbox_path):
                with open(inbox_path, 'w') as f:
                    json.dump([], f)
            
            # Create outbox.json
            outbox_path = os.path.join(self.mailbox_path, "outbox.json")
            if not os.path.exists(outbox_path):
                with open(outbox_path, 'w') as f:
                    json.dump([], f)
                    
        except Exception as e:
            print(f"Error creating mailbox files: {e}")

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming message and return a response."""
        # Base implementation - to be overridden by concrete agent classes
        print(f"[BaseAgent {self.agent_id}] Received message: {message}")
        return {"status": "message_processed", "agent_id": self.agent_id, "original_message": message}

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task and return the result."""
        # Base implementation - to be overridden by concrete agent classes
        print(f"[BaseAgent {self.agent_id}] Executing task: {task}")
        return {"status": "task_executed", "agent_id": self.agent_id, "task": task}

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "current_task": self.current_task,
            "error_count": self.error_count
        }

    def update_status(self, status: str, current_task: Any = None):
        self.status = status
        self.current_task = current_task

    def increment_error_count(self):
        self.error_count += 1 