"""
Dream.OS System Reset

This script coordinates:
1. Agent onboarding
2. Task assignment
3. Supervisor loop initialization
4. Overnight run management
"""

import argparse
import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import pyautogui
import pyperclip
from rich.console import Console
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("system_reset")

# Constants
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
MAILBOX_PATH = Path("runtime/agent_comms/agent_mailboxes")
TASKS_PATH = Path("runtime/tasks/board")
ONBOARDING_PATH = Path("runtime/governance/onboarding")
PROTOCOLS_PATH = Path("runtime/governance/protocols")
PROJECT_PLAN = Path("specs/PROJECT_PLAN.md")

# Timing constants
INITIAL_DELAY = 180  # 3 minutes initial delay
COPY_DELAY = 180  # 3 minutes between copies
TYPING_DELAY = 180  # 3 minutes typing delay

console = Console()


class SystemReset:
    """Tool for resetting agent mailboxes and tasks to a clean state."""

    # Files and directories that should be preserved
    PRESERVED_FILES: Set[str] = {"status.json", "devlog.md"}

    PRESERVED_DIRS: Set[str] = {"inbox", "outbox", "processed", "state"}

    def __init__(self, base_path: str = "runtime/agent_comms/agent_mailboxes"):
        self.base_path = Path(base_path)
        self.agent_paths = self._get_agent_paths()

    def _get_agent_paths(self) -> Dict[str, Path]:
        """Get paths for all agent mailboxes."""
        return {
            agent_dir.name: agent_dir
            for agent_dir in self.base_path.iterdir()
            if agent_dir.is_dir() and agent_dir.name.startswith("Agent-")
        }

    def _archive_agent_files(self, agent_path: Path) -> str:
        """
        Archive all non-essential files in the agent's mailbox.

        Returns:
            str: The archive directory name
        """
        # Create archive directory with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_dir = agent_path / "processed" / f"archive_{timestamp}"
        archive_dir.mkdir(parents=True, exist_ok=True)

        for item in agent_path.iterdir():
            if item.is_file() and item.name not in self.PRESERVED_FILES:
                try:
                    # Move file to archive
                    shutil.move(str(item), str(archive_dir / item.name))
                    logger.info(f"Archived file: {item.name}")
                except Exception as e:
                    logger.error(f"Error archiving file {item.name}: {str(e)}")
            elif item.is_dir() and item.name not in self.PRESERVED_DIRS:
                try:
                    # Move directory to archive
                    shutil.move(str(item), str(archive_dir / item.name))
                    logger.info(f"Archived directory: {item.name}")
                except Exception as e:
                    logger.error(f"Error archiving directory {item.name}: {str(e)}")

        return f"archive_{timestamp}"

    def reset_agent_mailbox(self, agent_id: str) -> bool:
        """
        Reset an agent's mailbox to a clean state.

        Args:
            agent_id: The ID of the agent to reset (e.g., "Agent-1")

        Returns:
            bool: True if reset was successful, False otherwise
        """
        try:
            if agent_id not in self.agent_paths:
                logger.error(f"Agent {agent_id} not found")
                return False

            agent_path = self.agent_paths[agent_id]

            # Archive all non-essential files first
            archive_name = self._archive_agent_files(agent_path)

            # Clear inbox
            inbox_dir = agent_path / "inbox"
            if inbox_dir.exists():
                shutil.rmtree(inbox_dir)
            inbox_dir.mkdir()

            # Clear outbox
            outbox_dir = agent_path / "outbox"
            if outbox_dir.exists():
                shutil.rmtree(outbox_dir)
            outbox_dir.mkdir()

            # Clear processed (except archives)
            processed_dir = agent_path / "processed"
            if processed_dir.exists():
                for item in processed_dir.iterdir():
                    if not item.name.startswith("archive_"):
                        if item.is_file():
                            item.unlink()
                        else:
                            shutil.rmtree(item)
            else:
                processed_dir.mkdir()

            # Reset state directory
            state_dir = agent_path / "state"
            if state_dir.exists():
                shutil.rmtree(state_dir)
            state_dir.mkdir()

            # Initialize fresh status.json
            status_data = {
                "status": "AGENT_MAILBOX_RESET",
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "cycle_count": 0,
                "operation_state": "UNINITIALIZED",
            }

            status_file = agent_path / "status.json"
            with open(status_file, "w") as f:
                json.dump(status_data, f, indent=2)

            # Initialize fresh operation state
            operation_state = {
                "cycle_count": 0,
                "last_cycle": None,
                "operation_state": "UNINITIALIZED",
                "last_updated": datetime.utcnow().isoformat() + "Z",
            }

            state_file = state_dir / "operation_state.json"
            with open(state_file, "w") as f:
                json.dump(operation_state, f, indent=2)

            # Create fresh devlog
            devlog_file = agent_path / "devlog.md"
            with open(devlog_file, "w") as f:
                f.write("# Agent Development Log\n\n")
                f.write(f"## Mailbox Reset - {datetime.utcnow().isoformat()}Z\n")
                f.write("Agent mailbox has been reset to a clean state.\n")
                f.write(f"Previous files archived to: processed/{archive_name}\n")

            logger.info(f"Successfully reset mailbox for {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error resetting agent {agent_id}: {str(e)}")
            return False

    def reset_all_mailboxes(self) -> Dict[str, bool]:
        """
        Reset all agent mailboxes to clean states.

        Returns:
            Dict[str, bool]: Dictionary mapping agent IDs to reset success status
        """
        results = {}
        for agent_id in self.agent_paths:
            results[agent_id] = self.reset_agent_mailbox(agent_id)
        return results


