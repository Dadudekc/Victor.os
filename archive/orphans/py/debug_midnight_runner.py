#!/usr/bin/env python3
"""Debug script for running the midnight runner with proper error handling."""

import logging
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.dreamos.automation.midnight_runner import MidnightRunner
from src.dreamos.core.config import AppConfig

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG level for maximum visibility
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler("runtime/logs/debug_midnight_runner.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("debug_midnight_runner")


def main():
    """Run the midnight runner with debug logging."""
    try:
        # Load configuration
        logger.info("Loading AppConfig...")
        AppConfig.load()
        logger.info("AppConfig loaded successfully")

        # Create and start midnight runner
        logger.info("Initializing MidnightRunner...")
        runner = MidnightRunner()

        logger.info("Starting MidnightRunner...")
        runner.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
