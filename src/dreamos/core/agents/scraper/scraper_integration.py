"""
Scraper Integration Module

This module provides integration between the scraper state machine and other system components.
It handles initialization, prompt sending, response management, and error recovery.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any, List, Tuple
from ..io.file_manager import FileManager
from ..io.agent_bus import AgentBus
from .scraper_state_machine import ScraperStateMachine, ScraperState, ScraperMetadata
from .chatgpt_scraper import ChatGPTScraper
import time
import uuid

logger = logging.getLogger(__name__)

@dataclass
class ScraperIntegrationConfig:
    """Configuration for the scraper integration."""
    timeout: int = 30
    stable_period: int = 5
    poll_interval: float = 0.5
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_metadata_logging: bool = True
    metadata_log_path: str = "logs/scraper_metadata"

class ScraperIntegration:
    """Integration class for connecting the scraper state machine with system components."""
    
    def __init__(self, file_manager: FileManager, agent_bus: AgentBus, config: ScraperIntegrationConfig):
        """Initialize the scraper integration.
        
        Args:
            file_manager: File manager instance for file operations
            agent_bus: Agent bus for system communication
            config: Configuration for the integration
        """
        self.file_manager = file_manager
        self.agent_bus = agent_bus
        self.config = config
        self.state_machine = ScraperStateMachine(file_manager)
        self.active_operations: Dict[str, ScraperMetadata] = {}
        
    def initialize(self) -> bool:
        """Initialize the scraper integration.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing scraper integration")
            self.state_machine.process()
            return self.state_machine.state == ScraperState.READY
        except Exception as e:
            logger.error(f"Failed to initialize scraper integration: {e}")
            return False
            
    def send_prompt(self, prompt: str, operation_id: Optional[str] = None, context_tags: Optional[List[str]] = None) -> str:
        """Send a prompt through the scraper.
        
        Args:
            prompt: The prompt to send
            operation_id: Optional ID to track this operation
            context_tags: Optional list of tags to categorize this operation
            
        Returns:
            str: The response from the scraper
            
        Raises:
            Exception: If sending the prompt fails
        """
        try:
            operation_id = operation_id or str(uuid.uuid4())
            logger.info(f"Sending prompt (operation_id: {operation_id})")
            
            # Initialize operation metadata
            metadata = ScraperMetadata(
                operation_id=operation_id,
                start_time=time.time(),
                prompt=prompt,
                context_tags=context_tags or []
            )
            self.active_operations[operation_id] = metadata
                
            self.state_machine.send_prompt(prompt, operation_id)
            self.state_machine.process()
            
            response = self.state_machine.get_current_response()
            if operation_id:
                self.active_operations[operation_id].response = response
                self.active_operations[operation_id].end_time = time.time()
                
                if self.config.enable_metadata_logging:
                    self._log_operation_metadata(operation_id)
                
            return response
        except Exception as e:
            logger.error(f"Failed to send prompt: {e}")
            if operation_id:
                self.active_operations[operation_id].error = str(e)
                self.active_operations[operation_id].end_time = time.time()
                if self.config.enable_metadata_logging:
                    self._log_operation_metadata(operation_id)
            raise
            
    def _log_operation_metadata(self, operation_id: str) -> None:
        """Log operation metadata to file.
        
        Args:
            operation_id: The operation ID to log
        """
        try:
            metadata = self.active_operations.get(operation_id)
            if not metadata:
                return
                
            log_file = f"{self.config.metadata_log_path}/{operation_id}.json"
            self.file_manager.write_json(log_file, metadata.__dict__)
        except Exception as e:
            logger.error(f"Failed to log operation metadata: {e}")
            
    def get_operation_metadata(self, operation_id: str) -> Optional[ScraperMetadata]:
        """Get metadata for a specific operation.
        
        Args:
            operation_id: The operation ID to get metadata for
            
        Returns:
            Optional[ScraperMetadata]: The operation metadata or None if not found
        """
        return self.active_operations.get(operation_id)
        
    def get_active_operations(self) -> Dict[str, ScraperMetadata]:
        """Get all active operations.
        
        Returns:
            Dict[str, ScraperMetadata]: Dictionary of active operations
        """
        return self.active_operations.copy()
            
    def get_conversation_content(self) -> str:
        """Get the current conversation content.
        
        Returns:
            str: The conversation content
            
        Raises:
            Exception: If getting the content fails
        """
        try:
            return self.state_machine.context.scraper.get_conversation_content()
        except Exception as e:
            logger.error(f"Failed to get conversation content: {e}")
            raise
            
    def ensure_login_session(self) -> bool:
        """Ensure the scraper has a valid login session.
        
        Returns:
            bool: True if login session is valid, False otherwise
        """
        try:
            return self.state_machine.context.scraper.ensure_login_session()
        except Exception as e:
            logger.error(f"Failed to ensure login session: {e}")
            return False
            
    def shutdown(self) -> None:
        """Shutdown the scraper integration."""
        try:
            logger.info("Shutting down scraper integration")
            self.state_machine.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    def get_state(self) -> ScraperState:
        """Get the current state of the scraper.
        
        Returns:
            ScraperState: The current state
        """
        return self.state_machine.state
        
    def get_error_message(self) -> Optional[str]:
        """Get the current error message if any.
        
        Returns:
            Optional[str]: The error message or None if no error
        """
        return self.state_machine.context.error_message 