"""
Environment Verification for Dream.OS

This module provides functionality to verify the runtime environment
and ensure all required components are available.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def verify_runtime_env(strict=False):
    """
    Verify that the runtime environment is properly set up.

    Args:
        strict (bool): If True, exit with error code on failures

    Returns:
        bool: True if environment is valid, False otherwise
    """
    logger.info("Verifying runtime environment...")

    # Check for required directories
    required_dirs = [
        Path("runtime"),
        Path("runtime/governance"),
        Path("runtime/governance/onboarding"),
        Path("runtime/governance/protocols"),
        Path("runtime/agent_comms"),
        Path("runtime/agent_comms/agent_mailboxes"),
    ]

    for directory in required_dirs:
        if not directory.exists():
            error_msg = f"Required directory not found: {directory}"
            logger.error(error_msg)
            if strict:
                sys.exit(1)
            return False

    # Check for required files
    required_files = [
        Path("runtime/governance/onboarding/AGENT_ONBOARDING_TEMPLATE.md"),
    ]

    for file_path in required_files:
        if not file_path.exists():
            error_msg = f"Required file not found: {file_path}"
            logger.error(error_msg)
            if strict:
                sys.exit(1)
            return False

    # Ensure agent mailboxes exist for all agents
    for i in range(1, 9):
        agent_id = f"Agent-{i}"
        agent_dir = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}")
        inbox_dir = agent_dir / "inbox"
        processed_dir = agent_dir / "processed"
        state_dir = agent_dir / "state"

        for dir_path in [agent_dir, inbox_dir, processed_dir, state_dir]:
            if not dir_path.exists():
                logger.info(f"Creating directory: {dir_path}")
                dir_path.mkdir(parents=True, exist_ok=True)

    logger.info("Environment verification completed successfully")
    return True


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run verification
    result = verify_runtime_env(strict=True)
    sys.exit(0 if result else 1)
