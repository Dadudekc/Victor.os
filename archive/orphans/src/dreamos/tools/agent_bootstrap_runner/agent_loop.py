"""
Agent loop implementation for Dream.OS
"""

import asyncio
import logging
from pathlib import Path
import time

from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

from .config import AgentConfig
from .state_manager import AgentStateManager
from .health_monitor import HealthMonitor
from .protocol_validator import ProtocolValidator
from .messaging import process_message


class AgentLoopManager:
    """Manages the main agent loop."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"loop.{config.agent_id}")
        self.app_config = AppConfig()
        self.agent_bus = AgentBus()

        # Initialize UI components
        self.injector = CursorInjector(
            agent_id=config.agent_id, coords_file=str(config.coords_file)
        )
        self.retriever = ResponseRetriever(
            agent_id=config.agent_id_for_retriever,
            coords_file=str(config.copy_coords_file),
        )

        # Initialize components
        self.state_manager = AgentStateManager(config)
        self.health_monitor = HealthMonitor(config, self.state_manager)
        self.protocol_validator = ProtocolValidator(config)
        
        # Validate initial state
        self._validate_initial_state()

    def _validate_initial_state(self) -> None:
        """Validate initial agent state and file structure."""
        # Validate protocol compliance
        protocol_valid, issues = self.protocol_validator.validate_file_structure()
        if not protocol_valid:
            self.logger.error(f"Protocol validation failed: {issues}")
            raise RuntimeError("Failed to validate agent protocol structure")

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
                cycle_start = time.time()
                
                try:
                    # Record heartbeat
                    self.health_monitor.record_heartbeat()
                    
                    # Check health status
                    health_status = self.health_monitor.check_health()
                    if not health_status["healthy"]:
                        self.logger.warning(f"Health issues detected: {health_status['issues']}")
                        if not await self.health_monitor.attempt_recovery(health_status["issues"]):
                            self.logger.error("Failed to recover from health issues")
                            break
                    
                    # Process messages
                    messages = list(self.config.inbox_dir.glob("*.md"))
                    for message in messages:
                        await self._process_message_safely(message)
                    
                    # Update metrics
                    cycle_time_ms = (time.time() - cycle_start) * 1000
                    self.state_manager.record_cycle_metrics(cycle_time_ms, True)
                    
                    if run_once:
                        break
                        
                    await asyncio.sleep(self.config.loop_delay_sec)
                    
                except Exception as e:
                    self.logger.error(f"Error in agent loop cycle: {e}")
                    self.state_manager.update_state(last_error=str(e))
                    self.state_manager.record_cycle_metrics(
                        (time.time() - cycle_start) * 1000, 
                        False
                    )
                    
        except KeyboardInterrupt:
            self.logger.info("Agent loop interrupted")
        finally:
            self.logger.info("Agent loop stopped")

    async def _process_message_safely(self, message: Path) -> bool:
        """Safely process a message with protocol validation."""
        try:
            # Load and validate message
            content = message.read_text()
            message_data = {"content": content, "type": "command", "protocol_version": "1.0"}
            
            valid, error = self.protocol_validator.validate_message_format(message_data)
            if not valid:
                self.logger.error(f"Invalid message format: {error}")
                return False
                
            # Process message
            success = await process_message(
                message,
                self.agent_bus,
                self.injector,
                self.retriever,
                self.config
            )
            
            if success:
                self.state_manager.state["messages_processed"] += 1
                self.state_manager.save_state()
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error processing message {message}: {e}")
            return False


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
