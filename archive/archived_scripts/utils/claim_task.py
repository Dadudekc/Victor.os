#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Adjust path to import from src
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

try:
    # Import the manager class and necessary constants
    from dreamos.core.comms.project_board import (
        FUTURE_TASKS_FILENAME,
        WORKING_TASKS_FILENAME,
        ProjectBoardError,
        ProjectBoardManager,
    )

    # Assume a default base dir if BOARD_DEFAULTS isn't available
    DEFAULT_BOARDS_DIR = "runtime/agent_comms/project_boards"
except ImportError as e:
    print(
        f"Error: Failed to import ProjectBoardManager or constants. Ensure src is in PYTHONPATH. Details: {e}",  # noqa: E501
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Safely claim a task from the future_tasks board using ProjectBoardManager."  # noqa: E501
    )
    parser.add_argument(
        "task_id", help="The ID of the task to claim from future_tasks.json."
    )
    parser.add_argument("agent_id", help="The ID of the agent claiming the task.")
    parser.add_argument(
        "--boards-dir",
        default=DEFAULT_BOARDS_DIR,  # Use defined default
        help=f"Directory containing project boards (default: {DEFAULT_BOARDS_DIR})",
    )
    parser.add_argument(
        "--future-board",
        default=FUTURE_TASKS_FILENAME,  # Use imported constant
        help=f"Filename for the future tasks board (default: {FUTURE_TASKS_FILENAME})",
    )
    parser.add_argument(
        "--working-board",
        default=WORKING_TASKS_FILENAME,  # Use imported constant
        help=f"Filename for the working tasks board (default: {WORKING_TASKS_FILENAME})",  # noqa: E501
    )

    args = parser.parse_args()

    # Convert boards_dir string to Path for ProjectBoardManager
    boards_base_dir = Path(args.boards_dir)

    try:
        # Instantiate manager with base dir only, let it use internal constants for filenames  # noqa: E501
        board_manager = ProjectBoardManager(boards_base_dir=boards_base_dir)

        print(
            f"Attempting to claim task '{args.task_id}' for agent '{args.agent_id}'..."
        )

        # Call claim_future_task, it uses internal constants for file paths
        success = board_manager.claim_future_task(
            task_id=args.task_id, agent_id=args.agent_id
        )

        if success:
            print(
                f"Successfully claimed task '{args.task_id}' for agent '{args.agent_id}'. Task moved to working board."  # noqa: E501
            )
            sys.exit(0)
        else:
            # claim_future_task logs warnings/errors internally if task not found etc.
            print(
                f"Failed to claim task '{args.task_id}'. Task might not exist in '{args.future_board}' or another error occurred.",  # noqa: E501
                file=sys.stderr,
            )
            sys.exit(1)

    except ProjectBoardError as e:
        print(f"Error during task claim process: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
