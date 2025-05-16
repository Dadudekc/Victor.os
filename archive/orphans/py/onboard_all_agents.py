"""
Dream.OS Agent Onboarding Script

This script handles onboarding for all agents (1-8) by:
1. Creating necessary directories and files
2. Setting up initial state
3. Sending onboarding messages
"""

import asyncio
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

from .config import AgentConfig
from .onboarding import AgentOnboardingManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Agent charters
AGENT_CHARTERS = {
    "Agent-1": "SYSTEM ARCHITECTURE",
    "Agent-2": "ESCALATION WATCH",
    "Agent-3": "CREATIVE SOLUTIONS",
    "Agent-4": "USER INTERACTION",
    "Agent-5": "KNOWLEDGE INTEGRATION",
    "Agent-6": "STRATEGIC PLANNING",
    "Agent-7": "IMPLEMENTATION",
    "Agent-8": "GOVERNANCE & ETHICS",
}


async def onboard_agent(agent_id: str, delay_sec: int = 5) -> bool:
    """
    Onboard a single agent with proper role initialization.

    Args:
        agent_id: The agent ID (e.g. "Agent-2")
        delay_sec: Delay before starting onboarding

    Returns:
        bool: True if onboarding was successful
    """
    try:
        logger.info(f"Starting onboarding for {agent_id}")

        # Create agent config
        config = AgentConfig(
            agent_id=agent_id, startup_delay_sec=0  # No startup delay for onboarding
        )

        # Create or clean required directories
        required_dirs = [
            config.base_runtime,
            config.inbox_dir,
            config.processed_dir,
            config.state_dir,
            config.devlog_path.parent,
        ]

        for directory in required_dirs:
            try:
                # If path exists but is not a directory
                if directory.exists():
                    if directory.is_file():
                        # Backup the file if it contains data
                        if directory.stat().st_size > 0:
                            backup_dir = directory.parent / "backup"
                            backup_dir.mkdir(parents=True, exist_ok=True)
                            backup_file = (
                                backup_dir
                                / f"{directory.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            )
                            shutil.move(str(directory), str(backup_file))
                            logger.info(f"Backed up file {directory} to {backup_file}")
                        else:
                            # Just delete empty files
                            directory.unlink()
                    elif not directory.is_dir():
                        # Handle other non-directory cases (symlinks, etc)
                        if directory.is_symlink():
                            directory.unlink()
                        else:
                            shutil.rmtree(directory)

                # Create directory and parents
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                return False

        logger.info(f"Created directories for {agent_id}")

        # Create initial state file
        if not config.state_file.exists():
            state = {
                "agent_id": agent_id,
                "status": "initializing",
                "last_update": datetime.now().isoformat(),
                "cycle_count": 0,
            }
            config.state_file.parent.mkdir(parents=True, exist_ok=True)
            config.state_file.write_text(json.dumps(state, indent=2))
            logger.info(f"Created initial state file for {agent_id}")

        # Load agent charter
        charter_file = (
            Path("runtime/governance/onboarding")
            / f"AGENT_CHARTER_{agent_id.split('-')[1]}.md"
        )
        if charter_file.exists():
            charter_file.read_text()
        else:
            f"# {agent_id} Charter\n\nRole: {AGENT_CHARTERS[agent_id]}"

        # Create onboarding manager
        manager = AgentOnboardingManager(config)

        # Optional delay between agents
        if delay_sec > 0:
            await asyncio.sleep(delay_sec)

        # Run onboarding
        success = await manager.onboard()

        if success:
            logger.info(f"Successfully onboarded {agent_id}")
        else:
            logger.error(f"Failed to onboard {agent_id}")

        return success

    except Exception as e:
        logger.error(f"Error onboarding {agent_id}: {e}")
        return False


async def onboard_all_agents(start_delay_sec: int = 10) -> Dict[str, bool]:
    """
    Onboard all agents in sequence.

    Args:
        start_delay_sec: Initial delay before starting onboarding

    Returns:
        Dict mapping agent IDs to onboarding success status
    """
    # Wait for initial delay
    logger.info(f"Starting onboarding sequence in {start_delay_sec} seconds...")
    await asyncio.sleep(start_delay_sec)

    results = {}

    # Onboard agents in sequence (1-8)
    for i in range(1, 9):
        agent_id = f"Agent-{i}"
        results[agent_id] = await onboard_agent(agent_id)

        # Break if an agent fails to onboard
        if not results[agent_id]:
            logger.error(f"Stopping onboarding sequence due to failure at {agent_id}")
            break

        # Delay between agents
        if i < 8:  # Don't delay after last agent
            await asyncio.sleep(5)

    # Print summary
    logger.info("\nOnboarding Results:")
    logger.info("-" * 20)
    for agent_id, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        logger.info(f"{agent_id}: {status}")

    return results


async def main():
    """Main entry point."""
    try:
        results = await onboard_all_agents()
        success = all(results.values())
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
