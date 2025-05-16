"""
MIDNIGHT.MISSION.RUNNER
Core system for overnight operation cycles.

Features:
- State management and persistence
- Recovery protocols
- Night cycle detection and handling
- Resource optimization
- Health monitoring
- Event logging
- Episode 5 automation integration
"""

import logging
import signal
import sys
import time

from .episode5_integration import episode5

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("runtime/logs/midnight_runner.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class MidnightRunner:
    def __init__(self):
        self.is_running = False

    def start(self):
        """Start the midnight runner."""
        logger.info("Starting MIDNIGHT.MISSION.RUNNER")
        self.is_running = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Start Episode 5 automation
        episode5.start()

        try:
            while self.is_running:
                self.run_cycle()
                time.sleep(60)  # Run cycle every minute
        except Exception as e:
            logger.error(f"Fatal error in runner: {e}")
            self.emergency_shutdown()

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received shutdown signal {signum}")
        self.is_running = False

        # Stop Episode 5 automation
        episode5.stop()

        self._save_state()
        sys.exit(0)

    def emergency_shutdown(self):
        """Handle emergency shutdown scenarios."""
        logger.error("Initiating emergency shutdown")
        self.is_running = False

        # Stop Episode 5 automation
        episode5.stop()

        self._save_state()
        sys.exit(1)
