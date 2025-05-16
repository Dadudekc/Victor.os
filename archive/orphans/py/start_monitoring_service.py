#!/usr/bin/env python3
"""
Script to start the Task Monitoring Service.

This script starts the TaskMonitoringService, which periodically checks for stalled tasks
and handles them according to the configured escalation strategy.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from dreamos.core.config import get_config
from dreamos.core.tasks.monitoring.task_monitoring_service import TaskMonitoringService
from dreamos.core.tasks.nexus.task_nexus import TaskNexus

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the script."""
    try:
        # Load configuration
        config = get_config()

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.logging.level.upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
        )

        logger.info("Starting Task Monitoring Service")

        # Initialize TaskNexus
        task_file = config.paths.central_task_boards / "task_list.json"
        task_nexus = TaskNexus(task_file)

        # Initialize and start TaskMonitoringService
        monitoring_service = TaskMonitoringService(
            task_nexus, config.task_monitoring.model_dump()
        )

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()

        def signal_handler():
            logger.info("Received shutdown signal, stopping service...")
            loop.create_task(shutdown(monitoring_service))

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        # Start the service
        await monitoring_service.start()

    except Exception as e:
        logger.error(f"Error starting Task Monitoring Service: {e}", exc_info=True)
        sys.exit(1)


async def shutdown(monitoring_service: TaskMonitoringService):
    """Gracefully shut down the service."""
    logger.info("Shutting down Task Monitoring Service...")
    await monitoring_service.stop()
    # Give a little time for cleanup
    await asyncio.sleep(1)
    # Exit the process
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