def load_coordinates() -> Optional[Dict]:
    """Load agent coordinates from config file."""
    try:
        if not COORDS_PATH.exists():
            logger.error(f"❌ Coordinates file not found: {COORDS_PATH}")
            return None
        coords = json.loads(COORDS_PATH.read_text())
        logger.info(f"✅ Loaded coordinates for {len(coords)} agents")
        return coords
    except Exception as e:
        logger.error(f"❌ Error loading coordinates: {e}")
        return None


def send_to_agent(
    coords: Dict, agent_id: str, message: str, dry_run: bool = False
) -> bool:
    """Send a message to an agent."""
    if agent_id not in coords:
        logger.error(f"❌ No coordinates found for {agent_id}")
        return False

    try:
        input_box = coords[agent_id]["input_box"]
        coords[agent_id]["copy_button"]

        if not dry_run:
            # Click input box
            pyautogui.click(input_box["x"], input_box["y"])
            time.sleep(0.5)

            # Accept any pending changes
            pyautogui.hotkey("ctrl", "enter")
            time.sleep(1.0)

            # Send message
            pyperclip.copy(message)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(INITIAL_DELAY)
            pyautogui.press("enter")
            logger.info(f"✅ Sent message to {agent_id}")
            return True
        else:
            logger.info(f"[DRY-RUN] Would send message to {agent_id}")
            return True

    except Exception as e:
        logger.error(f"❌ Error sending message to {agent_id}: {e}")
        return False


def get_agent_tasks(agent_id: str) -> List[Dict]:
    """Get tasks assigned to an agent."""
    try:
        working_tasks = TASKS_PATH / "runtime/tasks/working_tasks.json"
        future_tasks = TASKS_PATH / "runtime/tasks/future_tasks.json"

        tasks = []

        if working_tasks.exists():
            with working_tasks.open() as f:
                data = json.load(f)
                tasks.extend([t for t in data if t.get("assigned_to") == agent_id])

        if future_tasks.exists():
            with future_tasks.open() as f:
                data = json.load(f)
                tasks.extend([t for t in data if t.get("assigned_to") == agent_id])

        return tasks
    except Exception as e:
        logger.error(f"❌ Error getting tasks for {agent_id}: {e}")
        return []


def create_onboarding_message(agent_id: str) -> str:
    """Create onboarding message for an agent."""
    tasks = get_agent_tasks(agent_id)
    task_list = "\n".join([f"- {t['title']}" for t in tasks])

    return f"""# ONBOARDING PROTOCOL ACTIVATED

Welcome to Dream.OS! Please follow these steps:

1. Review your onboarding materials:
   - {ONBOARDING_PATH}
   - {PROTOCOLS_PATH}
   - {PROJECT_PLAN}

2. Your assigned tasks:
{task_list}

3. Start the supervisor loop:
   ```bash
   python src/dreamos/tools/autonomy/supervisor_loop.py --agent {agent_id}
   ```

4. Begin working on your tasks autonomously.

Remember:
- Stay in continuous autonomy mode
- Report only on task state changes
- Never stop unless absolutely necessary
- Complete at least 25 cycles before any pause

# END OF PROMPT"""


def reset_agent(agent_id: str, dry_run: bool = False) -> bool:
    """Reset an agent's state and start them on tasks."""
    coords = load_coordinates()
    if not coords:
        return False

    # Send onboarding message
    message = create_onboarding_message(agent_id)
    if not send_to_agent(coords, agent_id, message, dry_run):
        return False

    # Wait 3 minutes before starting supervisor loop
    if not dry_run:
        logger.info(
            f"⏳ Waiting {INITIAL_DELAY} seconds before starting supervisor loop for {agent_id}..."
        )
        time.sleep(INITIAL_DELAY)

    # Start supervisor loop
    if not dry_run:
        try:
            import subprocess

            subprocess.Popen(
                [
                    "python",
                    "src/dreamos/tools/autonomy/supervisor_loop.py",
                    "--agent",
                    agent_id,
                ]
            )
            logger.info(f"✅ Started supervisor loop for {agent_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error starting supervisor loop for {agent_id}: {e}")
            return False
    else:
        logger.info(f"[DRY-RUN] Would start supervisor loop for {agent_id}")
        return True


def main(agents: Optional[list] = None, dry_run: bool = False) -> int:
    """
    Main entry point for the system reset tool.

    Args:
        agents: Optional list of agent IDs to reset. If None, resets all agents.
        dry_run: If True, only show what would be reset without making changes.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    reset_tool = SystemReset()

    if dry_run:
        print("Dry run mode - no changes will be made")
        if agents:
            print(f"Would reset agents: {', '.join(agents)}")
        else:
            print("Would reset all agents")
        return 0

    if agents:
        results = {}
        for agent_id in agents:
            results[agent_id] = reset_tool.reset_agent_mailbox(agent_id)
    else:
        results = reset_tool.reset_all_mailboxes()

    # Check results
    all_success = all(results.values())
    for agent_id, success in results.items():
        status = "Success" if success else "Failed"
        print(f"{agent_id}: {status}")

    return 0 if all_success else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset agent mailboxes to a clean state"
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        help="Specific agent IDs to reset (e.g., Agent-1 Agent-2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be reset without making changes",
    )
    args = parser.parse_args()

    exit_code = main(args.agents, dry_run=args.dry_run)
    exit(exit_code)
