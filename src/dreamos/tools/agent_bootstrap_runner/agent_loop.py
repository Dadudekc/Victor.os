"""
Agent loop implementation for Dream.OS
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.config import AppConfig
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

from .config import AgentConfig
from .messaging import create_seed_inbox, update_inbox_with_prompt
from .validation import validate_all_files

class AgentLoopManager:
    """Manages the main agent loop."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"loop.{config.agent_id}")
        self.app_config = AppConfig()
        self.agent_bus = AgentBus()
        
        # Initialize UI components
        self.injector = CursorInjector(
            agent_id=config.agent_id,
            coords_file=str(config.coords_file)
        )
        self.retriever = ResponseRetriever(
            agent_id=config.agent_id_for_retriever,
            coords_file=str(config.copy_coords_file)
        )
        
    async def run(self, run_once: bool = False) -> bool:
        """
        Run the agent loop.
        
        Args:
            run_once: If True, run one cycle then exit
            
        Returns:
            bool: True if loop completed successfully
        """
        try:
            # Validate setup
            validation = validate_all_files(self.logger, self.config)
            if not validation.passed:
                self.logger.error(f"Validation failed: {validation.error}")
                return False
                
            # Optional startup delay
            if self.config.startup_delay_sec > 0:
                self.logger.info(f"Startup delay: {self.config.startup_delay_sec}s")
                await asyncio.sleep(self.config.startup_delay_sec)
                
            while True:
                # Run one cycle
                await self.run_cycle()
                
                if run_once:
                    break
                    
                # Loop delay
                await asyncio.sleep(self.config.loop_delay_sec)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Agent loop failed: {e}")
            return False
            
    async def run_cycle(self) -> None:
        """Run one cycle of the agent loop."""
        try:
            # Create seed inbox if needed
            create_seed_inbox(self.logger, self.config)
            
            # Load messages
            from .messaging import load_inbox
            messages = load_inbox(self.logger, self.config)
            
            if not messages:
                self.logger.info("No messages in inbox")
                return
                
            # Process each message
            for message in messages:
                prompt = message.get("prompt", "")
                if not prompt:
                    continue
                    
                # Inject prompt
                self.injector.inject(prompt)
                
                # Wait for and retrieve response
                response = None
                for _ in range(self.config.retrieve_retries):
                    await asyncio.sleep(self.config.response_wait_sec)
                    response = self.retriever.get_response()
                    if response:
                        break
                    await asyncio.sleep(self.config.retry_delay_sec)
                    
                if not response:
                    raise TimeoutError("Failed to retrieve agent response")
                    
                # Process response
                await self.agent_bus.publish(
                    BaseEvent(
                        agent_id=self.config.agent_id,
                        event_type="response",
                        data={"response": response}
                    )
                )
                
                # Archive processed message
                from .messaging import archive_inbox
                archive_inbox(self.logger, self.config)
                
            # Heartbeat delay
            await asyncio.sleep(self.config.heartbeat_sec)
            
        except Exception as e:
            self.logger.error(f"Cycle failed: {e}")
            raise

async def agent_loop(config: AgentConfig, run_once: bool = False) -> bool:
    """
    Main agent loop entry point.
    
    Args:
        config: Agent configuration
        run_once: If True, run one cycle then exit
        
    Returns:
        bool: True if loop completed successfully
    """
    manager = AgentLoopManager(config)
    return await manager.run(run_once=run_once) 