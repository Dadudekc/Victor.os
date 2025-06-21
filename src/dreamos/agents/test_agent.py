"""
Test Agent for testing purposes
"""

from typing import Dict, Any
from .base_agent import BaseAgent

class TestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    def __init__(self, agent_id: str = None, config: Dict[str, Any] = None, pbm=None):
        super().__init__(agent_id, config, pbm)
        self.message_count = 0
    
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming message and return a response."""
        self.message_count += 1
        return {
            "status": "processed",
            "agent_id": self.agent_id,
            "message_count": self.message_count,
            "response": f"Test response to: {message.get('content', 'unknown')}"
        } 