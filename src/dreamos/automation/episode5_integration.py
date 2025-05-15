"""Integration module for Episode 5 automation with overnight runner.

This module provides the necessary hooks to integrate the Episode 5 automation
loop with the overnight runner system, including state management and recovery.
"""

import logging
import threading
from typing import Optional

from .episode5_autonomy_loop import run_episode5_loop, run_episode5_loop_with_fallback
from .jarvis_core import JarvisCore
from .interaction import InteractionManager
from ..core.config import AppConfig

logger = logging.getLogger(__name__)

class Episode5Integration:
    """Integration handler for Episode 5 automation."""
    
    def __init__(self):
        self.thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        self.config = AppConfig.load()
        
        # Initialize JARVIS
        try:
            self.jarvis = JarvisCore()
            self.interaction_manager = InteractionManager(self.jarvis)
            self.jarvis_available = True
        except Exception as e:
            logger.error(f"Failed to initialize JARVIS: {str(e)}")
            self.jarvis = None
            self.interaction_manager = None
            self.jarvis_available = False

    def start(self):
        """Start the Episode 5 automation in a separate thread."""
        if self.thread and self.thread.is_alive():
            logger.warning("Episode 5 automation already running")
            return

        logger.info("Starting Episode 5 automation integration")
        
        # Activate JARVIS if available
        if self.jarvis_available and self.jarvis and not self.jarvis.is_active:
            try:
                success = self.jarvis.activate()
                if success:
                    logger.info("JARVIS activated successfully")
                else:
                    logger.warning("Failed to activate JARVIS")
                    self.jarvis_available = False
            except Exception as e:
                logger.error(f"Error activating JARVIS: {str(e)}")
                self.jarvis_available = False
        
        self.shutdown_event.clear()
        self.thread = threading.Thread(
            target=self._run_episode5,
            name="Episode5Automation",
            daemon=True
        )
        self.thread.start()

    def stop(self):
        """Stop the Episode 5 automation gracefully."""
        if not self.thread or not self.thread.is_alive():
            logger.warning("Episode 5 automation not running")
            return

        logger.info("Stopping Episode 5 automation")
        self.shutdown_event.set()
        self.thread.join(timeout=30)
        if self.thread.is_alive():
            logger.warning("Episode 5 automation did not stop gracefully")
            
        # Deactivate JARVIS if available
        if self.jarvis_available and self.jarvis and self.jarvis.is_active:
            try:
                success = self.jarvis.deactivate()
                if success:
                    logger.info("JARVIS deactivated successfully")
                else:
                    logger.warning("Failed to deactivate JARVIS")
            except Exception as e:
                logger.error(f"Error deactivating JARVIS: {str(e)}")

    def _run_episode5(self):
        """Run the Episode 5 automation loop with shutdown handling."""
        try:
            while not self.shutdown_event.is_set():
                if self.jarvis_available:
                    try:
                        # Try with JARVIS first
                        run_episode5_loop(jarvis=self.jarvis, interaction_manager=self.interaction_manager)
                    except Exception as e:
                        logger.error(f"Error in JARVIS-enabled loop: {str(e)}")
                        # Fall back to non-JARVIS mode
                        try:
                            run_episode5_loop(None, None)
                        except Exception as e2:
                            logger.error(f"Error in fallback loop: {str(e2)}")
                else:
                    # Run without JARVIS
                    try:
                        run_episode5_loop(None, None)
                    except Exception as e:
                        logger.error(f"Error in non-JARVIS loop: {str(e)}")
        except Exception as e:
            logger.error(f"Episode 5 automation crashed: {e}", exc_info=True)
        finally:
            logger.info("Episode 5 automation stopped")
            
    def process_input(self, input_text: str, source: str = "user"):
        """Process input through JARVIS.
        
        Args:
            input_text: The input text to process
            source: Source of the input
            
        Returns:
            Response from JARVIS
        """
        if not self.jarvis_available:
            return {"error": "JARVIS is not available", "content": "JARVIS is not available"}
            
        try:
            if not self.jarvis.is_active:
                logger.warning("JARVIS is not active, activating...")
                self.jarvis.activate()
                
            return self.interaction_manager.process_input(input_text, source)
        except Exception as e:
            logger.error(f"Error processing input through JARVIS: {str(e)}")
            return {"error": str(e), "content": "Error processing input"}

# Global instance for easy access
episode5 = Episode5Integration() 