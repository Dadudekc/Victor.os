"""
Base Agent implementation for Dream.OS.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

class Agent:
    """
    Base Agent class that provides core functionality for all agents in the system.
    """
    
    def __init__(
        self,
        name: str,
        capabilities: List[str],
        state_dir: Optional[Path] = None,
        log_level: int = logging.INFO
    ):
        """
        Initialize a new agent.
        
        Args:
            name: Unique identifier for the agent
            capabilities: List of capabilities this agent has
            state_dir: Directory to store agent state (optional)
            log_level: Logging level for the agent
        """
        self.name = name
        self.capabilities = set(capabilities)
        self.state_dir = state_dir or Path(f"runtime/agent_comms/agent_mailboxes/{name}/state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(f"dreamos.agent.{name}")
        self.logger.setLevel(log_level)
        
        # Initialize state
        self.state: Dict[str, Any] = {
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat(),
            "tasks_processed": 0,
            "errors": 0
        }
        
        self.logger.info(f"Agent {name} initialized with capabilities: {capabilities}")
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task and return the result.
        
        Args:
            task: Task to process
            
        Returns:
            Dict containing the result of task processing
        """
        try:
            self.logger.info(f"Processing task: {task.get('id', 'unknown')}")
            self.state["last_active"] = datetime.utcnow().isoformat()
            
            # Validate task
            if not self._validate_task(task):
                raise ValueError(f"Invalid task: {task}")
            
            # Process task based on type
            result = self._execute_task(task)
            
            # Update state
            self.state["tasks_processed"] += 1
            
            return {
                "status": "success",
                "task_id": task.get("id"),
                "result": result,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing task: {str(e)}")
            self.state["errors"] += 1
            
            return {
                "status": "error",
                "task_id": task.get("id"),
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def _validate_task(self, task: Dict[str, Any]) -> bool:
        """
        Validate that the agent can process this task.
        
        Args:
            task: Task to validate
            
        Returns:
            True if task is valid, False otherwise
        """
        # Check if task type is in capabilities
        task_type = task.get("type")
        if not task_type or task_type not in self.capabilities:
            self.logger.warning(f"Task type {task_type} not in capabilities")
            return False
            
        # Check required fields
        required_fields = ["id", "type", "parameters"]
        if not all(field in task for field in required_fields):
            self.logger.warning(f"Missing required fields in task: {task}")
            return False
            
        return True
    
    def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the task. To be implemented by subclasses.
        
        Args:
            task: Task to execute
            
        Returns:
            Result of task execution
        """
        raise NotImplementedError("Subclasses must implement _execute_task")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the agent.
        
        Returns:
            Current agent state
        """
        return self.state
    
    def save_state(self) -> None:
        """
        Save the current state to disk.
        """
        state_file = self.state_dir / "state.json"
        import json
        with open(state_file, "w") as f:
            json.dump(self.state, f, indent=2)
        self.logger.debug("State saved")
    
    def load_state(self) -> None:
        """
        Load state from disk.
        """
        state_file = self.state_dir / "state.json"
        if state_file.exists():
            import json
            with open(state_file, "r") as f:
                self.state = json.load(f)
            self.logger.debug("State loaded") 