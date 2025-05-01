# scripts/utils/simple_task_updater.py
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SimpleTaskHandler")  # Renamed logger slightly

# Ensure the src directory is in the Python path
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from dreamos.core.comms.project_board import ProjectBoardError, ProjectBoardManager
    from dreamos.utils.common_utils import get_utc_iso_timestamp
except ImportError as e:
    logger.critical(
        f"Error: Failed to import dreamos components. Ensure dependencies are met. Error: {e}"
    )
    sys.exit(1)

# Define the default BASE directory for boards
DEFAULT_BOARDS_BASE_DIR = PROJECT_ROOT / "runtime" / "agent_comms" / "project_boards"

# Define standard filenames as string literals here
WORKING_TASKS_FILENAME = "working_tasks.json"
COMPLETED_TASKS_FILENAME = "completed_tasks.json"


def main():
    # Main parser
    parser = argparse.ArgumentParser(
        description="Claim or Update tasks directly using ProjectBoardManager."
    )
    parser.add_argument(
        "--boards_dir",
        default=str(DEFAULT_BOARDS_BASE_DIR),
        help=f"Path to the directory containing task board JSON files (default: {DEFAULT_BOARDS_BASE_DIR})",
    )

    # Subparsers for actions
    subparsers = parser.add_subparsers(
        dest="action", required=True, help="Action to perform: 'claim' or 'update'"
    )

    # --- Claim Action Parser ---
    parser_claim = subparsers.add_parser(
        "claim", help="Claim a task from future_tasks.json."
    )
    parser_claim.add_argument("task_id", help="The ID of the task to claim.")
    parser_claim.add_argument("agent_id", help="The ID of the agent claiming the task.")

    # --- Update Action Parser ---
    parser_update = subparsers.add_parser(
        "update", help="Update a task status/notes in a specified board file."
    )
    parser_update.add_argument("task_id", help="The ID of the task to update.")
    parser_update.add_argument(
        "status", help="The new status for the task (e.g., COMPLETED, FAILED, WORKING)."
    )
    parser_update.add_argument(
        "--notes", default=None, help="Optional notes to add/update for the task."
    )
    parser_update.add_argument(
        "--board_file",
        default=WORKING_TASKS_FILENAME,
        help=f"Target board file for update (e.g., '{WORKING_TASKS_FILENAME}'). Default: {WORKING_TASKS_FILENAME}",
    )
    # Note: Moving to completed_tasks still needs ProjectBoardManager support

    args = parser.parse_args()

    # Instantiate ProjectBoardManager
    boards_base_dir = Path(args.boards_dir).resolve()
    if not boards_base_dir.is_dir():
        logger.critical(f"Error: Boards directory not found: {boards_base_dir}")
        sys.exit(1)
    try:
        board_manager = ProjectBoardManager(boards_base_dir=boards_base_dir)
    except Exception as e:
        logger.critical(f"Error initializing ProjectBoardManager: {e}", exc_info=True)
        sys.exit(1)

    # --- Perform Action ---
    if args.action == "claim":
        logger.info(
            f"Attempting to claim task '{args.task_id}' for agent '{args.agent_id}'"
        )
        try:
            success = board_manager.claim_future_task(
                task_id=args.task_id, agent_id=args.agent_id
            )
            if success:
                logger.info(
                    f"Task '{args.task_id}' claimed successfully by '{args.agent_id}'."
                )
                sys.exit(0)
            else:
                logger.error(
                    f"Failed to claim task '{args.task_id}'. Task may not exist, already claimed, or error occurred."
                )
                sys.exit(1)
        except ProjectBoardError as e:
            logger.error(
                f"ProjectBoardError claiming task '{args.task_id}': {e}", exc_info=True
            )
            sys.exit(1)
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during claim: {e}", exc_info=True
            )
            sys.exit(1)

    elif args.action == "update":
        # Determine if this update represents task completion
        is_completion_status = args.status.upper().startswith("COMPLETED")

        # Prepare the update dictionary
        update_dict = {
            "status": args.status,
            "timestamp_updated": get_utc_iso_timestamp(),
        }
        if args.notes is not None:
            update_dict["notes"] = args.notes

        if is_completion_status:
            # Add completed timestamp for completion updates
            update_dict["timestamp_completed"] = get_utc_iso_timestamp()

            # Use the new move_task_to_completed method
            logger.info(
                f"Attempting to move task '{args.task_id}' to completed with status '{args.status}'"
            )
            try:
                success = board_manager.move_task_to_completed(
                    task_id=args.task_id, final_updates=update_dict
                )
                if success:
                    logger.info(
                        f"Task '{args.task_id}' successfully moved to completed."
                    )
                    sys.exit(0)
                else:
                    logger.error(
                        f"Failed to move task '{args.task_id}' to completed. Task may not exist in working tasks or error occurred."
                    )
                    sys.exit(1)
            except ProjectBoardError as e:
                logger.error(
                    f"ProjectBoardError moving task '{args.task_id}' to completed: {e}",
                    exc_info=True,
                )
                sys.exit(1)
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred moving task '{args.task_id}' to completed: {e}",
                    exc_info=True,
                )
                sys.exit(1)
        else:
            # For non-completion updates, use the existing update_working_task method
            logger.info(
                f"Attempting to update task '{args.task_id}' status to '{args.status}' in '{args.board_file}'"
            )

            # Check if target board is supported (redundant check now maybe, but safe)
            if args.board_file != WORKING_TASKS_FILENAME:
                logger.error(
                    f"Error: Updating non-completion status on board '{args.board_file}' is not supported. Only '{WORKING_TASKS_FILENAME}' update is implemented."
                )
                sys.exit(1)

            try:
                success = board_manager.update_working_task(
                    task_id=args.task_id, updates=update_dict
                )
                if success:
                    logger.info(
                        f"Task '{args.task_id}' updated successfully in '{args.board_file}'."
                    )
                    sys.exit(0)
                else:
                    logger.error(
                        f"Failed to update task '{args.task_id}'. Task may not exist in '{args.board_file}' or an error occurred."
                    )
                    sys.exit(1)
            except ProjectBoardError as e:
                logger.error(
                    f"ProjectBoardError updating task '{args.task_id}': {e}",
                    exc_info=True,
                )
                sys.exit(1)
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during update: {e}", exc_info=True
                )
                sys.exit(1)

    else:
        logger.critical(f"Unknown action: {args.action}")  # Should not happen
        sys.exit(1)


if __name__ == "__main__":
    main()
