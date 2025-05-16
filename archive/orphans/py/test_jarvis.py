#!/usr/bin/env python3
"""
Simple test script for JARVIS core functionality.
"""

import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from dreamos.automation.interaction import InteractionManager
from dreamos.automation.jarvis_core import JarvisCore

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Test JARVIS core functionality."""
    logger.info("Initializing JARVIS core...")

    # Create memory directory
    memory_dir = Path("runtime/jarvis_memory")
    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_path = memory_dir / "memory.json"

    # Initialize JARVIS
    try:
        jarvis = JarvisCore()
        jarvis.memory_path = memory_path
        logger.info("JARVIS core initialized")

        # Initialize interaction manager
        interaction_manager = InteractionManager(jarvis)
        logger.info("Interaction manager initialized")

        # Activate JARVIS
        success = jarvis.activate()
        if success:
            logger.info("JARVIS activated successfully")
        else:
            logger.error("Failed to activate JARVIS")
            return

        # Test processing input
        response = jarvis.process_input("Hello JARVIS")
        logger.info(f"JARVIS response: {response}")

        # Test interaction manager
        response = interaction_manager.process_input("What can you do?")
        logger.info(f"Interaction manager response: {response}")

        # Test task execution
        task = {
            "id": "test_task",
            "type": "file_operation",
            "operation": "write",
            "file_path": "runtime/jarvis_test/test_output.txt",
            "content": "This is a test file created by JARVIS",
            "description": "Create test file",
        }
        result = jarvis.execute_task(task)
        logger.info(f"Task execution result: {result}")

        # Deactivate JARVIS
        success = jarvis.deactivate()
        if success:
            logger.info("JARVIS deactivated successfully")
        else:
            logger.error("Failed to deactivate JARVIS")

        # Verify memory file was created
        if memory_path.exists():
            logger.info(f"Memory file created at {memory_path}")
        else:
            logger.error(f"Memory file not created at {memory_path}")

    except Exception as e:
        logger.error(f"Error testing JARVIS: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
