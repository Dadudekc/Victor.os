"""Integration module for Episode 5 automation with overnight runner.

This module provides the necessary hooks to integrate the Episode 5 automation
loop with the overnight runner system, including state management and recovery.
"""

import logging
import threading
from typing import Optional

from .episode5_autonomy_loop import run_episode5_loop
from ..core.config import AppConfig

logger = logging.getLogger(__name__)

class Episode5Integration:
    """Integration handler for Episode 5 automation."""
    
    def __init__(self):
        self.thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        self.config = AppConfig.load()

    def start(self):
        """Start the Episode 5 automation in a separate thread."""
        if self.thread and self.thread.is_alive():
            logger.warning("Episode 5 automation already running")
            return

        logger.info("Starting Episode 5 automation integration")
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

    def _run_episode5(self):
        """Run the Episode 5 automation loop with shutdown handling."""
        try:
            while not self.shutdown_event.is_set():
                run_episode5_loop()
        except Exception as e:
            logger.error(f"Episode 5 automation crashed: {e}", exc_info=True)
        finally:
            logger.info("Episode 5 automation stopped")

# Global instance for easy access
episode5 = Episode5Integration() 