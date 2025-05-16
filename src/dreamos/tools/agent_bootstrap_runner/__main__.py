"""
Main entry point for Dream.OS Universal Agent Bootstrap Runner.
"""

import asyncio
import logging
import sys
from pathlib import Path

from dreamos.tools.agent_bootstrap_runner.config import AgentConfig
from dreamos.tools.agent_bootstrap_runner.task_manager import TaskManager
from dreamos.tools.agent_bootstrap_runner.consensus import ConsensusManager
from dreamos.core.coordination.agent_bus import AgentBus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("runtime/devlog/agents/bootstrap.log")
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the bootstrap runner."""
    try:
        # Initialize components
        workspace_path = Path("runtime")
        agent_bus = AgentBus()
        
        # Create agent config
        config = AgentConfig(
            agent_id="Agent-0",  # Coordinator agent
            prompt_dir="runtime/prompts",
            heartbeat_sec=30,
            loop_delay_sec=5,
            response_wait_sec=15,
            retrieve_retries=3,
            retry_delay_sec=2,
            startup_delay_sec=30
        )
        
        # Create task manager
        task_manager = TaskManager(workspace_path)
        
        # Create consensus manager with config
        consensus_manager = ConsensusManager(agent_bus, config)
        
        # Start agent bus
        await agent_bus.start()
        
        # Start consensus manager
        await consensus_manager.start()
        
        # Main loop
        while True:
            try:
                # Check for pending tasks
                pending_tasks = task_manager.list_tasks(state="pending")
                if pending_tasks:
                    logger.info(f"Found {len(pending_tasks)} pending tasks")
                    # TODO: Process tasks
                
                # Wait before next check
                await asyncio.sleep(config.loop_delay_sec)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(config.retry_delay_sec)
                
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await consensus_manager.stop()

if __name__ == "__main__":
    asyncio.run(main()) 