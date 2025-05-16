#!/usr/bin/env python3
"""
Test script for the Task Monitoring Service.
"""

import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import the required modules
from dreamos.core.tasks.monitoring.pending_monitor import PendingTaskMonitor
from dreamos.core.tasks.nexus.task_nexus import TaskNexus


async def main():
    """Main entry point for the test script."""
    try:
        print("Starting Task Monitoring test")

        # Initialize TaskNexus
        task_file = Path("runtime/agent_comms/central_task_boards/task_list.json")
        print(f"Using task file: {task_file.absolute()}")

        task_nexus = TaskNexus(task_file)

        # Initialize PendingTaskMonitor with a short timeout
        config = {
            "pending_timeout_seconds": 10,  # 10 seconds for testing
            "escalation_strategy": "mark_stalled",
        }

        monitor = PendingTaskMonitor(task_nexus, config)

        # Run a check
        print("Running check...")
        await monitor.check_pending_tasks()

        # Check the task list
        tasks = task_nexus.get_all_tasks()
        print(f"Tasks after check: {tasks}")

        print("Test completed!")

    except Exception as e:
        print(f"Error in test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
