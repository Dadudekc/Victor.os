"""
Example script demonstrating the usage of the scraper state machine and integration.
"""

import logging
import time
from typing import Optional
from ..io.file_manager import FileManager
from ..io.agent_bus import AgentBus
from .scraper_integration import ScraperIntegration, ScraperIntegrationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScraperExample:
    """Example class demonstrating scraper usage."""
    
    def __init__(self):
        """Initialize the example."""
        self.file_manager = FileManager()
        self.agent_bus = AgentBus()
        self.config = ScraperIntegrationConfig()
        self.integration = ScraperIntegration(
            self.file_manager,
            self.agent_bus,
            self.config
        )
        
    def run(self) -> None:
        """Run the example."""
        try:
            # Initialize
            logger.info("Initializing scraper...")
            if not self.integration.initialize():
                logger.error("Failed to initialize scraper")
                return
                
            # Ensure login session
            logger.info("Ensuring login session...")
            if not self.integration.ensure_login_session():
                logger.error("Failed to ensure login session")
                return
                
            # Send prompts
            self._send_prompts()
            
            # Get conversation content
            self._get_conversation_content()
            
        except Exception as e:
            logger.error(f"Error in example: {e}")
        finally:
            # Shutdown
            logger.info("Shutting down...")
            self.integration.shutdown()
            
    def _send_prompts(self) -> None:
        """Send example prompts."""
        prompts = [
            "What is the capital of France?",
            "Tell me about quantum computing.",
            "Write a short poem about programming."
        ]
        
        for i, prompt in enumerate(prompts, 1):
            operation_id = f"prompt_{i}"
            logger.info(f"Sending prompt {i}: {prompt}")
            
            try:
                response = self.integration.send_prompt(prompt, operation_id)
                logger.info(f"Response {i}: {response}")
                
                # Check operation status
                if operation_id in self.integration.active_operations:
                    operation = self.integration.active_operations[operation_id]
                    logger.info(f"Operation {i} started at: {operation['start_time']}")
                    
            except Exception as e:
                logger.error(f"Error sending prompt {i}: {e}")
                logger.error(f"Current state: {self.integration.get_state()}")
                logger.error(f"Error message: {self.integration.get_error_message()}")
                
            # Small delay between prompts
            time.sleep(1)
            
    def _get_conversation_content(self) -> None:
        """Get and display conversation content."""
        try:
            content = self.integration.get_conversation_content()
            logger.info("Conversation content:")
            logger.info(content)
        except Exception as e:
            logger.error(f"Error getting conversation content: {e}")

def main():
    """Main entry point."""
    example = ScraperExample()
    example.run()

if __name__ == "__main__":
    main() 