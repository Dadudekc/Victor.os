"""
Main entry point for Agent-3.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from dreamos.core.coordination.agent_bus import AgentBus
from .agent3 import Agent3
from .config import get_config

logger = logging.getLogger(__name__)

class Agent3Runner:
    """Runner for Agent-3."""
    
    def __init__(self):
        """Initialize the runner."""
        self.agent: Optional[Agent3] = None
        self.agent_bus: Optional[AgentBus] = None
        self.config = get_config()
        self._setup_logging()
        
    def _setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=self.config["logging"]["level"],
            format=self.config["logging"]["format"],
            filename=self.config["logging"]["file"]
        )
        
    async def start(self):
        """Start Agent-3."""
        try:
            # Initialize agent bus
            self.agent_bus = AgentBus()
            await self.agent_bus.start()
            
            # Initialize and start agent
            self.agent = Agent3(self.agent_bus, self.config)
            await self.agent.start()
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
            # Keep running until stopped
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting Agent-3: {e}")
            await self.stop()
            sys.exit(1)
            
    async def stop(self):
        """Stop Agent-3."""
        if self.agent:
            await self.agent.stop()
        if self.agent_bus:
            await self.agent_bus.stop()
            
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def handle_signal(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.stop())
            
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

def main():
    """Main entry point."""
    runner = Agent3Runner()
    
    try:
        asyncio.run(runner.start())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 