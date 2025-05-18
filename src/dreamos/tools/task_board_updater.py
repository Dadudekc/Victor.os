#!/usr/bin/env python3
"""
Task Board Updater Script

This script safely updates the task_board.json file using filelock to avoid
permission errors and race conditions. It can be used to add new tasks, update
existing tasks, or modify the status of tasks.
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import filelock
except ImportError:
    print("Error: filelock package not installed. Please install it with: pip install filelock")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("task_board_updater")

# Constants
DEFAULT_TASK_BOARD_PATH = Path("runtime/task_board.json")
DEFAULT_LOCK_TIMEOUT = 30  # seconds


class TaskBoardUpdater:
    """
    Safely updates the task_board.json file with proper file locking.
    """

    def __init__(
        self,
        task_board_path: Path = DEFAULT_TASK_BOARD_PATH,
        lock_timeout: int = DEFAULT_LOCK_TIMEOUT,
    ):
        """
        Initialize the TaskBoardUpdater.

        Args:
            task_board_path: Path to the task_board.json file
            lock_timeout: Timeout in seconds for acquiring the file lock
        """
        self.task_board_path = task_board_path
        self.lock_timeout = lock_timeout
        self.lock_path = task_board_path.with_suffix(task_board_path.suffix + ".lock")

        # Ensure directory exists
        self.task_board_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_task_board(self) -> Dict[str, Any]:
        """
        Read the task board file with file locking.

        Returns:
            Dict containing task board data
        """
        try:
            with filelock.FileLock(self.lock_path, timeout=self.lock_timeout):
                if not self.task_board_path.exists():
                    logger.warning(f"Task board file not found: {self.task_board_path}")
                    return {"cursor_agents": {}, "last_updated_utc": datetime.utcnow().isoformat()}

                with open(self.task_board_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                return data
        except filelock.Timeout:
            logger.error(f"Could not acquire lock for {self.task_board_path} within {self.lock_timeout} seconds")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task board: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to read task board: {e}")
            raise

    def _write_task_board(self, data: Dict[str, Any]) -> None:
        """
        Write data to the task board file with file locking and atomic replacement.

        Args:
            data: Dict containing task board data to write
        """
        temp_file_path = None
        try:
            with filelock.FileLock(self.lock_path, timeout=self.lock_timeout):
                # Update the last updated timestamp
                data["last_updated_utc"] = datetime.utcnow().isoformat()

                # Write to a temporary file first
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=self.task_board_path.parent,
                    delete=False,
                    suffix=".tmp",
                ) as temp_file:
                    temp_file_path = Path(temp_file.name)
                    json.dump(data, temp_file, indent=2)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())  # Ensure data is written to disk

                # Atomically replace the original file
                os.replace(temp_file_path, self.task_board_path)
                logger.info(f"Successfully updated task board at {self.task_board_path}")
        except filelock.Timeout:
            logger.error(f"Could not acquire lock for {self.task_board_path} within {self.lock_timeout} seconds")
            raise
        except Exception as e:
            logger.error(f"Failed to write task board: {e}")
            # Clean up temp file if it exists
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except Exception:
                    pass
            raise

    def update_agent_status(
        self,
        agent_id: str,
        status: str,
        status_details: Optional[str] = None,
        task_id: Optional[str] = None,
        task_description: Optional[str] = None,
    ) -> None:
        """
        Update an agent's status in the task board.

        Args:
            agent_id: ID of the agent (e.g., "cursor_1")
            status: New status (e.g., "EXECUTING", "IDLE")
            status_details: Optional details about the status
            task_id: Optional task ID the agent is working on
            task_description: Optional task description
        """
        data = self._read_task_board()

        # Ensure cursor_agents section exists
        if "cursor_agents" not in data:
            data["cursor_agents"] = {}

        # Create agent entry if it doesn't exist
        if agent_id not in data["cursor_agents"]:
            data["cursor_agents"][agent_id] = {
                "status": "UNKNOWN",
                "last_status_update_utc": datetime.utcnow().isoformat(),
            }

        # Update agent data
        agent_data = data["cursor_agents"][agent_id]
        agent_data["status"] = status
        agent_data["last_status_update_utc"] = datetime.utcnow().isoformat()

        if status_details:
            agent_data["status_details"] = status_details

        if task_id:
            agent_data["current_task_id"] = task_id

        if task_description:
            agent_data["assigned_task_description"] = task_description

        self._write_task_board(data)
        logger.info(f"Updated status for agent {agent_id} to {status}")

    def add_task(
        self, agent_id: str, task_id: str, task_data: Dict[str, Any]
    ) -> None:
        """
        Add a task to an agent's task list.

        Args:
            agent_id: ID of the agent to add the task to
            task_id: ID of the task
            task_data: Task data dictionary
        """
        data = self._read_task_board()

        # Ensure cursor_agents section exists
        if "cursor_agents" not in data:
            data["cursor_agents"] = {}

        # Create agent entry if it doesn't exist
        if agent_id not in data["cursor_agents"]:
            data["cursor_agents"][agent_id] = {
                "status": "UNKNOWN",
                "last_status_update_utc": datetime.utcnow().isoformat(),
                "tasks": {},
            }

        # Ensure tasks section exists
        if "tasks" not in data["cursor_agents"][agent_id]:
            data["cursor_agents"][agent_id]["tasks"] = {}

        # Add task
        data["cursor_agents"][agent_id]["tasks"][task_id] = task_data

        self._write_task_board(data)
        logger.info(f"Added task {task_id} to agent {agent_id}")

    def update_task(
        self, agent_id: str, task_id: str, task_updates: Dict[str, Any]
    ) -> None:
        """
        Update an existing task for an agent.

        Args:
            agent_id: ID of the agent
            task_id: ID of the task to update
            task_updates: Dictionary of task fields to update
        """
        data = self._read_task_board()

        # Check if agent and task exist
        if (
            "cursor_agents" not in data
            or agent_id not in data["cursor_agents"]
            or "tasks" not in data["cursor_agents"][agent_id]
            or task_id not in data["cursor_agents"][agent_id]["tasks"]
        ):
            logger.error(f"Task {task_id} not found for agent {agent_id}")
            return

        # Update task
        for key, value in task_updates.items():
            data["cursor_agents"][agent_id]["tasks"][task_id][key] = value

        # Update timestamp
        data["cursor_agents"][agent_id]["tasks"][task_id][
            "last_updated"
        ] = datetime.utcnow().isoformat()

        self._write_task_board(data)
        logger.info(f"Updated task {task_id} for agent {agent_id}")


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Update agent status and tasks in task_board.json")
    parser.add_argument(
        "--task-board",
        type=Path,
        default=DEFAULT_TASK_BOARD_PATH,
        help=f"Path to the task board JSON file (default: {DEFAULT_TASK_BOARD_PATH})",
    )
    parser.add_argument(
        "--lock-timeout",
        type=int,
        default=DEFAULT_LOCK_TIMEOUT,
        help=f"Timeout for acquiring file lock in seconds (default: {DEFAULT_LOCK_TIMEOUT})",
    )

    # Create subparsers for different operations
    subparsers = parser.add_subparsers(dest="operation", help="Operation to perform")

    # Parser for update-status operation
    update_status_parser = subparsers.add_parser("update-status", help="Update an agent's status")
    update_status_parser.add_argument("agent_id", help="ID of the agent (e.g., cursor_1)")
    update_status_parser.add_argument("status", help="New status (e.g., EXECUTING, IDLE)")
    update_status_parser.add_argument("--status-details", help="Optional details about the status")
    update_status_parser.add_argument("--task-id", help="Optional task ID the agent is working on")
    update_status_parser.add_argument("--task-description", help="Optional task description")

    # Parser for add-task operation
    add_task_parser = subparsers.add_parser("add-task", help="Add a task to an agent's task list")
    add_task_parser.add_argument("agent_id", help="ID of the agent to add the task to")
    add_task_parser.add_argument("task_id", help="ID of the task")
    add_task_parser.add_argument(
        "task_json",
        help="JSON string containing task data or path to JSON file",
    )

    # Parser for update-task operation
    update_task_parser = subparsers.add_parser("update-task", help="Update an existing task for an agent")
    update_task_parser.add_argument("agent_id", help="ID of the agent")
    update_task_parser.add_argument("task_id", help="ID of the task to update")
    update_task_parser.add_argument(
        "updates_json",
        help="JSON string containing task updates or path to JSON file",
    )

    args = parser.parse_args()

    # Create TaskBoardUpdater
    updater = TaskBoardUpdater(args.task_board, args.lock_timeout)

    # Perform the requested operation
    if args.operation == "update-status":
        updater.update_agent_status(
            args.agent_id,
            args.status,
            args.status_details,
            args.task_id,
            args.task_description,
        )
    elif args.operation == "add-task":
        # Parse task JSON
        task_data = _parse_json_arg(args.task_json)
        updater.add_task(args.agent_id, args.task_id, task_data)
    elif args.operation == "update-task":
        # Parse updates JSON
        updates = _parse_json_arg(args.updates_json)
        updater.update_task(args.agent_id, args.task_id, updates)
    else:
        parser.print_help()


def _parse_json_arg(json_arg: str) -> Dict[str, Any]:
    """
    Parse a JSON argument that could be a JSON string or a path to a JSON file.

    Args:
        json_arg: JSON string or path to JSON file

    Returns:
        Parsed JSON data as a dictionary
    """
    # First try to parse as a JSON string
    try:
        return json.loads(json_arg)
    except json.JSONDecodeError:
        # If that fails, try to read as a file path
        try:
            with open(json_arg, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, IsADirectoryError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse JSON argument: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main() 