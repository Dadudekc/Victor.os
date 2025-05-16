"""
Gracefully shutdown all running Dream.OS agents
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
LOG_DIR = Path("runtime/parallel_logs")
STATE_FILE = LOG_DIR / "launcher_state.json"
SHUTDOWN_TIMEOUT = 10  # seconds


def load_state() -> dict:
    """Load launcher state from file"""
    try:
        if STATE_FILE.exists():
            with STATE_FILE.open() as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load state file: {e}")
    return {}


def shutdown_agent(agent_id: str, pid: int, timeout: int = SHUTDOWN_TIMEOUT) -> bool:
    """
    Gracefully shutdown an agent process

    Args:
        agent_id: Agent identifier
        pid: Process ID to shutdown
        timeout: Seconds to wait for graceful shutdown

    Returns:
        bool: True if shutdown was successful
    """
    try:
        # Try sending SIGTERM first
        os.kill(pid, signal.SIGTERM)

        # Wait for process to terminate
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if process still exists
                os.kill(pid, 0)
                time.sleep(0.1)
            except OSError:
                # Process no longer exists
                logger.info(f"✅ {agent_id} (PID {pid}) stopped gracefully")
                return True

        # If still running after timeout, force kill
        os.kill(pid, signal.SIGKILL)
        logger.warning(f"⚠️  {agent_id} (PID {pid}) force killed after timeout")
        return True

    except ProcessLookupError:
        logger.info(f"Process {pid} for {agent_id} not found (already stopped)")
        return True
    except Exception as e:
        logger.error(f"Failed to stop {agent_id} (PID {pid}): {e}")
        return False


def shutdown_all(agents: list = None, force: bool = False) -> bool:
    """
    Shutdown all running agents

    Args:
        agents: List of agent IDs to shutdown, or None for all
        force: Whether to force kill processes

    Returns:
        bool: True if all agents were shutdown successfully
    """
    state = load_state()
    if not state:
        logger.error("No launcher state found. Are any agents running?")
        return False

    success = True
    for agent_id, info in state.items():
        if agents and agent_id not in agents:
            continue

        pid = info.get("pid")
        if not pid:
            continue

        logger.info(f"🛑 Stopping {agent_id}...")
        if force:
            try:
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Killed {agent_id} (PID {pid})")
            except ProcessLookupError:
                logger.info(f"Process {pid} for {agent_id} not found")
            except Exception as e:
                logger.error(f"Failed to kill {agent_id} (PID {pid}): {e}")
                success = False
        else:
            if not shutdown_agent(agent_id, pid):
                success = False

    return success


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Shutdown Dream.OS agents")
    parser.add_argument(
        "--agents",
        nargs="+",
        help="Specific agents to shutdown (e.g., 'Agent-1 Agent-2')",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force kill agents instead of graceful shutdown",
    )
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    if not shutdown_all(agents=args.agents, force=args.force):
        logger.error("Failed to shutdown all agents")
        sys.exit(1)

    logger.info("All agents stopped successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutdown cancelled")
        sys.exit(1)
