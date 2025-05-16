import asyncio
import logging
from dreamos.agents.loop.agent_loop import AgentLoop
from dreamos.agents.base_agent import BaseAgent
from dreamos.core.config import AppConfig
from dreamos.core.tasks.project_board_manager import ProjectBoardManager
from typing import Dict, Any

# Define a concrete agent for testing
class ConcreteAgent1(BaseAgent):
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id)
        # Add any specific initializations for Agent-1 if needed

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"Processing message: {message.get('type', 'unknown_type')}")
        # Simulate processing
        response_content = f"Agent-1 processed message type: {message.get('type', 'unknown_type')}"
        # Echo back or provide a stubbed response based on message type
        return {
            "status": "processed",
            "agent_id": self.agent_id,
            "response": response_content,
            "original_message_id": message.get("id")
        }

if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    agent_id = "Agent-1"
    config = AppConfig()
    # agent = BaseAgent(agent_id=agent_id) # Comment out direct BaseAgent instantiation
    agent = ConcreteAgent1(agent_id=agent_id) # Instantiate ConcreteAgent1
    pbm = ProjectBoardManager(config)

    loop = AgentLoop(
        agent=agent,
        config=config,
        pbm=pbm,
        agent_bus=None  # Optional unless THEA sync needed
    )

    # loop.run()  # Start the live loop
    asyncio.run(loop.run())  # Start the live loop 