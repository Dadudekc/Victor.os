from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.name = agent_id
        self.status = "idle"
        self.current_task = None
        self.error_count = 0
        self._active_tasks: Dict[str, Any] = {}

    @abstractmethod
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming message and return a response."""
        # Base implementation - to be overridden by concrete agent classes
        print(f"[BaseAgent {self.agent_id}] Received message: {message}")
        return {"status": "message_processed", "agent_id": self.agent_id, "original_message": message}

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