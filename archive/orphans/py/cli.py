"""
Command Line Interface for Episode Execution
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from tools.env.check_env import verify_runtime_env

from .orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("runtime/logs/automation.log"),
    ],
)

logger = logging.getLogger(__name__)

# Environment failure tracking
ENV_FAILURES: List[datetime] = []
MAX_FAILURES = 3
FAILURE_WINDOW = timedelta(hours=24)


def log_violation(message: str) -> None:
    """Log an environment violation and track for escalation."""
    global ENV_FAILURES
    now = datetime.now()

    # Clean old failures
    ENV_FAILURES = [f for f in ENV_FAILURES if now - f < FAILURE_WINDOW]

    # Add new failure
    ENV_FAILURES.append(now)

    # Log violation
    logger.error(f"Environment violation: {message}")

    # Check for escalation
    if len(ENV_FAILURES) >= MAX_FAILURES:
        logger.critical(
            "⚠️ Multiple environment failures detected! Escalating to THEA..."
        )
        # TODO: Implement THEA escalation
        # from dreamos.core.thea import escalate_to_thea
        # escalate_to_thea("Environment validation failed repeatedly", ENV_FAILURES)


def setup_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="DreamOS Episode Execution CLI")
    parser.add_argument("episode_path", type=str, help="Path to the episode YAML file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser


def validate_episode_path(path: str) -> Optional[Path]:
    """Validate episode file path."""
    episode_path = Path(path)
    if not episode_path.exists():
        logger.error(f"Episode file not found: {path}")
        return None
    if not episode_path.suffix == ".yaml":
        logger.error("Episode file must be a YAML file")
        return None
    return episode_path


def main() -> int:
    """Main entry point for the CLI."""
    # Validate environment
    if not verify_runtime_env(strict=True):
        log_violation("Environment validation failed")
        return 1

    parser = setup_parser()
    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate episode path
    episode_path = validate_episode_path(args.episode_path)
    if not episode_path:
        return 1

    try:
        # Initialize orchestrator
        orchestrator = Orchestrator()

        # Start episode
        if not orchestrator.start_episode(str(episode_path)):
            logger.error("Failed to start episode")
            return 1

        # Main execution loop
        while orchestrator.is_running:
            if not orchestrator.execute_loop():
                break

        return 0

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        orchestrator.stop_episode()
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
