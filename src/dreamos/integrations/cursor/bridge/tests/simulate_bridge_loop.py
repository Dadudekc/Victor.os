"""Bridge Loop Simulator
====================

Simulates the bridge loop for testing without requiring actual Cursor/ChatGPT interaction.
Provides a controlled environment for testing the bridge's response handling and relay logic.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..feedback.thea_response_handler import TheaResponseHandler
from ..relay.response_relay import ResponseRelay
from ..schemas.thea_response_schema import TheaResponse, ResponseType, ResponseStatus

logger = logging.getLogger(__name__)


class BridgeSimulator:
    """Simulates the bridge loop for testing."""

    def __init__(
        self,
        test_dir: Path,
        num_agents: int = 3,
        response_delay: float = 1.0,
        error_rate: float = 0.1
    ):
        """Initialize the simulator.
        
        Args:
            test_dir: Directory for test files
            num_agents: Number of simulated agents
            response_delay: Delay before generating responses (seconds)
            error_rate: Probability of generating error responses
        """
        self.test_dir = Path(test_dir)
        self.num_agents = num_agents
        self.response_delay = response_delay
        self.error_rate = error_rate
        
        # Setup test directories
        self.outbox_dir = self.test_dir / "outbox"
        self.agent_inbox_base = self.test_dir / "agents"
        self.prompt_dir = self.test_dir / "prompts"
        
        for dir_path in [self.outbox_dir, self.agent_inbox_base, self.prompt_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Initialize components
        self.response_handler = TheaResponseHandler(self.outbox_dir)
        self.response_relay = ResponseRelay(
            outbox_dir=self.outbox_dir,
            agent_inbox_base=self.agent_inbox_base,
            poll_interval=0.5
        )
        
        logger.info(f"Initialized bridge simulator with {num_agents} agents")
        logger.info(f"Test directory: {test_dir}")

    def _generate_response(self, prompt: str, task_id: str) -> TheaResponse:
        """Generate a simulated THEA response.
        
        Args:
            prompt: The prompt to respond to
            task_id: ID of the task
            
        Returns:
            TheaResponse: Generated response
        """
        # Determine response type
        if random.random() < self.error_rate:
            response_type = ResponseType.TASK_ERROR
            status = ResponseStatus.ERROR
            response = "Simulated error response"
        else:
            response_type = ResponseType.TASK_COMPLETE
            status = ResponseStatus.SUCCESS
            response = f"Simulated successful response to: {prompt[:50]}..."
            
        # Generate next steps
        next_steps = [
            "Simulated next step 1",
            "Simulated next step 2"
        ] if response_type == ResponseType.TASK_COMPLETE else None
        
        return TheaResponse(
            type=response_type,
            task_id=task_id,
            status=status,
            response=response,
            next_steps=next_steps,
            source_chat_id=f"sim-chat-{random.randint(1000, 9999)}",
            metadata={
                "simulated": True,
                "response_time": time.time(),
                "prompt_length": len(prompt)
            }
        )

    def _create_test_prompt(self, agent_id: int) -> Dict:
        """Create a test prompt for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Dict: Prompt data
        """
        task_id = f"agent-{agent_id}_task-{random.randint(1000, 9999)}"
        prompt = f"Simulated prompt for {task_id}"
        
        prompt_data = {
            "task_id": task_id,
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id
        }
        
        # Write prompt to file
        prompt_file = self.prompt_dir / f"{task_id}.json"
        prompt_file.write_text(json.dumps(prompt_data, indent=2))
        
        return prompt_data

    async def simulate_prompt_processing(self, prompt_data: Dict):
        """Simulate processing a prompt and generating a response.
        
        Args:
            prompt_data: The prompt data to process
        """
        # Simulate processing delay
        await asyncio.sleep(self.response_delay)
        
        # Generate response
        response = self._generate_response(
            prompt_data["prompt"],
            prompt_data["task_id"]
        )
        
        # Process response
        self.response_handler.process_response(
            response.to_dict(),
            prompt_data["task_id"]
        )

    async def run_simulation(self, num_prompts: int = 10):
        """Run a simulation with multiple prompts.
        
        Args:
            num_prompts: Number of prompts to simulate
        """
        logger.info(f"Starting simulation with {num_prompts} prompts")
        
        # Create prompts
        prompts = [
            self._create_test_prompt(random.randint(1, self.num_agents))
            for _ in range(num_prompts)
        ]
        
        # Process prompts
        tasks = [
            self.simulate_prompt_processing(prompt)
            for prompt in prompts
        ]
        await asyncio.gather(*tasks)
        
        # Start response relay
        relay_task = asyncio.create_task(
            asyncio.to_thread(self.response_relay.run)
        )
        
        # Wait for relay to process responses
        await asyncio.sleep(self.response_delay * 2)
        
        # Stop relay
        relay_task.cancel()
        try:
            await relay_task
        except asyncio.CancelledError:
            pass
            
        logger.info("Simulation completed")


def main():
    """Run a test simulation."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Create simulator
    simulator = BridgeSimulator(
        test_dir=Path("runtime/test/bridge_sim"),
        num_agents=3,
        response_delay=0.5,
        error_rate=0.2
    )
    
    # Run simulation
    asyncio.run(simulator.run_simulation(num_prompts=5))


if __name__ == "__main__":
    main() 